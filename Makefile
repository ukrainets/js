PYTHON     := .venv/bin/python
PYTEST     := .venv/bin/pytest
RUFF       := .venv/bin/ruff
PIP        := .venv/bin/pip
PLAYWRIGHT := .venv/bin/playwright

.PHONY: run schedule test populate debug install lint format

run:
	$(PYTHON) main.py

schedule:
	$(PYTHON) scheduler.py

test:
	$(PYTEST) tests/ -v

populate:
	$(PYTHON) populate_api_urls.py

debug:
	$(PYTHON) main.py --no-headless --no-log

install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt && $(PLAYWRIGHT) install chromium

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
