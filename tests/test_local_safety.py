"""The local stack's safety guidance stays complete and consistent.

The local stack publishes services with development credentials, keeps its state
in named volumes and offers a destructive reset. These tests keep the pages that
describe them honest:

- installation.md lists the default credential of every published port, and the
  pages that start the stack link to that warning;
- the backup procedure never archives a running PostgreSQL data directory and
  names every durable volume, with the same list on every page;
- every documented `down -v` sits in a danger admonition after a backup step.

When KIONGA_SRC points at the sibling checkouts (as in CI), the port and volume
lists are also compared with deploy/compose.yaml."""

import os
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
INSTALL = DOCS / "getting-started" / "installation.md"
WARNING_ANCHOR = "installation.md#local-credentials-and-network-access"


def deploy_compose():
    root = os.environ.get("KIONGA_SRC")
    path = Path(root) / "deploy" / "compose.yaml" if root else REPO.parent / "deploy" / "compose.yaml"
    if not path.is_file():
        pytest.skip("deploy/compose.yaml not found; set KIONGA_SRC to the sibling checkouts")
    return yaml.safe_load(path.read_text())


def section(path, heading):
    """Text of the Markdown section that starts with `heading`, up to the next heading of that level."""
    text = path.read_text()
    level = heading.split(" ", 1)[0]
    start = text.index(heading + "\n") if heading + "\n" in text else text.index(heading + " ")
    rest = text[start + len(heading):]
    end = re.search(rf"^{level} ", rest, re.M)
    return rest[: end.start()] if end else rest


def credentials_table():
    return section(INSTALL, "## Local credentials and network access")


def test_installation_warns_about_development_credentials():
    text = credentials_table()
    assert '!!! warning "Development credentials"' in text
    for credential in ("mlaiops-local", "mlaiops-local-secret", "mlaiops-local-admin", "kionga-local-service-token"):
        assert credential in text, f"{credential} is a default but not listed"
    assert "nc -vz" in text  # the reachability check from another machine


def test_installation_lists_every_published_port():
    ports = set(re.findall(r"\$\{([A-Z_]+_PORT):-", yaml.safe_dump(deploy_compose()["services"])))
    ports -= {"LOG_EXPORTER_PORT"}  # opt-in log-export profile, documented in Run locally
    listed = set(re.findall(r"`([A-Z_]+_PORT)`", credentials_table()))
    assert ports <= listed, f"published ports missing from installation.md: {sorted(ports - listed)}"


@pytest.mark.parametrize("page", ["getting-started/quickstart.md", "index.md"])
def test_start_pages_link_to_the_warning(page):
    text = (DOCS / page).read_text()
    assert WARNING_ANCHOR in text or WARNING_ANCHOR.split("#")[1] in text, f"{page} does not link to the warning"


def test_local_role_does_not_claim_anonymous_access():
    text = (DOCS / "reference" / "configuration.md").read_text()
    row = next(line for line in text.splitlines() if line.startswith("| `MLAIOPS_LOCAL_ROLE`"))
    assert "every API request still needs a credential" in row
    origin = next(line for line in text.splitlines() if line.startswith("| `MLAIOPS_ALLOWED_ORIGIN`"))
    assert "never allows credentials" in origin


LOCAL = DOCS / "operations" / "local.md"
EXCLUDED_VOLUMES = {"postgres-data", "sso-providers"}  # dumped with pg_dumpall / regenerated


def backup_section():
    return section(LOCAL, "## Back up local data")


def volume_loops(text):
    return [set(loop.split()) for loop in re.findall(r"for volume in ([a-z0-9 -]+); do", text)]


def test_backup_never_archives_a_running_postgres_directory():
    text = backup_section()
    assert "pg_dumpall" in text
    assert not re.search(r"postgres-data:/data", text), "the PostgreSQL data directory is archived"


def test_backup_archives_files_only_after_the_stack_stops():
    text = backup_section()
    assert text.index("make -C deploy local-down") < text.index("tar czf")


def test_backup_and_restore_cover_the_same_volumes():
    table = set(re.findall(r"^\| `([a-z0-9-]+)`", backup_section(), re.M))
    table |= {"workspace-codex", "workspace-claude"} if "`workspace-codex`, `workspace-claude`" in backup_section() else set()
    loops = volume_loops(backup_section()) + volume_loops(section(LOCAL, "## Restore a backup"))
    assert len(loops) == 2, "expected one archive loop and one restore loop"
    assert loops[0] == loops[1] == table - EXCLUDED_VOLUMES


