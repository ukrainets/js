# JS — Job Search Automation

A CLI tool that automates scanning company career pages for matching QA/SQA job titles.

---

## How It Works

### Input Files
| File | Columns Used | Purpose |
|------|-------------|---------|
| `input_data/companies.csv` | `company_name`, `open_positions_url` | List of companies and their careers page URLs |
| `input_data/sqa_titles.csv` | `title` | Job titles to search for |

### Core Logic
1. **Load companies** — reads `companies.csv`, extracts `company_name` + `open_positions_url`, deduplicates
2. **Load titles** — reads `sqa_titles.csv`, extracts `title` column, deduplicates
3. **Launch browser** — starts a headless Chromium instance via Playwright (handles JS-rendered ATS platforms like Greenhouse, Ashby, Rippling)
4. **For each company:**
   - Navigate to `open_positions_url` and wait for the page to fully load
   - Extract all anchor elements (`<a>` tags) — capturing both link text and URL
   - Match each title against the link text (exact, case-insensitive, line by line)
   - If a match is found, log the title and its direct job posting URL to the console
5. **Print summary** — total companies searched and total matches found

### Matching
Matches titles against anchor (`<a>`) link text — not the full page text blob. Each link's text is split line by line and compared exactly (case-insensitive) against titles.
- `"QA Automation Engineer"` matches a link labelled `"QA Automation Engineer"` regardless of casing
- `"Automation Engineer"` does **not** match a link labelled `"Cloud Test Automation Engineer"` — must be an exact line match
- The matched job URL is pulled directly from the link's `href`
- Title variations are covered by the breadth of `sqa_titles.csv` (e.g. both `"Sr. QA Engineer"` and `"Senior QA Engineer"` are listed)

### Console Output
```
🔎  Scanning : Litify - https://job-boards.greenhouse.io/litify/
✅  Match for: [QA Automation Engineer] https://job-boards.greenhouse.io/litify/jobs/7601828
✅  Match for: [Senior QA Engineer] https://job-boards.greenhouse.io/litify/jobs/7601901

🔎  Scanning : Acme Corp - https://jobs.ashbyhq.com/acme/
❌  No matches found

────────────────────────────────────────────────────────────
🏁  Done — searched 13 companies, found 2 matching position(s)
```

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
python main.py --companies input_data/companies.csv   # custom companies file path
python main.py --titles input_data/sqa_titles.csv     # custom titles file path
python main.py --no-headless                          # run with visible browser window (useful for debugging)
```

---

## Project Structure
```
job_search/
├── input_data/
│   ├── companies.csv       # Company names and career page URLs
│   └── sqa_titles.csv      # Job titles to match against
├── main.py                 # Entry point and core logic
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Dependencies
| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser — handles JS-rendered career pages |
