# Limitless API Examples — Handoff Document

## What This Repo Does

This repo is a personal productivity pipeline that turns **Limitless wearable recordings** into a structured, searchable **Google Calendar** of your day. It:

1. **Pulls conversation transcripts** ("lifelogs") from the Limitless API
2. **Summarizes each conversation** using Claude Sonnet 4.5, extracting descriptions, decisions, people involved, and conversation types
3. **Creates Google Calendar events** — one per conversation with full structured details
4. **Generates daily summary events** — an all-day event per day with themes, key decisions, and action items across all conversations
5. **Runs automatically every day** via a GitHub Actions workflow

The end result: every morning, your Google Calendar has yesterday's conversations logged as individual events plus a daily overview, all AI-summarized.

---

## Repository Structure

```
limitless-api-examples/
├── .github/workflows/
│   └── daily-sync.yml              # GitHub Action: daily automated sync
├── assets/
│   ├── chart.png                   # Screenshot for chart example
│   └── limitless-logo.svg          # Logo
├── notebooks/
│   └── chart_usage.ipynb           # Jupyter notebook for usage charts
├── python/                         # Main application code
│   ├── _client.py                  # Core Limitless API client
│   ├── batch_conversation_logger.py # THE MAIN SCRIPT — batch processes date ranges
│   ├── individual_conversation_logger.py # Per-conversation processing + calendar event creation
│   ├── daily_summary_calendar.py   # Daily summary all-day event creation
│   ├── daily_summary_generator.py  # Console-only daily summary (no calendar)
│   ├── create_daily_summaries.py   # Standalone tool to add daily summaries for specific dates
│   ├── google_calendar_integration.py # Google OAuth + Calendar/Tasks API wrapper
│   ├── export_markdown.py          # Simple: prints most recent lifelog markdown
│   ├── summarize_day.py            # Simple: summarizes day with OpenAI GPT-4o-mini
│   ├── analyze_conversations.py    # Stats and bar charts of conversation patterns
│   ├── check_calendars.py          # Lists Google calendars and IDs
│   ├── cleanup_duplicates.py       # Removes duplicate calendar events (last 30 days)
│   ├── test_conversation_calendar.py # Test: creates one test calendar event
│   ├── test_google_auth.py         # Test: verifies Google OAuth setup
│   ├── requirements.txt            # Python dependencies (pinned versions)
│   ├── credentials.json            # Google OAuth client config (gitignored, must be present locally)
│   ├── token.pickle                # Google OAuth token (gitignored, auto-generated)
│   ├── .env                        # API keys (gitignored)
│   ├── GOOGLE_OAUTH_TROUBLESHOOTING.md
│   └── TODO_CALENDAR_SETUP.md
├── typescript/                     # TypeScript versions of basic examples
│   ├── _client.ts
│   ├── export_markdown.ts
│   ├── summarize_day.ts
│   ├── package.json
│   ├── package-lock.json
│   └── tsconfig.json
├── openapi.yml                     # Limitless API spec
├── README.md                       # Public-facing README
├── HANDOFF.md                      # This file
└── .gitignore
```

---

## File-by-File Breakdown

### Core Files (the pipeline)

| File | What It Does |
|------|-------------|
| `_client.py` | Paginated client for `GET https://api.limitless.ai/v1/lifelogs`. Handles cursor-based pagination, deduplication by ID, timezone detection, and batch fetching. All other scripts import `get_lifelogs()` from here. The Limitless API key does **not** expire — it's a static key. |
| `google_calendar_integration.py` | `GoogleCalendarTodoManager` class. Handles Google OAuth (pickle-based token storage), Calendar API, Tasks API, calendar creation/lookup, event CRUD. Looks for `credentials.json` and `token.pickle` in the **current working directory**. Has retry logic for token refresh with linear backoff (2s/4s/6s, 3 attempts). Detects CI/headless environments (`CI` / `GITHUB_ACTIONS` env vars) and skips browser auth flow. Uses a calendar named **"Conversations"**. |
| `individual_conversation_logger.py` | Fetches lifelogs for a single day, filters conversations >30 seconds, sends each to **Claude Sonnet 4.5** for structured JSON summarization (6 fields: description, key_information, decisions_made, problems_solutions, people_involved, conversation_type), creates one calendar event per conversation. Supports date arguments as `YYYY-MM-DD` or negative numbers (e.g., `-3` for 3 days ago). |
| `batch_conversation_logger.py` | **The main script you'll run most often.** Wraps `individual_conversation_logger` with batch processing across date ranges. Features: rate limiting with exponential backoff, dynamic delays based on content length, duplicate detection (skips conversations already in calendar), `--force` flag to clear and recreate, `--daily-summary` flag for all-day summary events, `--summaries-only` mode. |
| `daily_summary_calendar.py` | Takes all conversations for a day, sends them to **Claude Sonnet 4.5** for a holistic daily summary, creates an all-day calendar event with themes, decisions, action items, and mood/energy. |

