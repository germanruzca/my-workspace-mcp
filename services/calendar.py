"""Google Calendar service tools."""

import asyncio
from typing import Optional

from googleapiclient.discovery import build

from auth import get_credentials


def _calendar(creds):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _list_calendars(creds) -> list[dict]:
    svc = _calendar(creds)
    resp = svc.calendarList().list().execute()
    return [
        {
            "id": cal["id"],
            "summary": cal.get("summary", ""),
            "primary": cal.get("primary", False),
            "access_role": cal.get("accessRole", ""),
        }
        for cal in resp.get("items", [])
    ]


def _get_events(
    creds, calendar_id: str, time_min: Optional[str], time_max: Optional[str], max_results: int
) -> list[dict]:
    svc = _calendar(creds)
    kwargs = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        kwargs["timeMin"] = time_min
    if time_max:
        kwargs["timeMax"] = time_max

    resp = svc.events().list(**kwargs).execute()
    events = []
    for e in resp.get("items", []):
        start = e.get("start", {})
        end = e.get("end", {})
        events.append({
            "id": e["id"],
            "summary": e.get("summary", ""),
            "description": e.get("description", ""),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "location": e.get("location", ""),
            "attendees": [a.get("email") for a in e.get("attendees", [])],
            "html_link": e.get("htmlLink", ""),
        })
    return events


def _create_event(
    creds,
    calendar_id: str,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str,
    attendees: list[str],
    timezone: str,
) -> dict:
    svc = _calendar(creds)
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": timezone},
        "end": {"dateTime": end_datetime, "timeZone": timezone},
    }
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]

    event = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return {
        "id": event["id"],
        "summary": event.get("summary", ""),
        "html_link": event.get("htmlLink", ""),
        "status": "created",
    }


# Async wrappers

async def list_calendars(user_google_email: str) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(None, _list_calendars, creds)


async def get_events(
    user_google_email: str,
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 20,
) -> list[dict]:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None, _get_events, creds, calendar_id, time_min, time_max, max_results
    )


async def create_event(
    user_google_email: str,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    calendar_id: str = "primary",
    description: str = "",
    attendees: Optional[list[str]] = None,
    timezone: str = "UTC",
) -> dict:
    creds = await get_credentials(user_google_email)
    return await asyncio.get_event_loop().run_in_executor(
        None,
        _create_event,
        creds,
        calendar_id,
        summary,
        start_datetime,
        end_datetime,
        description,
        attendees or [],
        timezone,
    )
