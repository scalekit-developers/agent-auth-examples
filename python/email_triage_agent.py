"""
Use Case 1: AI Email Triage & Draft Replies Agent
---------------------------------------------------
Fetches unread Gmail messages, categorizes them by priority, and
auto-creates a draft reply for emails that need a response.

Setup:
    pip install -r requirements.txt

Required env vars (.env):
    SCALEKIT_CLIENT_ID, SCALEKIT_CLIENT_SECRET, SCALEKIT_ENVIRONMENT_URL

Dashboard setup:
    Agent Auth → Connections → + Create Connection → Gmail → Name: "gmail"
"""

import os
import base64
import json
import requests
import scalekit.client
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

USER_ID   = "user_123"
CONNECTOR = "gmail"

# ---------------------------------------------------------------------------
# Get or create connected account, authorize if needed
# ---------------------------------------------------------------------------
response = actions.get_or_create_connected_account(connection_name=CONNECTOR, identifier=USER_ID)
connected_account = response.connected_account

if connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(connection_name=CONNECTOR, identifier=USER_ID)
    print("Authorize here:", link.link)
    input("Press Enter after completing authorization...")

tokens       = actions.get_connected_account(connection_name=CONNECTOR, identifier=USER_ID)
access_token = tokens.connected_account.authorization_details["oauth_token"]["access_token"]
headers      = {"Authorization": f"Bearer {access_token}"}
gmail_url    = "https://gmail.googleapis.com/gmail/v1/users/me"

# ---------------------------------------------------------------------------
# Triage categories
# ---------------------------------------------------------------------------
URGENT_KEYWORDS   = ["urgent", "action required", "asap", "immediately", "critical", "important"]
PROMO_SENDERS     = ["noreply@", "no-reply@", "newsletter@", "notifications@", "updates@",
                     "offers@", "deals@", "promotions@", "mailer@", "emailer"]
REPLY_NEEDED_WORDS = ["please reply", "let me know", "your thoughts", "can you", "could you",
                      "waiting for", "response needed", "get back to me"]

def classify(sender: str, subject: str, snippet: str) -> str:
    text = f"{subject} {snippet}".lower()
    sender_lower = sender.lower()
    if any(k in text for k in URGENT_KEYWORDS):
        return "URGENT"
    if any(p in sender_lower for p in PROMO_SENDERS):
        return "PROMO/NEWSLETTER"
    if any(k in text for k in REPLY_NEEDED_WORDS):
        return "REPLY NEEDED"
    return "FYI"

def draft_reply(access_token: str, message_id: str, thread_id: str,
                to: str, subject: str) -> str:
    """Create a draft reply in Gmail and return its ID."""
    reply_body = (
        f"Hi,\n\nThank you for your email regarding '{subject}'.\n\n"
        "I'll review this and get back to you shortly.\n\nBest regards"
    )
    msg = MIMEText(reply_body)
    msg["To"]      = to
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg["In-Reply-To"] = message_id
    msg["References"]  = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"message": {"raw": raw, "threadId": thread_id}}

    resp = requests.post(
        f"{gmail_url}/drafts",
        headers={**headers, "Content-Type": "application/json"},
        json=body,
    ).json()
    return resp.get("id", "unknown")

# ---------------------------------------------------------------------------
# Fetch up to 15 unread messages and triage them
# ---------------------------------------------------------------------------
messages = requests.get(
    f"{gmail_url}/messages",
    headers=headers,
    params={"q": "is:unread", "maxResults": 15},
).json().get("messages", [])

triage = {"URGENT": [], "REPLY NEEDED": [], "FYI": [], "PROMO/NEWSLETTER": []}

print(f"\nTriaging {len(messages)} unread emails...\n" + "=" * 60)

for msg in messages:
    data = requests.get(
        f"{gmail_url}/messages/{msg['id']}",
        headers=headers,
        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
    ).json()

    hdrs     = data.get("payload", {}).get("headers", [])
    subject  = next((h["value"] for h in hdrs if h["name"] == "Subject"), "(no subject)")
    sender   = next((h["value"] for h in hdrs if h["name"] == "From"),    "Unknown")
    snippet  = data.get("snippet", "")
    thread   = data.get("threadId", "")

    category = classify(sender, subject, snippet)
    triage[category].append({
        "id": msg["id"], "thread": thread,
        "subject": subject, "sender": sender, "snippet": snippet,
    })

# ---------------------------------------------------------------------------
# Print triage report
# ---------------------------------------------------------------------------
ICONS = {"URGENT": "🔴", "REPLY NEEDED": "🟡", "FYI": "🔵", "PROMO/NEWSLETTER": "⚪"}

for category, emails in triage.items():
    if not emails:
        continue
    print(f"\n{ICONS[category]} {category} ({len(emails)})")
    print("-" * 50)
    for e in emails:
        print(f"  From:    {e['sender']}")
        print(f"  Subject: {e['subject']}")
        print(f"  Snippet: {e['snippet'][:100]}...")
        print()

# ---------------------------------------------------------------------------
# Auto-draft replies for "REPLY NEEDED" emails
# ---------------------------------------------------------------------------
if triage["REPLY NEEDED"]:
    print(f"\n✍️  Auto-drafting replies for {len(triage['REPLY NEEDED'])} email(s)...")
    print("-" * 50)
    for e in triage["REPLY NEEDED"]:
        draft_id = draft_reply(access_token, e["id"], e["thread"], e["sender"], e["subject"])
        print(f"  Draft created (ID: {draft_id}) → Re: {e['subject']}")

print(f"\n✅ Triage complete. {len(triage['URGENT'])} urgent, "
      f"{len(triage['REPLY NEEDED'])} drafts created, "
      f"{len(triage['FYI'])} FYI, {len(triage['PROMO/NEWSLETTER'])} promos.")
