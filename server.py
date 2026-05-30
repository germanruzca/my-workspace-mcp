"""
Google Workspace MCP server.

Run via Claude Desktop stdio transport:
  python server.py [--read-only]

Flags:
  --read-only   Disable all write operations (send email, create drafts,
                create calendar events, create tasks). Useful to prevent
                prompt-injection attacks from acting on your behalf.

Environment variables required:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
"""

import json
import sys
from typing import Optional

from fastmcp import FastMCP

import auth
import services.calendar as cal_svc
import services.drive as drive_svc
import services.gmail as gmail_svc
import services.tasks as tasks_svc

READ_ONLY_MODE = "--read-only" in sys.argv

mcp = FastMCP(
    name="my-workspace",
    instructions=(
        "Google Workspace MCP — READ-ONLY MODE ACTIVE. "
        "Write operations are disabled: you MUST NOT attempt to send emails, "
        "create drafts, create calendar events, or create tasks. "
        "Only read/list/search tools are available. "
        "Every tool requires a `user_google_email` parameter."
        if READ_ONLY_MODE else
        "Google Workspace MCP. Every tool requires a `user_google_email` parameter "
        "to identify which Google account to use. If the account is not yet authenticated, "
        "a browser window will open for OAuth consent."
    ),
)


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------


@mcp.tool()
def list_connected_accounts() -> str:
    """Return the Google accounts that have stored OAuth tokens."""
    accounts = auth.list_connected_accounts()
    if not accounts:
        return "No accounts connected yet. Call any tool with a user_google_email to start the OAuth flow."
    return json.dumps(accounts)


@mcp.tool()
def revoke_account(user_google_email: str) -> str:
    """Remove the stored token for a Google account."""
    removed = auth.revoke_account(user_google_email)
    if removed:
        return f"Token for {user_google_email} has been removed."
    return f"No stored token found for {user_google_email}."


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_gmail_messages(
    user_google_email: str,
    query: str,
    page_size: int = 10,
) -> str:
    """
    Search Gmail messages using the Gmail search syntax.

    Examples:
      query="is:unread"
      query="from:boss@example.com subject:report"
      query="after:2024/01/01 has:attachment"
    """
    results = await gmail_svc.search_messages(user_google_email, query, page_size)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
async def get_gmail_message(user_google_email: str, message_id: str) -> str:
    """Read the full content of a Gmail message by its ID."""
    result = await gmail_svc.get_message(user_google_email, message_id)
    return json.dumps(result, ensure_ascii=False)


if not READ_ONLY_MODE:
    @mcp.tool()
    async def send_gmail_message(
        user_google_email: str,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
    ) -> str:
        """Send an email. Optionally pass reply_to_message_id to reply in-thread."""
        result = await gmail_svc.send_message(user_google_email, to, subject, body, reply_to_message_id)
        return json.dumps(result)

    @mcp.tool()
    async def create_gmail_draft(
        user_google_email: str,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """Save an email as a draft (does not send)."""
        result = await gmail_svc.create_draft(user_google_email, to, subject, body)
        return json.dumps(result)


@mcp.tool()
async def list_gmail_labels(user_google_email: str) -> str:
    """List all Gmail labels for the account."""
    result = await gmail_svc.list_labels(user_google_email)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_google_calendars(user_google_email: str) -> str:
    """List all calendars accessible by the account."""
    result = await cal_svc.list_calendars(user_google_email)
    return json.dumps(result)


@mcp.tool()
async def get_calendar_events(
    user_google_email: str,
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 20,
) -> str:
    """
    Retrieve calendar events.

    time_min / time_max: RFC 3339 strings, e.g. "2024-06-01T00:00:00Z"
    """
    result = await cal_svc.get_events(
        user_google_email, calendar_id, time_min, time_max, max_results
    )
    return json.dumps(result, ensure_ascii=False)


if not READ_ONLY_MODE:
    @mcp.tool()
    async def create_calendar_event(
        user_google_email: str,
        summary: str,
        start_datetime: str,
        end_datetime: str,
        calendar_id: str = "primary",
        description: str = "",
        attendees: Optional[list[str]] = None,
        timezone: str = "UTC",
    ) -> str:
        """
        Create a calendar event.

        start_datetime / end_datetime: RFC 3339, e.g. "2024-06-15T10:00:00"
        timezone: IANA tz name, e.g. "America/New_York"
        attendees: list of email addresses
        """
        result = await cal_svc.create_event(
            user_google_email, summary, start_datetime, end_datetime,
            calendar_id, description, attendees, timezone,
        )
        return json.dumps(result)


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_drive_files(
    user_google_email: str,
    query: str,
    page_size: int = 20,
) -> str:
    """
    Search Google Drive files using Drive query syntax.

    Examples:
      query="name contains 'report'"
      query="mimeType='application/vnd.google-apps.document'"
      query="'root' in parents and trashed = false"
    """
    result = await drive_svc.search_files(user_google_email, query, page_size)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def list_drive_folder(
    user_google_email: str,
    folder_id: str,
    page_size: int = 50,
) -> str:
    """List files inside a specific Drive folder by its ID."""
    result = await drive_svc.list_folder(user_google_email, folder_id, page_size)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def read_drive_file(user_google_email: str, file_id: str) -> str:
    """
    Read the text content of a Drive file.

    Google Docs/Sheets/Slides are exported as plain text / CSV.
    Binary files are read and decoded as UTF-8.
    """
    result = await drive_svc.read_file_content(user_google_email, file_id)
    return result


# ---------------------------------------------------------------------------
# Google Tasks
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_task_lists(user_google_email: str) -> str:
    """List all Google Task lists for the account."""
    result = await tasks_svc.list_task_lists(user_google_email)
    return json.dumps(result)


@mcp.tool()
async def list_tasks(
    user_google_email: str,
    task_list_id: str = "@default",
    show_completed: bool = False,
) -> str:
    """List tasks in a task list. Use '@default' for the default list."""
    result = await tasks_svc.list_tasks(user_google_email, task_list_id, show_completed)
    return json.dumps(result, ensure_ascii=False)


if not READ_ONLY_MODE:
    @mcp.tool()
    async def create_task(
        user_google_email: str,
        title: str,
        task_list_id: str = "@default",
        notes: str = "",
        due: Optional[str] = None,
    ) -> str:
        """
        Create a task.

        due: RFC 3339 timestamp, e.g. "2024-06-01T00:00:00.000Z"
        """
        result = await tasks_svc.create_task(user_google_email, title, task_list_id, notes, due)
        return json.dumps(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from config import CLIENT_ID, CLIENT_SECRET

    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    if READ_ONLY_MODE:
        print("INFO: Running in read-only mode. Write tools are disabled.", file=sys.stderr)
        sys.argv = [arg for arg in sys.argv if arg != "--read-only"]

    mcp.run(transport="stdio")
