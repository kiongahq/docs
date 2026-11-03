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
