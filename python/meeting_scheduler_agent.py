"""
Use Case 2: Meeting Scheduler Agent
--------------------------------------
Finds a free 1-hour slot in the next 3 days, creates a Google Calendar event,
and sends a Gmail confirmation to the attendee.

Setup:
    pip install -r requirements.txt

Required env vars (.env):
    SCALEKIT_CLIENT_ID, SCALEKIT_CLIENT_SECRET, SCALEKIT_ENVIRONMENT_URL

Dashboard setup:
    Agent Auth → Connections → + Create Connection → Google Calendar → Name: "googlecalendar"
    Agent Auth → Connections → + Create Connection → Gmail          → Name: "gmail"
"""

import os
import base64
import requests
import scalekit.client
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
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


cal_token   = authorize("googlecalendar")
gmail_token = authorize("gmail")

cal_headers   = {"Authorization": f"Bearer {cal_token}",   "Content-Type": "application/json"}
gmail_headers = {"Authorization": f"Bearer {gmail_token}", "Content-Type": "application/json"}
calendar_url  = "https://www.googleapis.com/calendar/v3"
gmail_url     = "https://gmail.googleapis.com/gmail/v1/users/me"

# ---------------------------------------------------------------------------
# Meeting parameters (customise as needed)
# ---------------------------------------------------------------------------
ATTENDEE_EMAIL   = "attendee@example.com"
MEETING_TITLE    = "Quick Sync"
MEETING_DURATION = 60   # minutes
SEARCH_DAYS      = 3    # look this many days ahead
WORK_START_HOUR  = 9    # 09:00 local (UTC used here for simplicity)
WORK_END_HOUR    = 17   # 17:00

# ---------------------------------------------------------------------------
# Find a free 1-hour slot via freebusy query
# ---------------------------------------------------------------------------
now       = datetime.now(timezone.utc)
time_max  = now + timedelta(days=SEARCH_DAYS)

freebusy_body = {
    "timeMin": now.isoformat(),
    "timeMax": time_max.isoformat(),
    "items":   [{"id": "primary"}],
}

busy_resp  = requests.post(
    f"{calendar_url}/freeBusy",
    headers=cal_headers,
    json=freebusy_body,
).json()

busy_slots = busy_resp.get("calendars", {}).get("primary", {}).get("busy", [])

def find_free_slot(busy: list, duration_min: int) -> tuple[datetime, datetime] | None:
    """Walk forward in 1-hour increments and return the first gap."""
    duration = timedelta(minutes=duration_min)
    candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    for _ in range(SEARCH_DAYS * 24):
        # Skip outside working hours
        if not (WORK_START_HOUR <= candidate.hour < WORK_END_HOUR - (duration_min // 60 - 1)):
            candidate += timedelta(hours=1)
            continue

        slot_end = candidate + duration
        conflict = any(
            candidate < datetime.fromisoformat(b["end"])
            and slot_end > datetime.fromisoformat(b["start"])
            for b in busy
        )
        if not conflict:
            return candidate, slot_end
        candidate += timedelta(hours=1)
    return None


slot = find_free_slot(busy_slots, MEETING_DURATION)

if slot is None:
    print(f"No free {MEETING_DURATION}-minute slot found in the next {SEARCH_DAYS} days.")
    raise SystemExit(1)

start_time, end_time = slot
print(f"\nFree slot found: {start_time.strftime('%Y-%m-%d %H:%M')} UTC"
      f" → {end_time.strftime('%H:%M')} UTC")

# ---------------------------------------------------------------------------
# Create the calendar event
# ---------------------------------------------------------------------------
event_body = {
    "summary":     MEETING_TITLE,
    "description": f"Scheduled automatically by an AI agent.",
    "start":       {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
    "end":         {"dateTime": end_time.isoformat(),   "timeZone": "UTC"},
    "attendees":   [{"email": ATTENDEE_EMAIL}],
}

created_event = requests.post(
    f"{calendar_url}/calendars/primary/events",
    headers=cal_headers,
    json=event_body,
).json()

event_link = created_event.get("htmlLink", "(no link)")
print(f"Calendar event created: {created_event.get('summary')}")
print(f"  Link: {event_link}")

# ---------------------------------------------------------------------------
# Send confirmation email via Gmail
# ---------------------------------------------------------------------------
subject = f"Meeting Scheduled: {MEETING_TITLE}"
body    = (
    f"Hi,\n\n"
    f"A meeting has been scheduled for you:\n\n"
    f"  Title:  {MEETING_TITLE}\n"
    f"  When:   {start_time.strftime('%A, %B %d %Y at %H:%M UTC')}\n"
    f"  Length: {MEETING_DURATION} minutes\n"
    f"  Link:   {event_link}\n\n"
    f"This was booked automatically by an AI scheduling agent.\n\n"
    f"Best regards"
)

msg                = MIMEText(body)
msg["To"]          = ATTENDEE_EMAIL
msg["Subject"]     = subject

raw   = base64.urlsafe_b64encode(msg.as_bytes()).decode()
draft = requests.post(
    f"{gmail_url}/drafts",
    headers=gmail_headers,
    json={"message": {"raw": raw}},
).json()

draft_id = draft.get("id", "unknown")
print(f"\nConfirmation draft created (ID: {draft_id}) → ready to send to {ATTENDEE_EMAIL}")
print("\n✅ Meeting scheduled and confirmation drafted successfully.")
