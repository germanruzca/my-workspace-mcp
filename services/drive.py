"""Google Drive service tools."""

import asyncio
import io
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from auth import get_credentials

# MIME types that can be exported as plain text
_EXPORTABLE = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}


def _drive(creds):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _search_files(creds, query: str, page_size: int) -> list[dict]:
    svc = _drive(creds)
    resp = (
        svc.files()
        .list(
            q=query,
            pageSize=page_size,
            fields="files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
        )
        .execute()
    )
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "mime_type": f["mimeType"],
            "modified_time": f.get("modifiedTime", ""),
            "size": f.get("size", ""),
            "web_view_link": f.get("webViewLink", ""),
        }
        for f in resp.get("files", [])
    ]


def _list_folder(creds, folder_id: str, page_size: int) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed = false"
    return _search_files(creds, query, page_size)


def _read_file_content(creds, file_id: str) -> str:
    svc = _drive(creds)
    meta = svc.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime = meta["mimeType"]

    buf = io.BytesIO()

    if mime in _EXPORTABLE:
        export_mime, _ = _EXPORTABLE[mime]
        req = svc.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        req = svc.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buf.getvalue().decode("utf-8", errors="replace")


# Async wrappers

async def search_files(
    user_google_email: str, query: str, page_size: int = 20
) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _search_files, creds, query, page_size
    )


async def list_folder(
    user_google_email: str, folder_id: str, page_size: int = 50
) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _list_folder, creds, folder_id, page_size
    )


async def read_file_content(user_google_email: str, file_id: str) -> str:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _read_file_content, creds, file_id
    )
