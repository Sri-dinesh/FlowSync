PYTHON ?= $(firstword $(wildcard server/.venv/bin/python server/venv/bin/python) python3)

.PHONY: check-repository lint typecheck test build check server client

check-repository:
	$(PYTHON) scripts/check_repository.py

lint:
	npm --prefix client run lint

typecheck:
	npm --prefix client run typecheck

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest server/tests --no-cov -p no:cacheprovider

build:
	npm --prefix client run build

check: check-repository lint typecheck test

server:
	$(PYTHON) -m uvicorn app.main:app --app-dir server --reload --port 8000

client:
	npm --prefix client run dev
