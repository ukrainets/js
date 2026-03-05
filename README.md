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
   - Extract all visible text content from the page
   - Run fuzzy matching of every title against the page text using `rapidfuzz`
   - If a match exceeds the similarity threshold (default: 80%), log it to the console immediately
5. **Print summary** — total companies searched and total matches found

### Fuzzy Matching
Uses `rapidfuzz` partial ratio scoring to catch title variations:
- Abbreviations: `Sr.` vs `Sr` vs `Senior`
- Casing differences: `QA engineer` vs `QA Engineer`
- Minor word order or punctuation differences

Match threshold is a configurable constant (`MATCH_THRESHOLD`) in `main.py`.

### Console Output
```
[MATCH] Litify | https://job-boards.greenhouse.io/litify/ | QA Automation Engineer (score: 92%)
[MATCH] 1Password | https://jobs.ashbyhq.com/1password | Senior QA Engineer (score: 88%)
...
---
Searched: 13 companies | Matches found: 2
```

---

## Setup

### Prerequisites
- Python 3.9+
- pip

### Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Run

```bash
python main.py
```

### Optional flags
```bash
python main.py --threshold 85        # set custom fuzzy match threshold (default: 80)
python main.py --companies input_data/companies.csv   # custom companies file path
python main.py --titles input_data/sqa_titles.csv     # custom titles file path
python main.py --no-headless         # run with visible browser window (useful for debugging)
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
| `rapidfuzz` | Fuzzy string matching for job title detection |
