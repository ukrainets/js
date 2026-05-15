# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment first
source .venv/bin/activate

# Common tasks via Make
make run        # one-off scan
make schedule   # start the scheduler
make debug      # scan with browser visible and no log file
make populate   # populate api_url column in companies.csv after adding companies
make install    # install dependencies and Playwright browser
make test       # run full test suite
make lint       # check for linting issues (Ruff)
make format     # auto-format code (Ruff)

# Run a single test
.venv/bin/pytest tests/test_find_matches.py::test_name -v  # Example only

# Populate API URLs with validation
python populate_api_urls.py --validate
```

## Architecture

The tool scans company career pages for matching job titles. Each `run()` call in [main.py](main.py) follows this flow:

1. Load companies and titles from CSV → split into **API companies** (have `api_url`) and **Playwright companies** (don't).
2. Launch one shared `httpx.AsyncClient` and one shared Playwright browser context for the entire run.
3. Run both groups concurrently via `asyncio.gather`. API group is capped by `API_CONCURRENCY=20` semaphore; Playwright group by the `concurrency` config value (default 5 tabs).
4. Each scanner writes matches under a shared `write_lock` and checks a shared `known_urls` set to prevent duplicates within the same run and against the existing `match.csv`.

### Two scanning paths

**API path** ([crawlers/api_scanner.py](crawlers/api_scanner.py)): Generic engine — fetches an ATS API endpoint via httpx, delegates JSON parsing to a platform-specific extractor, then runs `find_matches`. All output lines are buffered per company and printed atomically to prevent interleaving.

**Playwright path** ([crawlers/scanner.py](crawlers/scanner.py)): Opens a browser tab, waits for `domcontentloaded` + a 2s settle delay (avoids `networkidle` hangs on analytics-heavy pages), extracts all `<a>` tags, runs `find_matches`. Includes one retry with extended timeout on first-attempt timeout.

### Matching logic

`find_matches` in [utils.py](utils.py) uses word-boundary regex against normalized link text. `normalize_text` strips bracket groups — `()`, `[]`, `{}` — so qualifiers like `(Remote)` or `(Contract)` are ignored on both sides. First matching title per URL wins; same URL is never returned twice.

### Adding a new ATS platform

Three files need changes:
1. Create `crawlers/api_{platform}.py` with an extractor: `(json_data: dict) -> list[tuple[str, str]]` returning `(title, absolute_url)` pairs.
2. Add one entry to `API_EXTRACTORS` in [crawlers/api_registry.py](crawlers/api_registry.py).
3. Add one entry to `PLATFORM_REGISTRY` in [populate_api_urls.py](populate_api_urls.py) (known hosts + API URL template with `{token}`), then run `make populate`.

### Key files

| File | Role |
|------|------|
| [config.py](config.py) | Constants (`PAGE_TIMEOUT`, `API_CONCURRENCY`) and `load_config()` which merges `config.json` with defaults |
| [config.json](config.json) | Runtime config — re-read before each scheduler run without restart |
| [csv_io.py](csv_io.py) | `load_companies`, `load_titles`, `load_known_urls`, `append_match_row`; includes schema migration for `match.csv` |
| [utils.py](utils.py) | `find_matches` and `normalize_text` — core matching logic |
| [populate_api_urls.py](populate_api_urls.py) | Standalone script to fill `api_url` column — run after adding companies to CSV |

### companies.csv requirements

- Only rows with `no_click == "TRUE"` are scanned.
- Sorted by `rating` descending (companies with no rating go last).
- `hr_platform` column (`greenhouse` / `ashby`) + `api_url` column determine which scanner path is used.

### match.csv schema

`id, company_name, match_title, position_title, match_position_url, time_found, reviewed, comment`

`csv_io.py` has schema migration (`_migrate_header_if_needed`) that updates the header in place when columns are added, without touching existing data rows.

### Slack notifications

`SLACK_WEBHOOK` in `.env` enables notifications. `notifications_enabled` in `config.json` is a master toggle. Match notifications fire from both `main.py` and the scheduler; scan start/done messages fire only from the scheduler.
