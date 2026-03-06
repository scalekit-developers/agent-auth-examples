"""
Google (Gmail) Agent Auth Example
----------------------------------
Demonstrates using Scalekit Agent Auth to authenticate an AI agent
and fetch the last 5 unread Gmail messages on behalf of a user.

Setup:
    pip install scalekit-sdk-python python-dotenv requests

Required env vars (.env):
    SCALEKIT_CLIENT_ID
    SCALEKIT_CLIENT_SECRET
    SCALEKIT_ENV_URL

Note: Gmail does NOT require dashboard setup — it works out of the box.
"""

import os
import requests
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

USER_ID = "user_123"          # Replace with your actual user identifier
CONNECTOR = "gmail"

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

# ---------------------------------------------------------------------------
# 5. Call the Gmail API using the access token
# ---------------------------------------------------------------------------
headers = {"Authorization": f"Bearer {access_token}"}
list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

messages = requests.get(
    list_url,
    headers=headers,
    params={"q": "is:unread", "maxResults": 5},
).json().get("messages", [])

print(f"\nLast {len(messages)} unread messages:\n" + "-" * 50)

for msg in messages:
    data = requests.get(
        f"{list_url}/{msg['id']}",
        headers=headers,
        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
    ).json()

    hdrs = data.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in hdrs if h["name"] == "Subject"), "No Subject")
    sender  = next((h["value"] for h in hdrs if h["name"] == "From"),    "Unknown")
    date    = next((h["value"] for h in hdrs if h["name"] == "Date"),    "Unknown")

    print(f"From:    {sender}")
    print(f"Date:    {date}")
    print(f"Subject: {subject}")
    print(f"Snippet: {data.get('snippet', '')}")
    print("-" * 50)
