# JS — Job Search

A tool that automates scanning companies career pages for matching job titles.

**Purpose**  
This tool is better suited to a passive job search than an active one.  
You create a list of companies that are interesting for you to work at, and a list of job titles that suit your next position.  
The tool periodically scans the careers pages for matching job titles.  

---

## Setup

### Prerequisites
- Python 3.9+
- pip

### Install dependencies
```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright's Chromium browser
playwright install chromium
```
4. Copy companies.csv and sqa_titles.csv files from `test/test_data` to `data` folder


### Slack notifications (optional)
```bash
# Copy the example env file and add your webhook URL
cp .env.example .env
```
Get a webhook URL at [api.slack.com/messaging/webhooks](https://api.slack.com/messaging/webhooks) and paste it into `.env`:
```
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```
If `SLACK_WEBHOOK` is not set, the app runs normally with no notifications.

---

## Tests & Linting

```bash
make test     # run test suite
make lint     # check for linting issues
make format   # auto-format code
```

---

## Run

### Main commands
```bash
make run        # one-off scan
make schedule   # start the scheduler
make debug      # scan with browser visible and no log file (useful for debugging)
make populate   # populate api_url column in companies.csv after adding new companies
make install    # install dependencies and Playwright browser
make lint       # check for linting issues (Ruff)
make format     # auto-format code (Ruff)
```

### All commands

#### One-off scan
```bash
python main.py
```

#### Optional flags
```bash
python main.py --concurrency 10                  # override tab count from config
python main.py --companies data/companies.csv    # override companies file
python main.py --titles data/sqa_titles.csv      # override titles file
python main.py --output data/match.csv           # override output file
python main.py --no-headless                     # show browser window (useful for debugging)
python main.py --no-log                          # skip log file for this run
```

#### Scheduler
Runs a scan automatically at the times configured in `config.json` (`schedule_times`).

```bash
python scheduler.py             # start scheduler, wait for first scheduled time
python scheduler.py --run-now   # run a scan immediately, then follow the schedule
```

---

## How It Works

### Input Files
| File | Columns Used | Purpose |
|------|-------------|---------|
| `data/companies.csv` | `company_name`, `open_positions_url` | List of companies and their careers page URLs |
| `data/sqa_titles.csv` | `title` | Job titles to search for |

### Core Logic
1. **Load config** — reads `config.json` for concurrency limit and CSV file paths
2. **Load companies** — reads companies CSV, extracts `company_name` + `open_positions_url`, deduplicates
3. **Load titles** — reads titles CSV, extracts `title` column, deduplicates
4. **Launch browser** — starts a single headless Chromium instance via async Playwright
5. **Scan companies concurrently** — companies with a populated `api_url` are routed to the API scanner; the rest use Playwright:
   - **API path** (Greenhouse, Ashby): sends an HTTP GET to `api_url`, parses JSON, extracts job titles and URLs via a per-platform extractor. Ashby filters out `isListed=false` jobs. Up to `API_CONCURRENCY` (20) requests run in parallel.
   - **Playwright path**: opens up to `concurrency` browser tabs; navigates to `open_positions_url`, extracts all `<a>` tags, matches titles against link text
   - If a new match is found, it is written to `data/match.csv` and (if configured) a Slack notification is sent
6. **Print summary** — elapsed time, companies searched, and matches found

### Matching
Matches titles against anchor (`<a>`) link text — not the full page text blob. Each link's text is split line by line and compared against titles using word-boundary contains matching (case-insensitive).
- A title matches if it appears as a **complete word sequence** anywhere within the link text
- Bracket groups — `()`, `[]`, `{}` — are stripped from both sides before comparison, so qualifiers like `(Contract)`, `(Remote)`, or `(Mid level SDET)` are ignored
- `"Automation Engineer"` matches `"Automation Engineer (Mid level SDET)"` and `"Cloud Test Automation Engineer"`
- `"QA Lead"` does **not** match `"Squad Leader"` — word boundaries prevent partial-word collisions
- The matched job URL is pulled directly from the link's `href`
- First matching title wins per URL; the same URL is never returned twice
- Title variations are covered by the breadth of `sqa_titles.csv` (e.g. both `"Sr. QA Engineer"` and `"Senior QA Engineer"` are listed)

### Duplicate detection
Before writing a match, the app checks `data/match.csv` for the URL. Duplicates are skipped silently — re-running the scanner never adds the same position twice.

### Console Output example
```
Start time        : 09:03
Companies to scan : 276  (no_click=TRUE, sorted by rating ↓)
Titles loaded     : 144
Concurrency       : 5 tab(s)
Headless          : True
────────────────────────────────────────────────────────────

🔎  Scanning : Litify - https://job-boards.greenhouse.io/litify/
✅  Match for: [QA Automation Engineer] https://job-boards.greenhouse.io/litify/jobs/7601828
🟢  added to output file

🔎  Scanning : Acme Corp - https://jobs.ashbyhq.com/acme/
❌  No matches found

────────────────────────────────────────────────────────────
🏁  Done in 2min. 30sec.
   - end time  : 09:05
   - searched  : 276 companies
   - found     : 1 new match(es)
📄  New results saved to: data/match.csv
```

---

## Scheduler

The scheduler runs the scan automatically at configured times every day.

```bash
python scheduler.py
```

On startup it prints the registered times and the next run timestamp:
```
🚀  Scheduler started — running every day at: 08:08, 13:13, 18:18
    Next run : 2026-03-17 08:08
    Press Ctrl+C to stop.
```

**Behaviour:**
- Times are read from `config.json` on each scheduler start
- Config is re-read before every scan — edit `config.json` without restarting the scheduler
- If a scan crashes (network down, Playwright error), the error is logged and the scheduler continues to the next run
- Use `--run-now` to trigger an immediate scan on startup before waiting for the first scheduled time

---

## Slack Notifications

When `SLACK_WEBHOOK` is set in `.env`, the app sends three types of messages:

| Event | Message |
|---|---|
| Scheduled scan starts | `🔎 Scheduled scan started for 276 companies.` |
| New match found (real-time) | `🥳 New match found: Acme Corp - QA Engineer`<br>`https://jobs.acme.com/123` |
| Scan complete | `✅ Scan done in 3min. 1 new match(es) found.` or `ℹ️ Scan done in 3min. No new matches found.` |

**Notes:**
- Match notifications fire immediately when a match is saved — not after all companies finish scanning
- Scan start and completion messages are sent only from the scheduler (`python scheduler.py`)
- Match notifications fire from both `python main.py` and the scheduler
- If Slack is unreachable, a warning is printed but the scan continues

---

## Configuration

Edit `config.json` to set your defaults:

```json
{
  "concurrency": 5,
  "companies_file": "data/companies.csv",
  "titles_file": "data/sqa_titles.csv",
  "output_file": "data/match.csv",
  "schedule_times": ["08:00", "13:00"],
  "notifications_enabled": true,
  "logging_enabled": true,
  "log_dir": "logs",
  "log_retention_days": 30
}
```

| Key | Description |
|-----|-------------|
| `concurrency` | Number of browser tabs open simultaneously. Start at `5`, raise to `10–15` for larger lists |
| `companies_file` | Path to your companies CSV |
| `titles_file` | Path to your job titles CSV |
| `output_file` | Path to the output CSV for matched positions |
| `schedule_times` | List of daily run times in `HH:MM` format. Add or remove times as needed |
| `notifications_enabled` | Set to `false` to disable all Slack notifications (useful for test runs) |
| `logging_enabled` | Set to `false` to disable log file creation globally |
| `log_dir` | Directory where log files are saved (created automatically if missing) |
| `log_retention_days` | Log files older than this many days are deleted on each scan start |

All file path values can be overridden at runtime via CLI flags.

---

## Logging

Each scan run automatically saves all console output to a markdown log file in the `logs/` directory.

**Log filename format:** `yyyy.mm.dd_hh-mm-ss_js_run.md`

**Log file structure:**
```
# JS Run Log
**Date:** 2026.05.04
**Start time:** 09:03
**Trigger:** manual | scheduler

---

` `` `
... full scan output ...
` `` `
```

**Behaviour:**
- The `logs/` directory is created automatically on first run
- Each run produces a separate file — seconds in the filename prevent collisions if two scans start within the same minute
- Log files older than `log_retention_days` days are deleted silently at the start of each scan
- Log files are never committed to the repository (`logs/` is in `.gitignore`)
- If log file creation fails for any reason, the scan continues normally

**Disabling logging:**
- For a single run: `python main.py --no-log`
- Permanently: set `"logging_enabled": false` in `config.json`

---

## Project Structure
```
job_search/
├── data/
│   ├── companies.csv           # Company names and career page URLs
│   ├── sqa_titles.csv          # Job titles to match against
│   └── match.csv               # Output — matched positions (auto-created)
├── crawlers/
│   ├── scanner.py              # Async Playwright career page scanner
│   ├── api_scanner.py          # Generic async API scanner engine
│   ├── api_registry.py         # Platform → extractor dispatch table
│   ├── api_greenhouse.py       # Greenhouse JSON extractor
│   └── api_ashby.py            # Ashby JSON extractor (filters isListed=false)
├── integrations/
│   ├── notifier.py             # Slack notifications via webhook
│   └── scheduler.py            # Scheduler logic (times, run loop)
├── tests/                      # Test suite
├── logs/                           # Per-run log files (git-ignored, auto-created)
├── main.py                     # Entry point — one-off scan
├── scheduler.py                # Entry point — scheduled scan
├── logger.py                   # Scan run logging (Tee stdout → markdown file)
├── config.py                   # Constants and config loader
├── csv_io.py                   # CSV read/write functions
├── utils.py                    # Shared helpers
├── config.json                 # Runtime configuration
├── .env.example                # Slack webhook setup template
├── requirements.txt            # Python dependencies
└── README.md
```

---

## Dependencies
| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser — handles JS-rendered career pages |
| `schedule` | Time-based job scheduling for the scheduler |
| `requests` | HTTP client for Slack webhook calls |
| `python-dotenv` | Loads `SLACK_WEBHOOK` from `.env` file |

## Contributors
- Vasyl S. 
- Claude (Anthropic AI) — assisted codding, research & CTO.