### Utility / Maintenance Files

| File | What It Does |
|------|-------------|
| `cleanup_duplicates.py` | Scans the last 30 days in the "Conversations" calendar, finds duplicate events (same title + start time), keeps one and deletes the rest. Skips "Daily Summary" events. Does NOT take date arguments. |
| `check_calendars.py` | Lists all Google calendars and prints their IDs. Useful for debugging. |
| `analyze_conversations.py` | Fetches 100 lifelogs and prints stats: date distribution, hourly patterns, duration analysis, bar charts. |
| `create_daily_summaries.py` | Standalone tool to add daily summary events for specific dates. Useful for backfilling. |

### Simple Example Scripts

| File | What It Does |
|------|-------------|
| `export_markdown.py` | Prints the markdown content of the most recent lifelog. |
| `summarize_day.py` | Fetches 10 lifelogs, summarizes with **GPT-4o-mini** (`OPENAI_API_KEY`), streams to console. Note: the TypeScript twin `typescript/summarize_day.ts` uses **`gpt-4.1`** instead — the two are not in sync. |
| `daily_summary_generator.py` | Console-only daily summary using **Claude 3.5 Sonnet** (older model). Not part of the main pipeline. |

### Test Scripts

| File | What It Does |
|------|-------------|
| `test_google_auth.py` | Verifies Google OAuth works, lists calendars and task lists, optionally creates a test event/task. |
| `test_conversation_calendar.py` | Fetches yesterday's lifelogs, lets you pick one, creates one test calendar event. |

---

## AI Models Used

| Script | Model | Purpose |
|--------|-------|---------|
| `batch_conversation_logger.py` | `claude-sonnet-4-5-20250929` | Individual conversation summaries |
| `individual_conversation_logger.py` | `claude-sonnet-4-5-20250929` | Individual conversation summaries |
| `daily_summary_calendar.py` | `claude-sonnet-4-5-20250929` | Daily summary events |
| `daily_summary_generator.py` | `claude-3-5-sonnet-20241022` | Console-only summaries (legacy, not in main pipeline) |
| `summarize_day.py` | `gpt-4o-mini` | Simple console summarizer |

---

## API Integrations

| API | Auth Method | Expiration | Notes |
|-----|-------------|-----------|-------|
| **Limitless API** | Static API key via `X-API-Key` header | **Does not expire** | `GET https://api.limitless.ai/v1/lifelogs` |
| **Anthropic Claude** | API key via `ANTHROPIC_API_KEY` | Does not expire (but can be revoked) | Used for all conversation and daily summarization |
| **Google Calendar/Tasks** | OAuth 2.0 with `credentials.json` + `token.pickle` | **Token expires and needs refresh** | This is the only auth that causes issues. See troubleshooting section below. |
| **OpenAI** | API key via `OPENAI_API_KEY` | Does not expire | Only used by `summarize_day.py` (not the main pipeline) |

---

## Environment Setup

### Required Files (all in `python/` directory)

1. **`.env`** — API keys:
   ```
   LIMITLESS_API_KEY=sk-your-limitless-key
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
   ```

