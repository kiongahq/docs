.PHONY: docs-install docs-serve docs-build docs-check docs-lint docs-diagrams docs-test docs-ui

# Workspace folder holding the sibling Kionga checkouts (deploy, platform, ...).
KIONGA_SRC ?= ..
# Material for MkDocs prints a notice about MkDocs 2.0 on every build.
export NO_MKDOCS_2_WARNING := 1

docs-install:
	python -m pip install -r requirements-docs.txt
	npm ci --prefix ui
	npm run build --prefix ui

docs-serve: docs-ui          ## product documentation, http://127.0.0.1:8000
	mkdocs serve

docs-build: docs-ui          ## product documentation only, strict
	mkdocs build --strict --site-dir site
	python scripts/check_public_site.py site

docs-check:          ## references against the code; product pages also keep code internals out
	python scripts/check_references.py --root $(KIONGA_SRC) --product

docs-lint:           ## prose: Google developer documentation style via Vale (errors fail)
	vale sync >/dev/null
	vale --minAlertLevel=error docs

docs-diagrams:       ## every mermaid diagram parses (needs Node)
	npm install --prefix scripts --no-audit --no-fund --silent
	node scripts/check_mermaid.mjs docs

docs-test:           ## gate tests: reference checker and legacy URL redirects
	python -m pytest -q tests
	npm test --prefix ui

docs-ui:
	npm ci --prefix ui --ignore-scripts
	npm run build --prefix ui

.PHONY: docs-releases
docs-releases:       ## refresh the public component changelog (requires network access)
	python scripts/sync_releases.py
