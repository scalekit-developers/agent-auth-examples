# Python Examples

**Note: The Scalekit SDK is a work in progress.**

## Examples

| Script | Connector | What it does |
|--------|-----------|--------------|
| [google_agent.py](google_agent.py) | Gmail | Fetches the last 5 unread Gmail messages |
| [google_calendar_agent.py](google_calendar_agent.py) | Google Calendar | Lists upcoming events and creates a new event |

## Setup

**Install dependencies:**

```bash
pip install scalekit-sdk-python python-dotenv requests
```

**Configure credentials** — copy `.env.example` from the repo root and fill in your values:

```bash
cp ../.env.example ../.env
# Edit .env with values from app.scalekit.com → Developers → Settings → API Credentials
```

## Usage

```bash
# Gmail — no dashboard setup required
python google_agent.py

# Google Calendar — requires dashboard setup (see below)
python google_calendar_agent.py
```

## Google Calendar Dashboard Setup (one-time)

1. Go to **Scalekit Dashboard → Agent Auth → Connections**
2. Click **+ Create Connection** → Select **Google Calendar**
3. Set Connection Name to `google-calendar`
4. Click **Save**

## How It Works

Each script follows the same four-step pattern:

1. **Initialize** the Scalekit client with your credentials
2. **Get or create** a connected account for the user
3. **Authorize** — if the account isn't active, the user completes OAuth via a printed link
4. **Fetch token** — Scalekit returns a fresh access token (auto-refreshed as needed)
5. **Call the API** — use the token as a Bearer token with the Google REST API