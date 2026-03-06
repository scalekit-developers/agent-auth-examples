# Python Examples

**Note: The Scalekit SDK is a work in progress.**

## Examples

| Script | Connector(s) | What it does |
|--------|--------------|--------------|
| [email_triage_agent.py](email_triage_agent.py) | Gmail | Fetches unread emails, categorizes by priority (URGENT / REPLY NEEDED / FYI / PROMO), and auto-drafts replies |
| [meeting_scheduler_agent.py](meeting_scheduler_agent.py) | Google Calendar + Gmail | Finds a free slot in the next 3 days, creates a calendar event, and drafts a confirmation email |
| [daily_briefing_agent.py](daily_briefing_agent.py) | Gmail + Google Calendar | Prints a morning digest of today's calendar events and unread emails |

## Setup

**1. Create and activate a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Configure credentials** — copy `.env.example` from the repo root and fill in your values:

```bash
cp ../.env.example ../.env
# Edit .env with values from app.scalekit.com → Developers → Settings → API Credentials
```

## Usage

Make sure the virtual environment is active (`source .venv/bin/activate`), then:

```bash
python email_triage_agent.py
python meeting_scheduler_agent.py
python daily_briefing_agent.py
```

## Dashboard Setup (required for all connectors)

All scripts require a one-time connection setup in the Scalekit Dashboard before they can run.

1. Go to **Scalekit Dashboard → Agent Auth → Connections**
2. Click **+ Create Connection**
3. Create each connector with the exact Connection Name shown below:

| Script | Connector | Connection Name |
|--------|-----------|----------------|
| `email_triage_agent.py` | Gmail | `gmail` |
| `meeting_scheduler_agent.py` | Google Calendar | `googlecalendar` |
| `meeting_scheduler_agent.py` | Gmail | `gmail` |
| `daily_briefing_agent.py` | Gmail | `gmail` |
| `daily_briefing_agent.py` | Google Calendar | `googlecalendar` |

4. Click **Save** for each

> The Connection Name must match the value used in the script exactly. You only need to create each connector once — `gmail` and `googlecalendar` can be shared across scripts.

## First-Run Authorization

On the first run, the script will print an authorization link and pause:

```
Authorize gmail here: https://your-env.scalekit.dev/magicLink/...
Press Enter after completing authorization...
```

1. Open the link in your browser
2. Sign in with the Google account you want to connect
3. Grant the requested permissions
4. Return to the terminal and press **Enter**

Scripts that use two connectors (Calendar + Gmail) will prompt for each separately on first run. On all subsequent runs, Scalekit uses the stored token (auto-refreshed as needed) and skips this step entirely.

## How It Works

Each script follows the same pattern:

1. **Initialize** the Scalekit client with your credentials
2. **Get or create** a connected account for the user
3. **Authorize** — if the account isn't active, the user completes OAuth via the printed link
4. **Fetch token** — Scalekit returns a fresh access token (auto-refreshed as needed)
5. **Call the API** — use the token as a Bearer token with the Google REST API
