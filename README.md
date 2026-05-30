# my_workspace_mcp

A local Python MCP server for Google Workspace with **multi-account support**.  
Connect N Gmail, Calendar, Drive, and Tasks accounts simultaneously from Claude Desktop.

---

## Prerequisites

- Python 3.11+
- A Google Cloud project with an OAuth 2.0 **Web application** credential
- The following APIs enabled in your Cloud project:
  - Gmail API
  - Google Calendar API
  - Google Drive API
  - Google Tasks API

---

## 1 — Google Cloud setup

1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** → Application type: **Web application**.
3. Note your **Client ID** and **Client Secret**.
5. Add the email addresses you want to use under **Test users** (OAuth consent screen → Test users) while the app is in *Testing* mode.

---

## 2 — Install

```bash
cd my_workspace_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3 — Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-workspace": {
      "command": "/absolute/path/to/my_workspace_mcp/.venv/bin/python",
      "args": ["/absolute/path/to/my_workspace_mcp/server.py"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

Replace the paths with the actual absolute paths on your machine.

Restart Claude Desktop after saving.

---

## 4 — First-time authentication

When you call any tool with a new `user_google_email`, the server:

1. Prints a message in the Claude Desktop console.
2. Opens a browser tab to the Google consent screen.
3. After you approve, the token is saved to `~/.my_workspace_mcp/credentials/<email>.json`.
4. The tool call completes.

Subsequent calls refresh the token automatically.

---

## 5 — Token storage

Tokens are stored at:

```
~/.my_workspace_mcp/credentials/
├── you@gmail.com.json
└── work@company.com.json
```

---

## Available tools

### Account management
| Tool | Description |
|------|-------------|
| `list_connected_accounts` | Show accounts with stored tokens |
| `revoke_account(user_google_email)` | Delete a stored token |

### Gmail
| Tool | Key parameters |
|------|---------------|
| `search_gmail_messages` | `query`, `page_size` |
| `get_gmail_message` | `message_id` |
| `send_gmail_message` | `to`, `subject`, `body`, `reply_to_message_id?` |
| `create_gmail_draft` | `to`, `subject`, `body` |
| `list_gmail_labels` | — |

### Google Calendar
| Tool | Key parameters |
|------|---------------|
| `list_google_calendars` | — |
| `get_calendar_events` | `calendar_id`, `time_min?`, `time_max?`, `max_results` |
| `create_calendar_event` | `summary`, `start_datetime`, `end_datetime`, `attendees?`, `timezone` |

### Google Drive
| Tool | Key parameters |
|------|---------------|
| `search_drive_files` | `query`, `page_size` |
| `list_drive_folder` | `folder_id`, `page_size` |
| `read_drive_file` | `file_id` |

### Google Tasks
| Tool | Key parameters |
|------|---------------|
| `list_task_lists` | — |
| `list_tasks` | `task_list_id`, `show_completed` |
| `create_task` | `title`, `task_list_id`, `notes?`, `due?` |

Every tool requires `user_google_email` to identify the account.

---

## Example prompts

```
List my connected accounts.

Search unread emails for me@gmail.com.

Show my calendar events for work@company.com this week (time_min="2024-06-03T00:00:00Z", time_max="2024-06-07T23:59:59Z").

Search Drive files containing "Q2 report" for me@gmail.com.

Create a task "Review PR" in my default list for me@gmail.com.
```

---

## Troubleshooting

**Token expired / invalid**  
Call `revoke_account(user_google_email)` then trigger any tool to re-authenticate.

**"Access blocked: This app's request is invalid"**  
Make sure the account is listed as a test user on the OAuth consent screen.