def test_every_compose_volume_is_backed_up_or_excluded():
    volumes = set(deploy_compose()["volumes"])
    table = set(re.findall(r"`([a-z0-9-]+)`", backup_section()))
    assert volumes <= table, f"volumes without backup guidance: {sorted(volumes - table)}"


def test_installation_names_the_same_durable_volumes():
    text = section(INSTALL, "## Stop and restart")
    listed = set(re.findall(r"`([a-z0-9]+-[a-z0-9-]+)`", text)) - {"local-down", "local-up", "local-status", "local-logs", "local-rebuild", "workspace-pull"}
    (loop,) = volume_loops(backup_section())[:1]
    assert listed == loop | {"postgres-data"}


def test_restore_is_documented_and_checked():
    text = section(LOCAL, "## Restore a backup")
    assert "psql" in text and "postgres.sql" in text
    assert "/api/v1/projects" in text  # compare the project count


ALL_PAGES = sorted([*DOCS.rglob("*.md"), *(REPO / "engineering" / "docs").rglob("*.md")])


def danger_blocks(text):
    """(start, end) offsets of every `!!! danger` admonition body."""
    blocks = []
    for match in re.finditer(r"^( *)!!! danger.*\n", text, re.M):
        indent = len(match.group(1)) + 4
        end = match.end()
        for line in text[match.end():].splitlines(keepends=True):
            if line.strip() and len(line) - len(line.lstrip()) < indent:
                break
            end += len(line)
        blocks.append((match.start(), end))
    return blocks


def reset_commands(text):
    """Offsets of `down -v` inside fenced code (commands, not prose)."""
    offsets, fence = [], False
    position = 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        elif fence and re.search(r"\bdown\b.*\s-v\b", line):
            offsets.append(position)
        position += len(line)
    return offsets


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: str(p.relative_to(REPO)))
def test_every_reset_command_is_guarded_by_a_backup(page):
    text = page.read_text()
    blocks = danger_blocks(text)
    for offset in reset_commands(text):
        block = next(((s, e) for s, e in blocks if s <= offset < e), None)
        assert block, f"{page.name}: a `down -v` command is outside a danger admonition"
        before = text[block[0]:offset]
        assert "#back-up-local-data" in before, f"{page.name}: `down -v` is not preceded by a backup step"


def test_reset_commands_exist_only_where_expected():
    pages = {page.relative_to(DOCS).as_posix() for page in ALL_PAGES if page.is_relative_to(DOCS) and reset_commands(page.read_text())}
    assert pages == {"operations/local.md"}


def test_troubleshooting_tries_non_destructive_steps_first():
    text = section(DOCS / "operations" / "troubleshooting.md", "### The stack is broken after an update")
    danger = text.index("!!! danger")
    steps = [cmd for cmd in ("local-status", "local-logs", "local-build-up", "local-rebuild", "--force-recreate gateway", "smoke")
             if 0 <= text.find(cmd) < danger]
    assert len(steps) >= 3, steps
    assert "local.md#back-up-local-data" in text[danger:]
    assert "down -v" not in text


CONFIGURATION = DOCS / "reference" / "configuration.md"


@pytest.mark.parametrize("name", [
    "SERVE_IMAGE_ALLOWED_PREFIXES", "SERVE_IMAGE_REQUIRE_DIGEST", "SERVE_FETCH_IMAGE", "SERVE_READY_TIMEOUT_SECONDS",
    "TRACE_PROXY_KEYS", "TRACE_PROXY_KEYS_FILE", "TRACE_PROXY_ALLOW_UNAUTHENTICATED", "LLM_UPSTREAM_API_KEY",
    "LLM_UPSTREAM_API_KEY_FILE", "LLM_UPSTREAM_AUTH_HEADER", "LLM_UPSTREAM_AUTH_SCHEME",
])
def test_configuration_reference_lists_security_settings(name):
    assert f"`{name}`" in CONFIGURATION.read_text()


def test_guides_keep_the_provider_key_in_the_trace_proxy():
    # Behind the trace proxy, OPENAI_API_KEY holds a Kionga project key.
    agents = (DOCS / "guides" / "agents.md").read_text()
    assert "OPENAI_API_KEY=sk-" not in agents and "OPENAI_API_KEY=sk-" not in CONFIGURATION.read_text()
    assert "LLM_UPSTREAM_API_KEY=sk-" in agents
    assert "{#project-keys}" in agents


def test_models_guide_does_not_claim_servers_hold_credentials():
    assert "run with the platform's model-store credentials" not in (DOCS / "guides" / "models-serving.md").read_text()
