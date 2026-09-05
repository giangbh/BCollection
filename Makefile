PYTHON ?= .venv/bin/python

.PHONY: install test init-db seed-demo api frontend-install frontend-build
install:
	$(PYTHON) -m pip install -r requirements-dev.txt
test:
	$(PYTHON) -m pytest -q
init-db:
	$(PYTHON) scripts/bcollection.py --mode demo init-db
seed-demo:
	$(PYTHON) scripts/bcollection.py --mode demo seed-demo
api:
	$(PYTHON) scripts/bcollection.py --mode demo serve
frontend-install:
	npm --prefix bcollection-platform/apps/collector-workspace ci
frontend-build:
	npm --prefix bcollection-platform/apps/collector-workspace run build
