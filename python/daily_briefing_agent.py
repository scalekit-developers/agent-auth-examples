"""
Use Case 3: Daily Briefing / Morning Digest Agent
---------------------------------------------------
Fetches today's calendar events and unread emails, then prints a structured
morning digest so you can start your day with full context.

Setup:
    pip install -r requirements.txt

Required env vars (.env):
    SCALEKIT_CLIENT_ID, SCALEKIT_CLIENT_SECRET, SCALEKIT_ENVIRONMENT_URL

Dashboard setup:
    Agent Auth → Connections → + Create Connection → Gmail          → Name: "gmail"
    Agent Auth → Connections → + Create Connection → Google Calendar → Name: "googlecalendar"
"""

import os
import requests
import scalekit.client
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Scalekit auth setup
# ---------------------------------------------------------------------------
sk = scalekit.client.ScalekitClient(
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
)
actions = sk.actions

USER_ID = "user_123"

# ---------------------------------------------------------------------------
# Authorize both connectors
# ---------------------------------------------------------------------------
def authorize(connector: str) -> str:
    """Ensure the connector is authorized and return a fresh access token."""
    resp = actions.get_or_create_connected_account(
        connection_name=connector, identifier=USER_ID
    )
    if resp.connected_account.status != "ACTIVE":
        link = actions.get_authorization_link(
            connection_name=connector, identifier=USER_ID
        )
        print(f"Authorize {connector} here: {link.link}")
        input("Press Enter after completing authorization...")

    tokens = actions.get_connected_account(
        connection_name=connector, identifier=USER_ID
    )
    return tokens.connected_account.authorization_details["oauth_token"]["access_token"]


gmail_token = authorize("gmail")
cal_token   = authorize("googlecalendar")

gmail_headers = {"Authorization": f"Bearer {gmail_token}"}
cal_headers   = {"Authorization": f"Bearer {cal_token}"}
gmail_url     = "https://gmail.googleapis.com/gmail/v1/users/me"
calendar_url  = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

# ---------------------------------------------------------------------------
# Time bounds for "today"
# ---------------------------------------------------------------------------
now        = datetime.now(timezone.utc)
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
today_end   = today_start + timedelta(days=1)

# ---------------------------------------------------------------------------
# Fetch today's calendar events
# ---------------------------------------------------------------------------
events_resp = requests.get(
    calendar_url,
    headers=cal_headers,
    params={
        "timeMin":     today_start.isoformat(),
        "timeMax":     today_end.isoformat(),
        "singleEvents": True,
        "orderBy":     "startTime",
    },
).json()

events = events_resp.get("items", [])

# ---------------------------------------------------------------------------
# Fetch unread emails (up to 10)
# ---------------------------------------------------------------------------
messages_resp = requests.get(
    f"{gmail_url}/messages",
    headers=gmail_headers,
    params={"q": "is:unread", "maxResults": 10},
).json()

message_ids = messages_resp.get("messages", [])

emails = []
for msg in message_ids:
    data = requests.get(
        f"{gmail_url}/messages/{msg['id']}",
        headers=gmail_headers,
        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
    ).json()
    hdrs    = data.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in hdrs if h["name"] == "Subject"), "(no subject)")
    sender  = next((h["value"] for h in hdrs if h["name"] == "From"),    "Unknown")
    snippet = data.get("snippet", "")
    emails.append({"subject": subject, "sender": sender, "snippet": snippet})

# ---------------------------------------------------------------------------
# Print morning digest
# ---------------------------------------------------------------------------
date_str = now.strftime("%A, %B %d %Y")
print(f"\n{'=' * 60}")
print(f"  MORNING BRIEFING — {date_str}")
print(f"{'=' * 60}")

# --- Calendar section ---
print(f"\nCALENDAR — {len(events)} event(s) today")
print("-" * 50)
if events:
    for event in events:
        start_raw = event.get("start", {})
        start     = start_raw.get("dateTime") or start_raw.get("date", "All day")
        if "T" in start:
            try:
                dt    = datetime.fromisoformat(start)
                start = dt.strftime("%H:%M")
            except ValueError:
                pass
        title = event.get("summary", "No Title")
        loc   = event.get("location", "")
        print(f"  {start:>8}  {title}" + (f"  [{loc}]" if loc else ""))
else:
    print("  No events today — enjoy the open calendar!")

# --- Email section ---
print(f"\nEMAIL — {len(emails)} unread message(s)")
print("-" * 50)
if emails:
    for e in emails:
        print(f"  From:    {e['sender']}")
        print(f"  Subject: {e['subject']}")
        print(f"  Preview: {e['snippet'][:90]}...")
        print()
else:
    print("  Inbox zero — no unread messages!")

print(f"{'=' * 60}")
print(f"  Briefing complete. Have a productive day!")
print(f"{'=' * 60}\n")