2. **`credentials.json`** — Google OAuth client config. Download from [Google Cloud Console](https://console.cloud.google.com/) > Credentials > OAuth 2.0 Client ID (Desktop app). The Google Cloud project is called `limitless-469904`.

3. **`token.pickle`** — Auto-generated on first run after Google OAuth browser flow. Gets refreshed automatically.

All three files are gitignored.

### Python Environment

**Important:** The pinned versions in `requirements.txt` are outdated and **do not work with Python 3.13**. The `anthropic==0.40.0` package hangs on import with Python 3.13 due to pydantic compatibility issues.

To set up locally:

```bash
cd ~/Documents/GitHub/limitless-api-examples
rm -rf python/.venv
python3 -m venv python/.venv
source python/.venv/bin/activate
pip install anthropic openai python-dotenv pytz requests tzlocal google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pynacl
```

This installs latest versions instead of the pinned ones. The GitHub Action uses Python 3.11 with the pinned versions, which works fine.

---

## How to Run

### Important: Always run from the `python/` directory

All scripts look for `.env`, `credentials.json`, and `token.pickle` in the **current working directory**. You must `cd python` before running anything.

> **Which checkout has the runtime files?** There are two checkouts and **both** are now runnable:
> - `~/GitHub/LimitlessW/python/` — has `.env`, `credentials.json`, `token.pickle`, and a fresh `.venv` (Python 3.14, latest packages). This is the active copy.
> - `~/Documents/GitHub/limitless-api-examples/python/` — the original copy, also has its own `.venv`/`.env`/`credentials.json`/`token.pickle`.
>
> The two have **independent** local `token.pickle` files, and both are separate from the GitHub Actions `GOOGLE_TOKEN_PICKLE` secret. All of these gitignored files are excluded from git in both checkouts.

### The Main Command (batch process a date range)

```bash
cd ~/Documents/GitHub/limitless-api-examples/python
source .venv/bin/activate
python3 batch_conversation_logger.py --from YYYY-MM-DD --to YYYY-MM-DD --daily-summary --force
```

**Flags:**
- `--from` / `--to` — Date range (inclusive)
- `--daily-summary` — Also create all-day summary events
- `--force` — Clear existing events and recreate (use when re-running a date range)
- `--summaries-only` — Only create daily summaries, skip individual conversation events
- `--last N` — Process last N days
- Positional dates: `python3 batch_conversation_logger.py 2026-04-23 2026-04-24`
- Negative days: `python3 batch_conversation_logger.py -3 -2 -1` (3, 2, 1 days ago)

**Examples:**

```bash
# Process yesterday (default)
python3 batch_conversation_logger.py --daily-summary

# Process last 7 days with daily summaries
python3 batch_conversation_logger.py --last 7 --daily-summary

# Redo April 16-25 from scratch
python3 batch_conversation_logger.py --from 2026-04-16 --to 2026-04-25 --daily-summary --force

# Only create daily summaries for a range
python3 batch_conversation_logger.py --from 2026-04-16 --to 2026-04-25 --summaries-only
```

### Cleanup Duplicates

```bash
cd ~/Documents/GitHub/limitless-api-examples/python
source .venv/bin/activate
python3 cleanup_duplicates.py
```

Scans the last 30 days automatically. No date arguments.

### Single Day (individual logger)

```bash
python3 individual_conversation_logger.py 2026-04-25    # specific date
python3 individual_conversation_logger.py -1             # yesterday
python3 individual_conversation_logger.py                # defaults to yesterday
```

---

## GitHub Actions — Automated Daily Sync

### What It Does

The workflow at `.github/workflows/daily-sync.yml` runs **every day at 8:00 AM Eastern** (13:00 UTC) on `ubuntu-latest`. It:

1. Checks out the repo
2. Sets up Python 3.11 with pinned dependencies
3. Restores `credentials.json` and `token.pickle` from GitHub Secrets (base64-encoded)
4. Runs `batch_conversation_logger.py --daily-summary` (processes yesterday)
5. If the Google token was refreshed during the run, encrypts the new token with the repo's public key and updates the `GOOGLE_TOKEN_PICKLE` secret automatically

It can also be triggered manually from the GitHub UI via `workflow_dispatch`.

### Required GitHub Secrets

| Secret | What It Is |
|--------|-----------|
| `LIMITLESS_API_KEY` | Your Limitless API key |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GOOGLE_CREDENTIALS` | Base64-encoded `credentials.json` |
| `GOOGLE_TOKEN_PICKLE` | Base64-encoded `token.pickle` (auto-updated by the workflow) |
| `GH_PAT` | GitHub Personal Access Token with `repo` scope (needed to update secrets programmatically) |

### Local vs GitHub Action Token Independence

The local `token.pickle` on your machine and the `GOOGLE_TOKEN_PICKLE` secret on GitHub are **completely separate copies**. They both use the same OAuth client (`credentials.json`) but maintain independent sessions. Refreshing or deleting one does not affect the other. The only thing that would break both is revoking the app entirely from Google Account > Security > Third-party apps.

---

## Google OAuth Troubleshooting

### First-Time Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) (project: `limitless-469904`)
2. Ensure **Google Calendar API** and **Google Tasks API** are enabled
3. Go to Credentials > Create Credentials > OAuth 2.0 Client ID (Desktop app)
4. Download as `credentials.json`, place in `python/`
5. In **OAuth consent screen**: set to External, Testing mode, add your email as a test user
6. Run any script — browser will open for auth, creates `token.pickle`

### Token Expired / Script Hangs

If a script hangs with no output, the token is likely stale:

```bash
cd ~/Documents/GitHub/limitless-api-examples/python
rm token.pickle
source .venv/bin/activate
python3 batch_conversation_logger.py --daily-summary
```

**Important:** You must run this in **Terminal.app** (not Cursor's integrated terminal) because the OAuth flow needs to open a browser window. Cursor's shell cannot do this and will hang silently.

### "limitless has not completed the Google verification process"

See `python/GOOGLE_OAUTH_TROUBLESHOOTING.md` for full details. TL;DR: add your email as a test user in the OAuth consent screen.

---

## Known Issues and Gotchas

1. **Python 3.13 compatibility:** The pinned `requirements.txt` versions (especially `anthropic==0.40.0`) hang on import with Python 3.13. Install latest versions instead (see Environment Setup above). The GitHub Action uses Python 3.11 and works fine with pinned versions.

2. **Must run from `python/` directory:** All scripts use relative paths for `.env`, `credentials.json`, and `token.pickle`. Running from the repo root will fail silently or error on missing credentials.

3. **OAuth browser flow:** The Google OAuth flow (`flow.run_local_server()`) requires a real terminal that can open a browser. It will hang indefinitely in headless environments, CI, or Cursor's integrated terminal. Always run locally in Terminal.app for first-time auth or token refresh.

4. **Rate limiting on Anthropic:** The batch logger has built-in dynamic delays (3-9 seconds between calls, scaled by token count) and exponential backoff (multiplier 2) on rate limit errors. Processing many days takes a while — plan accordingly.

5. **Duplicate events:** If a run fails partway through and you re-run, use `--force` to clear and recreate. Otherwise, run `cleanup_duplicates.py` afterward.

6. **`TODO_CALENDAR_SETUP.md` references missing files:** It mentions `limitless_todo_calendar.py` and `todo_tracker.py` which are not in the repo. This feature was planned but not fully implemented.

---

## Common One-Liners

```bash
# Full setup from scratch
cd ~/Documents/GitHub/limitless-api-examples
python3 -m venv python/.venv
source python/.venv/bin/activate
pip install anthropic openai python-dotenv pytz requests tzlocal google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pynacl

# Process a date range
cd python && source .venv/bin/activate && python3 batch_conversation_logger.py --from 2026-04-16 --to 2026-04-28 --daily-summary --force

# Process yesterday
cd python && source .venv/bin/activate && python3 batch_conversation_logger.py --daily-summary

# Clean up duplicates
cd python && source .venv/bin/activate && python3 cleanup_duplicates.py

# Nuke venv and start fresh (if imports hang)
rm -rf python/.venv && python3 -m venv python/.venv && source python/.venv/bin/activate && pip install anthropic openai python-dotenv pytz requests tzlocal google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pynacl

# Reset Google auth (if token is stale)
rm python/token.pickle
```

---

## Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Limitless API   │────▶│  _client.py       │────▶│  batch_conversation │
│  (lifelogs)      │     │  (fetch + dedup)  │     │  _logger.py         │
└─────────────────┘     └──────────────────┘     │  (orchestrator)     │
                                                  └────────┬────────────┘
                                                           │
                                    ┌──────────────────────┼──────────────────────┐
                                    ▼                      ▼                      ▼
                         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
                         │ individual_       │   │ daily_summary_   │   │ google_calendar_ │
                         │ conversation_     │   │ calendar.py      │   │ integration.py   │
                         │ logger.py         │   │ (daily summary)  │   │ (OAuth + CRUD)   │
                         │ (per-conversation)│   └────────┬─────────┘   └────────┬─────────┘
                         └────────┬─────────┘            │                      │
                                  │                      │                      │
                                  ▼                      ▼                      ▼
                         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
                         │ Claude Sonnet 4.5│   │ Claude Sonnet 4.5│   │ Google Calendar  │
                         │ (summarize each) │   │ (summarize day)  │   │ API              │
                         └──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## Contact / Accounts

- **Limitless API Key:** Get from [limitless.ai/developers](https://limitless.ai/developers)
- **Google Cloud Project:** `limitless-469904` at [console.cloud.google.com](https://console.cloud.google.com/)
- **GitHub Repo:** [github.com/willwallwan/limitless-api-examples](https://github.com/willwallwan/limitless-api-examples) (check repo settings > Secrets for all the encrypted secrets)
- **Anthropic API:** [console.anthropic.com](https://console.anthropic.com/)
