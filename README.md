# JS — Job Search Automation

A CLI tool that automates scanning company career pages for matching QA/SQA job titles.

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

---

## Run

```bash
python main.py
```

### Optional flags
```bash
python main.py --concurrency 10                       # override tab count from config
python main.py --companies input_data/companies.csv   # override companies file from config
python main.py --titles input_data/sqa_titles.csv     # override titles file from config
python main.py --no-headless                          # run with visible browser window (useful for debugging)
```
---

## How It Works

### Input Files
| File | Columns Used | Purpose |
|------|-------------|---------|
| `input_data/companies.csv` | `company_name`, `open_positions_url` | List of companies and their careers page URLs |
| `input_data/sqa_titles.csv` | `title` | Job titles to search for |

### Core Logic
1. **Load config** — reads `config.json` for concurrency limit and CSV file paths
2. **Load companies** — reads companies CSV, extracts `company_name` + `open_positions_url`, deduplicates
3. **Load titles** — reads titles CSV, extracts `title` column, deduplicates
4. **Launch browser** — starts a single headless Chromium instance via async Playwright
5. **Scan companies concurrently** — up to `concurrency` tabs open at the same time (controlled by semaphore):
   - Navigate to `open_positions_url` and wait for the page to fully load
   - Extract all anchor elements (`<a>` tags) — capturing both link text and URL
   - Match each title against the link text (exact, case-insensitive, line by line)
   - If a match is found, log the title and its direct job posting URL to the console
6. **Print summary** — elapsed time, companies searched, and matches found

### Matching
Matches titles against anchor (`<a>`) link text — not the full page text blob. Each link's text is split line by line and compared exactly (case-insensitive) against titles.
- `"QA Automation Engineer"` matches a link labelled `"QA Automation Engineer"` regardless of casing
- `"Automation Engineer"` does **not** match a link labelled `"Cloud Test Automation Engineer"` — must be an exact line match
- The matched job URL is pulled directly from the link's `href`
- Title variations are covered by the breadth of `sqa_titles.csv` (e.g. both `"Sr. QA Engineer"` and `"Senior QA Engineer"` are listed)

### Console Output
```
Start time        : 09:03
Companies loaded  : 13
Titles loaded     : 144
Concurrency       : 5 tab(s)
Headless          : True
────────────────────────────────────────────────────────────

🔎  Scanning : Litify - https://job-boards.greenhouse.io/litify/
✅  Match for: [QA Automation Engineer] https://job-boards.greenhouse.io/litify/jobs/7601828
✅  Match for: [Senior QA Engineer] https://job-boards.greenhouse.io/litify/jobs/7601901

🔎  Scanning : Acme Corp - https://jobs.ashbyhq.com/acme/
❌  No matches found

────────────────────────────────────────────────────────────
🏁  Done in 2min. 30sec.
   - end time  : 09:05
   - searched  : 13 companies
   - found     : 2 match(es)
```
---

## Configuration

Edit `config.json` to set your defaults:

```json
{
  "concurrency":    5,
  "companies_file": "input_data/companies.csv",
  "titles_file":    "input_data/sqa_titles.csv"
}
```

| Key | Description |
|-----|-------------|
| `concurrency` | Number of browser tabs open simultaneously. Start at `5`, raise to `10–15` for larger lists |
| `companies_file` | Path to your companies CSV |
| `titles_file` | Path to your job titles CSV |

All values can be overridden at runtime via CLI flags.

---

## Project Structure
```
job_search/
├── input_data/
│   ├── companies.csv       # Company names and career page URLs
│   └── sqa_titles.csv      # Job titles to match against
├── main.py                 # Entry point and core logic
├── config.json             # Runtime configuration (concurrency, file paths)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Dependencies
| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser — handles JS-rendered career pages |
