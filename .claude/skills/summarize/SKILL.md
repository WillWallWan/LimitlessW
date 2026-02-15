---
name: summarize
description: Sync and summarize Limitless conversations to Google Calendar
argument-hint: (optional dates in plain English)
---

You are a helper that runs the Limitless conversation sync pipeline. This creates individual calendar events for each conversation AND an all-day daily summary event.

## What to do

1. **Ask the user what dates they want summarized** if they didn't already specify in `$ARGUMENTS`. They can answer in plain English (e.g. "yesterday", "last 3 days", "Feb 1 through Feb 10", "today", "this week", etc.).

2. **Translate their answer into the correct CLI flags** for `batch_conversation_logger.py`:
   - "yesterday" or no answer → no date flags needed (yesterday is the default)
   - "today" → `--from YYYY-MM-DD --to YYYY-MM-DD` using today's date
   - "last N days" → `--last N`
   - A date range → `--from YYYY-MM-DD --to YYYY-MM-DD`
   - Specific dates → pass them as positional args in `YYYY-MM-DD` format
   - Relative like "3 days ago" → `-3`

3. **Run the command**:
   ```bash
   cd /Users/willwallwan/Documents/GitHub/limitless-api-examples/python && python3 batch_conversation_logger.py <date-flags> --daily-summary
   ```

   Always include `--daily-summary` to create both individual events and the all-day summary.

4. **Report the results** back to the user — how many conversations were found, events created, duplicates skipped, etc.

## Important notes

- Never use `--force` unless the user explicitly asks to recreate/overwrite existing events.
- Never use `--summaries-only` unless the user explicitly asks to skip individual events.
- Duplicate detection is built in — safe to run multiple times for the same dates.
- The script requires `LIMITLESS_API_KEY` and `ANTHROPIC_API_KEY` in the `.env` file and Google OAuth credentials in `python/credentials.json`.
- The script can take a while for large date ranges due to API rate limits. Let the user know if it's going to be a long run.
