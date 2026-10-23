.PHONY: docs-install docs-serve docs-serve-engineering docs-build docs-check docs-lint docs-diagrams docs-test

# Workspace folder holding the sibling Kionga checkouts (deploy, platform, ...).
KIONGA_SRC ?= ..
# Material for MkDocs prints a notice about MkDocs 2.0 on every build.
export DISABLE_MKDOCS_2_WARNING := true

docs-install:
	python -m pip install -r requirements-docs.txt

docs-serve:          ## product documentation, http://127.0.0.1:8000
	mkdocs serve

docs-serve-engineering: ## engineering handbook, http://127.0.0.1:8001
	mkdocs serve -f engineering/mkdocs.yml -a 127.0.0.1:8001

docs-build:          ## both sites, strict; the handbook is published under /engineering/
	mkdocs build --strict --site-dir site
	mkdocs build --strict -f engineering/mkdocs.yml --site-dir ../site/engineering

docs-check:          ## references against the code; product pages also keep code internals out
	python scripts/check_references.py --root $(KIONGA_SRC) --product
	python scripts/check_references.py --root $(KIONGA_SRC) --docs engineering/docs

docs-lint:           ## prose: Google developer documentation style via Vale (errors fail)
	vale sync >/dev/null
	vale --minAlertLevel=error docs engineering/docs

docs-diagrams:       ## every mermaid diagram parses (needs Node)
	npm install --prefix scripts --no-audit --no-fund --silent
	node scripts/check_mermaid.mjs docs engineering/docs

docs-test:           ## gate tests: reference checker and legacy URL redirects
	python -m pytest -q tests
	node --test tests/assistant.test.cjs
