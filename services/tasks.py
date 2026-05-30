"""Google Tasks service tools."""

import asyncio
from typing import Optional

from googleapiclient.discovery import build

from auth import get_credentials


def _tasks_svc(creds):
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


def _list_task_lists(creds) -> list[dict]:
    svc = _tasks_svc(creds)
    resp = svc.tasklists().list(maxResults=100).execute()
    return [
        {"id": tl["id"], "title": tl["title"], "updated": tl.get("updated", "")}
        for tl in resp.get("items", [])
    ]


def _list_tasks(creds, task_list_id: str, show_completed: bool) -> list[dict]:
    svc = _tasks_svc(creds)
    resp = (
        svc.tasks()
        .list(
            tasklist=task_list_id,
            showCompleted=show_completed,
            showHidden=show_completed,
            maxResults=100,
        )
        .execute()
    )
    return [
        {
            "id": t["id"],
            "title": t.get("title", ""),
            "status": t.get("status", ""),
            "due": t.get("due", ""),
            "notes": t.get("notes", ""),
            "completed": t.get("completed", ""),
        }
        for t in resp.get("items", [])
    ]


def _create_task(
    creds, task_list_id: str, title: str, notes: str, due: Optional[str]
) -> dict:
    svc = _tasks_svc(creds)
    body = {"title": title, "notes": notes}
    if due:
        body["due"] = due  # RFC 3339 timestamp, e.g. "2024-06-01T00:00:00.000Z"
    task = svc.tasks().insert(tasklist=task_list_id, body=body).execute()
    return {"id": task["id"], "title": task.get("title", ""), "status": "created"}


# Async wrappers

async def list_task_lists(user_google_email: str) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(None, _list_task_lists, creds)


async def list_tasks(
    user_google_email: str,
    task_list_id: str = "@default",
    show_completed: bool = False,
) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _list_tasks, creds, task_list_id, show_completed
    )


async def create_task(
    user_google_email: str,
    title: str,
    task_list_id: str = "@default",
    notes: str = "",
    due: Optional[str] = None,
) -> dict:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _create_task, creds, task_list_id, title, notes, due
    )
