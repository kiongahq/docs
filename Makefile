.PHONY: docs-install docs-serve docs-build docs-check docs-test

# Workspace folder holding the sibling Kionga checkouts (deploy, platform, ...).
KIONGA_SRC ?= ..

docs-install:
	python -m pip install -r requirements-docs.txt

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build --strict

docs-check:          ## verify make targets, paths, env vars, routes, CLI and SDK names against the code
	python scripts/check_references.py --root $(KIONGA_SRC)

docs-test:           ## gate tests for the reference checker
	python -m pytest -q tests
