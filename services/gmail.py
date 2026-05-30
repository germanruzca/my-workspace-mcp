"""Gmail service tools."""

import asyncio
import base64
import email as email_lib
from email.mime.text import MIMEText
from typing import Optional

from googleapiclient.discovery import build

from auth import get_credentials


def _gmail(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from a message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if body_data and "text/plain" in mime_type:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result

    return ""


# ---------------------------------------------------------------------------
# Tool implementations (sync, wrapped with run_in_executor by server.py)
# ---------------------------------------------------------------------------


def _search_messages(creds, query: str, page_size: int) -> list[dict]:
    svc = _gmail(creds)
    resp = svc.users().messages().list(userId="me", q=query, maxResults=page_size).execute()
    messages = resp.get("messages", [])
    results = []
    for msg in messages:
        full = (
            svc.users()
            .messages()
            .get(userId="me", id=msg["id"], format="metadata",
                 metadataHeaders=["From", "To", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
        results.append({
            "id": msg["id"],
            "thread_id": full.get("threadId"),
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": full.get("snippet", ""),
        })
    return results


def _get_message(creds, message_id: str) -> dict:
    svc = _gmail(creds)
    full = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
    body = _decode_body(full.get("payload", {}))
    return {
        "id": full["id"],
        "thread_id": full.get("threadId"),
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "body": body,
        "labels": full.get("labelIds", []),
    }


def _send_message(creds, to: str, subject: str, body: str, reply_to_id: Optional[str]) -> dict:
    svc = _gmail(creds)
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    msg_body = {"raw": raw}
    if reply_to_id:
        original = svc.users().messages().get(userId="me", id=reply_to_id, format="metadata").execute()
        msg_body["threadId"] = original.get("threadId")
    sent = svc.users().messages().send(userId="me", body=msg_body).execute()
    return {"id": sent["id"], "thread_id": sent.get("threadId"), "status": "sent"}


def _create_draft(creds, to: str, subject: str, body: str) -> dict:
    svc = _gmail(creds)
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"draft_id": draft["id"], "status": "created"}


def _list_labels(creds) -> list[dict]:
    svc = _gmail(creds)
    resp = svc.users().labels().list(userId="me").execute()
    return [{"id": lb["id"], "name": lb["name"]} for lb in resp.get("labels", [])]


# ---------------------------------------------------------------------------
# Async wrappers used by server.py
# ---------------------------------------------------------------------------

async def search_messages(user_google_email: str, query: str, page_size: int = 10) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _search_messages, creds, query, page_size
    )


async def get_message(user_google_email: str, message_id: str) -> dict:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _get_message, creds, message_id
    )


async def send_message(
    user_google_email: str, to: str, subject: str, body: str,
    reply_to_id: Optional[str] = None,
) -> dict:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _send_message, creds, to, subject, body, reply_to_id
    )


async def create_draft(user_google_email: str, to: str, subject: str, body: str) -> dict:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _create_draft, creds, to, subject, body
    )


async def list_labels(user_google_email: str) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(None, _list_labels, creds)
