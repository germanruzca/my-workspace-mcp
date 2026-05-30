import os
from pathlib import Path

# Allow Google to return a superset of requested scopes without raising an error
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

# OAuth credentials from environment
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Token storage
CREDENTIALS_DIR = Path.home() / ".my_workspace_mcp" / "credentials"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth callback
REDIRECT_URI = "http://localhost:8000/oauth/callback"
OAUTH_PORT = 8000

# Google OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/tasks",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
