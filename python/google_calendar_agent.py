"""
Google Calendar Agent Auth Example
-------------------------------------
Demonstrates using Scalekit Agent Auth to authenticate an AI agent
and interact with Google Calendar on behalf of a user:
  - List upcoming events
  - Create a new event

Setup:
    pip install scalekit-sdk-python python-dotenv requests

Required env vars (.env):
    SCALEKIT_CLIENT_ID
    SCALEKIT_CLIENT_SECRET
    SCALEKIT_ENV_URL

Dashboard setup required (one-time):
    Scalekit Dashboard → Agent Auth → Connections → + Create Connection
    → Select "Google Calendar" → Connection Name: "google-calendar" → Save
"""

import os
import requests
from datetime import datetime, timedelta, timezone
import scalekit.client
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Initialize Scalekit client
# ---------------------------------------------------------------------------
sk = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
)
actions = sk.actions

USER_ID   = "user_123"            # Replace with your actual user identifier
CONNECTOR = "googlecalendar"     # Must match the Connection Name in the dashboard

# ---------------------------------------------------------------------------
# 2. Get or create a connected account for this user
# ---------------------------------------------------------------------------
response = actions.get_or_create_connected_account(
    connection_name=CONNECTOR,
    identifier=USER_ID,
)
connected_account = response.connected_account

# ---------------------------------------------------------------------------
# 3. If not authorized yet, send the user through OAuth
# ---------------------------------------------------------------------------
if connected_account.status != "ACTIVE":
    link_response = actions.get_authorization_link(
        connection_name=CONNECTOR,
        identifier=USER_ID,
    )
    print("Authorize access here:", link_response.link)
    input("Press Enter after completing authorization...")

# ---------------------------------------------------------------------------
# 4. Fetch the latest OAuth token (Scalekit auto-refreshes when needed)
# ---------------------------------------------------------------------------
account_response = actions.get_connected_account(
    connection_name=CONNECTOR,
    identifier=USER_ID,
)
tokens = account_response.connected_account.authorization_details["oauth_token"]
access_token = tokens["access_token"]

headers      = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
calendar_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

# ---------------------------------------------------------------------------
# 5a. List the next 5 upcoming events
# ---------------------------------------------------------------------------
now = datetime.now(timezone.utc).isoformat()

events_response = requests.get(
    calendar_url,
    headers=headers,
    params={
        "timeMin":    now,
        "maxResults": 5,
        "singleEvents": True,
        "orderBy":    "startTime",
    },
).json()

items = events_response.get("items", [])
print(f"\nNext {len(items)} upcoming events:\n" + "-" * 50)

for event in items:
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "Unknown")
    print(f"  {event.get('summary', 'No Title')}  |  {start}")

print("-" * 50)

# ---------------------------------------------------------------------------
# 5b. Create a sample event 1 hour from now
# ---------------------------------------------------------------------------
start_time = datetime.now(timezone.utc) + timedelta(hours=1)
end_time   = start_time + timedelta(hours=1)

new_event = {
    "summary": "Agent-Created Meeting",
    "description": "This event was created by a Scalekit-authenticated agent.",
    "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
    "end":   {"dateTime": end_time.isoformat(),   "timeZone": "UTC"},
}

created = requests.post(calendar_url, headers=headers, json=new_event).json()

print(f"\nCreated event: {created.get('summary')}")
print(f"  Start:  {created.get('start', {}).get('dateTime')}")
print(f"  Link:   {created.get('htmlLink')}")
