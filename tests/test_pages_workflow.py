"""The Pages workflow deploys only from main.

The github-pages environment accepts deployments from the main branch only. A
run started by a published release has the release tag as its ref, so its
deploy job was refused (v2.0.0 and v2.0.1). The release run must instead start
the workflow on main."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def workflow():
    data = yaml.safe_load((REPO / ".github/workflows/pages.yml").read_text())
    # PyYAML reads the bare key `on` as the boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def test_release_runs_never_deploy_from_the_tag():
    condition = workflow()["jobs"]["deploy"]["if"]
    assert "github.event_name != 'release'" in condition
    assert "github.event_name != 'pull_request'" in condition


def test_a_release_starts_the_workflow_on_main():
    data = workflow()
    assert "release" in data["on"]
    job = data["jobs"]["redeploy-from-main"]
    assert job["if"] == "github.event_name == 'release'"
    assert job["permissions"] == {"actions": "write"}
    command = job["steps"][0]["run"]
    assert "gh workflow run pages.yml" in command
    assert "--ref main" in command


def test_the_dispatched_run_can_deploy():
    data = workflow()
    assert "workflow_dispatch" in data["on"]
    assert "workflow_dispatch" not in data["jobs"]["deploy"]["if"]
