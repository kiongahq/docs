"""Gate tests for scripts/check_references.py against a small fake workspace."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_references as cr  # noqa: E402

DOCS_REPO = Path(__file__).resolve().parent.parent


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """A workspace with just enough of each sibling repository to check against."""
    root = tmp_path / "src"
    write(root / "deploy" / "Makefile", """
        .PHONY: local-up test
        COMPOSE := docker compose
        local-up:            ## start
        \tbash scripts/local-up.sh
        test smoke:
        \tpytest
    """)
    write(root / "deploy" / "scripts" / "local-up.sh", "echo $KIONGA_START_RETRIES\n")
    write(root / "deploy" / "compose.yaml", """
        services:
          gateway:
            environment:
              OIDC_ISSUER: x
              MLAIOPS_LOCAL_ROLE: admin
              KIONGA_LOG_EXPORT_URL: ""
            ports: ["${KIONGA_BIND_ADDRESS:-127.0.0.1}:${GATEWAY_PORT:-8080}:8080"]
    """)
    write(root / "platform" / "Makefile", "build:\n\tgo build ./...\nverify: build\n")
    write(root / "platform" / "go" / "internal" / "httpapi" / "server.go", """
        package httpapi
        func routes(mux *http.ServeMux) {
            mux.HandleFunc("GET /api/v1/projects", s.projects)
            mux.HandleFunc("POST /api/v1/projects", s.createProject)
            mux.HandleFunc("PUT /api/v1/projects/{id}/repository", s.repo)
            mux.HandleFunc("GET /api/v1/editorial/posts/{id}/revisions", s.revisions)
            mux.HandleFunc("GET /api/v1/editorial/posts/{id}/revisions/{number}", s.revision)
            mux.HandleFunc("/workspaces/{kind}/{path...}", s.proxy)
        }
    """)
    # Test files never count as registered routes.
    write(root / "platform" / "go" / "internal" / "httpapi" / "server_test.go",
          'mux.HandleFunc("GET /api/v1/only-in-tests", nil)\n')
    write(root / "platform" / "go" / "internal" / "auth" / "authenticator.go", """
        switch r.URL.Path {
        case "/auth/callback":
        }
    """)
    write(root / "platform" / "go" / "cmd" / "cli" / "main.go", """
        switch strings.Join(os.Args[1:], " ") {
        case "project list":
        default:
            if len(os.Args) == 4 && os.Args[1] == "pipeline" && os.Args[2] == "submit" {
            }
        }
    """)
    write(root / "sdk-python" / "mlaiops_sdk" / "__init__.py", """
        from .client import MLAIOpsClient
        from .models import Project
        __all__ = ["MLAIOpsClient", "Project", "build_chat_model"]
        _LAZY = {"build_chat_model": ("mlaiops_sdk.llm", "build_chat_model")}
    """)
    write(root / "sdk-python" / "mlaiops_sdk" / "models.py", """
        from pydantic import BaseModel
        class Project(BaseModel):
            id: str
            name: str
    """)
    write(root / "sdk-python" / "mlaiops_sdk" / "client.py", """
        class MLAIOpsClient:
            def __init__(self, base_url: str = "", *, actor: str = "") -> None: ...
            def __enter__(self): ...
            def list_projects(self) -> list[Project]: ...
            def create_project(self, name: str, *, description: str = "") -> Project: ...
    """)
    write(root / "sdk-python" / "mlaiops_sdk" / "llm.py", "def build_chat_model(**kwargs): ...\n")
    return root


def check(workspace: Path, markdown: str, **only) -> list[cr.Finding]:
    docs = workspace / "docs" / "docs"
    write(docs / "page.md", markdown)
    write(workspace / "docs" / "Makefile", "docs-build:\n\tmkdocs build --strict\n")
    return cr.run(docs, workspace, checks={k: cr.CHECKS[k] for k in only} or None)


def values(findings: list[cr.Finding]) -> list[str]:
    return [f.value for f in findings]


def test_make_targets_resolve_per_repository(workspace: Path) -> None:
    findings = check(workspace, """
        Run `make -C deploy local-up`, `make -C ../deploy smoke` and `make -C docs docs-build`.

        ```bash
        GATEWAY_PORT=18080 make -C deploy local-up
        make -C deploy local-upp
        make -C platform build verify lint
        make -C nowhere build
        ```

        Prose that says make sure is not a command.
    """, make=True)
    assert values(findings) == [
        "make -C deploy local-upp",
        "make -C platform lint",
        "make -C nowhere build",
    ]
    assert "no target 'local-upp' in deploy/Makefile" in findings[0].message


def test_paths_into_sibling_repositories(workspace: Path) -> None:
    findings = check(workspace, """
        See `deploy/compose.yaml`, `deploy/scripts/*.sh`, `platform/go/internal/{name}`,
        `deploy/compose.yml`, and `go/internal/httpapi/server.go` and `go/cmd/nope`.

        ```bash
        ./deploy/scripts/local-up.sh
        bash deploy/scripts/missing.sh
        git clone https://github.com/kiongahq/deploy.git
        ```
    """, path=True)
    assert values(findings) == ["deploy/compose.yml", "go/cmd/nope", "deploy/scripts/missing.sh"]


def test_environment_variables(workspace: Path) -> None:
    findings = check(workspace, """
        Set `KIONGA_BIND_ADDRESS=0.0.0.0` or KIONGA_START_RETRIES; tune `KIONGA_LOG_EXPORT_*`.
        `OIDC_ISSUER` is required; `OIDC_ISSUER_URL` and `MLAIOPS_LOCAL_ROLES` are not real,
        and neither is `KIONGA_NOPE_*`.
    """, env=True)
    assert values(findings) == ["OIDC_ISSUER_URL", "MLAIOPS_LOCAL_ROLES", "KIONGA_NOPE_*"]


def test_routes_against_registered_patterns(workspace: Path) -> None:
    findings = check(workspace, """
        | `GET /api/v1/projects` | list |
        | `PUT /api/v1/projects/<id>/repository` | connect Git |
        | `DELETE /api/v1/projects` | not registered |
        | `GET /api/v1/editorial/posts/{id}/revisions[/{n}]` | history |
        | `GET /api/v1/pipelines` | missing |
        | `GET /api/v1/only-in-tests` | test-only |

        Prefix references such as `/api/v1/editorial/...` and links such as
        http://localhost:8080/api/v1/projects?limit=1 also resolve, while
        https://huggingface.co/api/v1/models belongs to another service.
        The browser returns to `/auth/callback`, not `/auth/return`.
        Prefect's own `/api/health` is not a gateway route.
    """, route=True)
    assert values(findings) == [
        "DELETE /api/v1/projects",
        "GET /api/v1/pipelines",
        "GET /api/v1/only-in-tests",
        "/auth/return",
    ]
    assert findings[0].message.startswith("method not registered")


def test_cli_commands(workspace: Path) -> None:
    findings = check(workspace, """
        ```bash
        mlaiops project list
        MLAIOPS_URL=https://example.com mlaiops pipeline submit <project-id>
        ./bin/mlaiops-cli project delete prj-1
        mlaiops widget list
        psql -U mlaiops mlaiops
        ```
    """, cli=True)
    assert values(findings) == ["mlaiops project delete", "mlaiops widget"]


def test_sdk_symbols_methods_and_keywords(workspace: Path) -> None:
    findings = check(workspace, """
        ```python
        from mlaiops_sdk import MLAIOpsClient, Project, build_chat_model, Missing
        from mlaiops_sdk.nothing import x

        with MLAIOpsClient(base_url="http://localhost:8080", actor="me") as client:
            project = client.create_project("demo", description="d", owner="me")
            print(project.id, project.title)
            client.list_project()
        build_chat_model(model="x")
        MLAIOpsClient(token="t")
        ```

        Inline `client.list_projects()` is fine; `client.py` is a file name.
        `mlaiops_sdk.Project` exists; `mlaiops_sdk.Projects` does not.
    """, sdk=True)
    assert values(findings) == [
        "from mlaiops_sdk import Missing",
        "mlaiops_sdk.nothing",
        "client.create_project",
        "project.title",
        "client.list_project",
        "MLAIOpsClient",
        "mlaiops_sdk.Projects",
    ]


def test_allowlist_suppresses_with_wildcards(workspace: Path, tmp_path: Path) -> None:
    allow = tmp_path / "allow.txt"
    allow.write_text("# comment\npath deploy/.env*   # created by the reader\n")
    docs = workspace / "docs" / "docs"
    write(docs / "page.md", "Copy to `deploy/.env` and `deploy/.envrc`.\n")
    findings = cr.run(docs, workspace, cr.load_allowlist(allow), {"path": cr.check_paths})
    assert findings == []


def test_main_requires_sibling_checkouts(tmp_path: Path, capsys) -> None:
    assert cr.main(["--root", str(tmp_path)]) == 2
    assert "workspace.sh" in capsys.readouterr().err


def test_main_reports_and_fails(workspace: Path, capsys) -> None:
    docs = workspace / "docs" / "docs"
    write(docs / "page.md", "Run `make -C deploy nope`.\n")
    status = cr.main(["--root", str(workspace), "--docs", str(docs),
                      "--allowlist", str(workspace / "none.txt")])
    out = capsys.readouterr()
    assert status == 1
    assert "docs/page.md:1: [make] make -C deploy nope" in out.out


def test_repository_allowlist_entries_are_well_formed() -> None:
    entries = cr.load_allowlist(DOCS_REPO / "scripts" / "reference-allowlist.txt")
    assert entries, "allowlist should parse"
    assert {category for category, _ in entries} <= set(cr.CHECKS)
