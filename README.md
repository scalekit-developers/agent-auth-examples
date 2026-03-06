# Scalekit Agent Auth Examples

This repository hosts examples of the agent auth capabilities of Scalekit.

**Note: This project is a work in progress.**

## What is Agent Auth?

Scalekit Agent Auth handles the full OAuth lifecycle — authorization, token storage, and automatic refresh — so AI agents can act on behalf of users in Gmail, Google Calendar, Slack, Notion, and other connectors.

## Examples

| Language | Use Case | Connector(s) | File |
|----------|----------|--------------|------|
| Python | AI Email Triage & Draft Replies | Gmail | [python/email_triage_agent.py](python/email_triage_agent.py) |
| Python | Meeting Scheduler | Google Calendar + Gmail | [python/meeting_scheduler_agent.py](python/meeting_scheduler_agent.py) |
| Python | Daily Briefing / Morning Digest | Gmail + Google Calendar | [python/daily_briefing_agent.py](python/daily_briefing_agent.py) |

## Getting Started

### 1. Set up credentials

```bash
cp .env.example .env
# Edit .env with your values from app.scalekit.com → Developers → Settings → API Credentials
```

### 2. Install dependencies

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run an example

```bash
python email_triage_agent.py
python meeting_scheduler_agent.py
python daily_briefing_agent.py
```

## Dashboard Setup (required for all connectors)

All scripts require a one-time connection setup in the Scalekit Dashboard before running.

1. Go to **Scalekit Dashboard → Agent Auth → Connections**
2. Click **+ Create Connection**
3. Select the connector and set the **Connection Name** exactly as shown below:

| Connector | Connection Name |
|-----------|----------------|
| Gmail | `gmail` |
| Google Calendar | `googlecalendar` |

4. Click **Save**

> The Connection Name must match the `connection_name` value in the script exactly.

## First-Run Authorization

The first time you run a script, the user hasn't authorized access yet. The script will print an authorization link and wait:

```
Authorize access here: https://your-env.scalekit.dev/magicLink/...
Press Enter after completing authorization...
```

1. Open the link in your browser
2. Sign in with the Google account you want to connect
3. Grant the requested permissions
4. Return to the terminal and press **Enter**

On all subsequent runs, Scalekit uses the stored token (auto-refreshed as needed) and skips the authorization step entirely.