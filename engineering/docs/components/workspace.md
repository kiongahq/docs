---
description: The workspace repository, the Jupyter and IDE images, the project CLI and the loopback sidecar that runs scaffold jobs.
---

# Workspace

## Responsibility

Builds the developer workspaces that the console opens in the browser:

- `ghcr.io/kiongahq/jupyter`: JupyterLab with Jupyter AI, the Kionga SDK, the
  platform's runnable modules (agents, features, real-time, pipelines) and the object
  store buckets mounted with S3FS under `/workspace/object-store/<bucket>`.
- `ghcr.io/kiongahq/ide`: code-server on the same `/workspace` folder, with optional
  coding-agent CLIs.

Both carry the `kionga` CLI, which generates projects from the versioned template
catalog and synchronizes project Git remotes, and a sidecar that lets the gateway
create project folders and run scaffold jobs.

## Interfaces

| Interface | Detail |
| --- | --- |
| Jupyter `:8888` | Reached through the gateway at `/workspaces/`; in Compose the host port binds to `127.0.0.1` for diagnostics only |
| code-server | Compose profile `ide`; publishes no port and is reached through the gateway |
| Sidecar `127.0.0.1:8890` | `POST /prepare-project`, `POST /scaffold-jobs`, and `/api/v1/*` forwarding with the provisioned identity of the workspace; reached only through the authenticated port proxy of the workspace (`/proxy/8890`) |
| `kionga` CLI | `kionga scaffold`, `kionga templates`, `kionga agents`, `kionga project` |

Scaffold jobs are hardened: the gateway builds the argument list from the stored
project, the sidecar validates it again against a fixed flag allowlist and character
class, runs it without a shell in `/workspace/projects` with a scrubbed environment and
a timeout, and requires the shared job token (`KIONGA_WORKSPACE_JOB_TOKEN`).

## Dependencies

The SDK release pinned in the images; the gateway's API; on Kubernetes the operator,
which creates one workspace per grant ([decision 0007](../decisions/0007-per-user-workspaces.md)).

## Configuration

`KIONGA_WORKSPACE` (workspace root), `KIONGA_SUBJECT`, `KIONGA_CUSTOM_AGENT_COMMAND`,
`KIONGA_SIDECAR_PORT`, `KIONGA_WORKSPACE_JOB_TOKEN`, `KIONGA_WORKSPACE_API_TOKEN`.

## Code map

| Path | Contents |
| --- | --- |
| `workspace/jupyter/` | Jupyter image, entrypoint, platform source wiring, quickstart notebook |
| `workspace/ide/` | IDE image and entrypoint |
| `workspace/workspace/kionga.py` | The `kionga` CLI and template generators |
| `workspace/workspace/directories.py` | The sidecar |

## Tests

`workspace/tests` (`test_workspace_cli.py`, `test_workspace_directories.py` with a real
HTTP server, `test_platform_sources.py`). Install `requirements-dev.txt`, then run
`python -m pytest -q` and `ruff check .`. The generated projects' own tests run for real
and need the SDK runtime, scikit-learn and CPU PyTorch.
