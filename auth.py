"""
OAuth 2.0 manager for multi-account Google authentication.

Flow for a new account:
  1. Tool is called with user_google_email
  2. get_credentials(email) is called
  3. No token found → build auth URL → open browser → local HTTP server catches callback
  4. Exchange code for tokens → save to disk → return credentials
"""

import asyncio
import json
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from config import (
    CLIENT_ID,
    CLIENT_SECRET,
    CREDENTIALS_DIR,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    OAUTH_PORT,
    REDIRECT_URI,
    SCOPES,
)

logger = logging.getLogger(__name__)

# Shared state between HTTP handler and OAuth flow
_oauth_code: Optional[str] = None
_oauth_error: Optional[str] = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth redirect from Google."""

    def do_GET(self):  # noqa: N802
        global _oauth_code, _oauth_error
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _oauth_code = params["code"][0]
            body = b"<h2>Authentication successful! You can close this tab.</h2>"
        elif "error" in params:
            _oauth_error = params["error"][0]
            body = f"<h2>Authentication failed: {_oauth_error}</h2>".encode()
        else:
            body = b"<h2>Unexpected response.</h2>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # suppress server logs
        pass


def _token_path(email: str) -> Path:
    return CREDENTIALS_DIR / f"{email}.json"


def _save_credentials(email: str, creds: Credentials) -> None:
    token_path = _token_path(email)
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    token_path.write_text(json.dumps(data, indent=2))
    logger.info("Saved credentials for %s", email)


def _load_credentials(email: str) -> Optional[Credentials]:
    token_path = _token_path(email)
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", GOOGLE_TOKEN_URI),
        client_id=data.get("client_id", CLIENT_ID),
        client_secret=data.get("client_secret", CLIENT_SECRET),
        scopes=data.get("scopes", SCOPES),
    )


def _build_flow() -> Flow:
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [REDIRECT_URI, "urn:ietf:wg:oauth:2.0:oob"],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


async def _run_oauth_flow(email: str) -> Credentials:
    """Run the browser-based OAuth flow and return credentials."""
    global _oauth_code, _oauth_error
    _oauth_code = None
    _oauth_error = None

    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=email,
    )

    # Start the local callback server in a background thread
    server = HTTPServer(("localhost", OAUTH_PORT), _CallbackHandler)
    server.timeout = 1.0

    logger.info("Opening browser for %s OAuth consent…", email)
    print(f"\n[auth] Opening browser for {email}. Complete the Google sign-in flow.")
    webbrowser.open(auth_url)

    # Poll until callback arrives (max 5 minutes)
    deadline = asyncio.get_event_loop().time() + 300
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.get_event_loop().run_in_executor(None, server.handle_request)
        if _oauth_code or _oauth_error:
            break

    server.server_close()

    if _oauth_error:
        raise RuntimeError(f"OAuth error for {email}: {_oauth_error}")
    if not _oauth_code:
        raise TimeoutError(f"OAuth timed out waiting for callback for {email}")

    flow.fetch_token(code=_oauth_code)
    creds = flow.credentials
    _save_credentials(email, creds)
    return creds


async def get_credentials(email: str) -> Credentials:
    """Return valid credentials for *email*, refreshing or re-authing as needed."""
    creds = _load_credentials(email)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing token for %s", email)
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: creds.refresh(Request())
        )
        _save_credentials(email, creds)
        return creds

    # No valid token → start full OAuth flow
    return await _run_oauth_flow(email)


def list_connected_accounts() -> list[str]:
    """Return email addresses that have stored tokens."""
    return [p.stem for p in CREDENTIALS_DIR.glob("*.json")]


def revoke_account(email: str) -> bool:
    """Delete stored token for *email*. Returns True if a file was removed."""
    path = _token_path(email)
    if path.exists():
        path.unlink()
        return True
    return False
