---
icon: material/console
description: Reference for the Kionga command-line client and the workspace command.
---

# CLI reference

Kionga has two command-line tools:

| Tool | Runs | Use it to |
| --- | --- | --- |
| `kionga` | Anywhere you can reach Kionga | List resources, submit runs, manage pipeline files, deploy and invoke functions, and connect Git repositories |
| `kionga` | Inside the Jupyter workbench and browser IDE | Generate project starter code, list templates, and sync a project's Git repository |

For anything these tools do not cover, use the [Python SDK](python-sdk.md) or the
[REST API](api.md).

## The `kionga` client

`kionga` is a single static binary. It prints responses as indented JSON, writes
errors to standard error, and exits with a non-zero status when a request fails,
so it works in shell scripts.

### Install

Build it from your workspace checkout. This needs Go 1.26 or later:

```bash
make -C platform build
export PATH="$PWD/platform/bin:$PATH"
```

The build writes `platform/bin/kionga-cli` along with Kionga's other server
binaries. To get a binary named `kionga`, build only the CLI:

```bash
(cd platform/go && go build -o ../bin/kionga-cli ./cmd/cli)
```

The examples on this page call it `kionga`.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_URL` | `http://localhost:8080` | Kionga base URL |
| `KIONGA_TOKEN` | *(unset)* | Personal API key, sent as a bearer token |
| `USER` | `cli` | Sent as `X-Kionga-Actor`; used for attribution only when the request has no authenticated identity |
| `KIONGA_FUNCTION_PAYLOAD` | `{}` | JSON body for `function invoke` and `function invoke-async` |

Every command needs a credential: set `KIONGA_TOKEN` to a personal API key from
**Settings → Personal API keys**. The key acts as a normal `user` limited to its
services and projects; see [Personal API keys](rbac.md#personal-api-keys).

```bash
export KIONGA_URL=https://kionga.example.com
export KIONGA_TOKEN='nxs_...'
kionga-cli project list
```

### Commands

| Command | Effect | API call |
| --- | --- | --- |
| `kionga-cli project list` | List projects | `GET /api/v1/projects` |
| `kionga-cli project connect <project-id> <repository-url> [branch]` | Connect a Git repository; `branch` defaults to `main` | `PUT /api/v1/projects/{id}/repository` |
| `kionga-cli pipeline list` | List pipeline runs | `GET /api/v1/pipelines/runs` |
| `kionga-cli pipeline definitions` | List pipeline flows | `GET /api/v1/pipelines/definitions` |
| `kionga-cli pipeline submit <project-id>` | Run the built-in `training-pipeline` | `POST /api/v1/pipelines/submit` |
| `kionga-cli pipeline submit <project-id> <definition-id>` | Run a flow | `POST /api/v1/pipelines/submit` |
| `kionga-cli pipeline export <definition-id>` | Print the current revision as canonical YAML | `GET /api/v1/pipelines/definitions/{id}/yaml` |
| `kionga-cli pipeline validate <file>` | Validate a flow file. Prints `valid: N stage(s), sha256 <hash>`, or each issue as `line N (node X): message` and exits `1`. | `POST /api/v1/pipelines/validate` |
| `kionga-cli pipeline apply <file> [definition-id] [message]` | Create a flow (without `definition-id`) or save a new revision, with an optional revision message. Prints `<id> revision N (sha256 <hash>)`. | `POST /api/v1/pipelines/definitions/yaml` or `PUT /api/v1/pipelines/definitions/{id}/yaml` |
| `kionga-cli model list` | List models | `GET /api/v1/models` |
| `kionga-cli agent list` | List agents | `GET /api/v1/agents` |
| `kionga-cli tool list` | List tools | `GET /api/v1/tools` |
| `kionga-cli function list` | List functions | `GET /api/v1/functions` |
| `kionga-cli function deploy <project-id> <name> <image>` | Deploy a function with default resources | `POST /api/v1/functions` |
| `kionga-cli function invoke <name>` | Invoke a function with `KIONGA_FUNCTION_PAYLOAD` | `POST /api/v1/functions/{name}/invoke` |
| `kionga-cli function invoke-async <name>` | Queue an invocation with `KIONGA_FUNCTION_PAYLOAD` | `POST /api/v1/functions/{name}/invoke-async` |
| `kionga-cli connection list` | List connections | `GET /api/v1/connections` |
| `kionga-cli audit list` | List audit events | `GET /api/v1/audit` |

Running `kionga` with no arguments or an unknown command prints the usage and
exits with status `2`.

### Examples

```bash
# Find a project ID, then start a training run.
kionga-cli project list
kionga-cli pipeline submit <project-id>

# Keep a flow in Git and apply changes from the file.
kionga-cli pipeline export <definition-id> > train.kionga.yaml
kionga-cli pipeline validate train.kionga.yaml
kionga-cli pipeline apply train.kionga.yaml <definition-id> "Raise training memory"

# Invoke a function with a payload.
KIONGA_FUNCTION_PAYLOAD='{"id":"evt-1"}' kionga-cli function invoke feature-transform
```

See [Pipelines](../guides/pipelines.md#revisions-diff-and-rollback) for the flow
file format.

## The `kionga` workspace command

The `kionga` command is installed in the Jupyter workbench and the browser IDE.
It works with your project's source code. It reaches Kionga through the
preset `KIONGA_URL` of the workspace, so it needs no API key.

The command also runs the SDK's `apps` commands, described in
[Manage applications](#manage-applications), when the SDK (version 0.3.2 or
later) is installed. Elsewhere, install the SDK with `pip install kionga` to get
the same `kionga` command.

| Command | Effect |
| --- | --- |
| `kionga templates [--json]` | Show the project template catalog |
| `kionga agents` | Show which coding agents are available in the workspace |
| `kionga project sync <project-id>` | Clone the project's connected Git repository, or fast-forward an existing clone |
| `kionga scaffold <name> [options]` | Generate a project's starter code |

`kionga scaffold` options:

| Option | Values | Default |
| --- | --- | --- |
| `--template` | `production-ml`, `distributed-training`, `production-agent`, `fullstack-ai`, `blank-python` | `blank-python` |
| `--template-version` | A template version | The current version |
| `--framework` | A framework the template supports | The template's default |
| `--accelerator` | An accelerator the template supports | The template's default |
| `--profile` | `starter`, `team`, `power`, `gpu`, `custom` | The template's recommendation |
| `--agent` | `none`, `codex`, `claude`, `custom` | `none` |
| `--prompt` | Instructions for the coding agent | *(empty)* |

```bash
kionga templates --json
kionga project sync <project-id>
kionga scaffold vision-training --template distributed-training --agent none
kionga scaffold support-agent --template production-agent --agent codex \
  --prompt "Add retrieval, refusal, escalation, and deterministic tests"
```

When you create a project, Kionga returns a `scaffold_command` with the exact
template, version and settings. Prefer running that command. See
[Scaffold a project](../guides/scaffolding.md) and
[Project templates](../guides/project-templates.md).

## Manage applications

`kionga apps` deploys and operates [applications](../guides/applications.md) on a
Kubernetes install. It reads the gateway address from `KIONGA_URL` (or `--url`)
and a personal API key from `KIONGA_TOKEN`. Errors print as `kionga: <reason>`
and exit with status 1. On an install without applications, every command fails
with the `not_configured` reply and its steps.

| Command | Effect | API call |
| --- | --- | --- |
| `kionga apps deploy <name> --project <id> (--image <image> \| --git <url>)` | Deploy an application | `POST /api/v1/applications` |
| `kionga apps update <name>` | Change the settings you pass and keep the rest | `GET` then `PUT /api/v1/applications/{name}` |
| `kionga apps list [--project <id>]` | List applications with phase, replicas and URL | `GET /api/v1/applications` |
| `kionga apps get <name>` | Show one application with its status | `GET /api/v1/applications/{name}` |
| `kionga apps logs <name> [--tail N] [--container NAME]` | Print recent logs of each pod, 1 to 2000 lines (default 200) | `GET /api/v1/applications/{name}/logs` |
| `kionga apps events <name>` | Print Kubernetes events, newest first | `GET /api/v1/applications/{name}/events` |
| `kionga apps redeploy <name>` | Restart the pods, and rebuild a Git source | `POST /api/v1/applications/{name}/redeploy` |
| `kionga apps delete <name> [-y]` | Delete the application, after confirmation unless `-y` | `DELETE /api/v1/applications/{name}` |

`deploy` and `update` take these options:

| Option | Meaning |
| --- | --- |
| `--image`, or `--git` with `--ref`, `--context-dir` and `--dockerfile` | What to run. Use one of the two. |
| `--port` | The container port. Default 8080. |
| `--env KEY=VALUE` | An environment variable. Repeat for more. |
| `--secret NAME` | A Kubernetes Secret to load as environment. Repeat for more. |
| `--cpu`, `--memory` | Per-replica resources, such as `500m` and `512Mi`. |
| `--min-replicas`, `--max-replicas` | The replica range. A minimum of 0 scales to zero. |
| `--scale-on requests\|cpu` with `--target N` | The autoscaling trigger and its target. Pass both. |
| `--health-path` | The health check path. Default `/`. |
| `--visibility public\|sso` | Who can reach it. Default `sso`. |
| `--wait`, `--timeout SECONDS`, `--json` | Wait until ready (default 600 seconds), and print JSON instead of a table. |

`kionga apps logs --follow` arrives in a later SDK release. To follow logs now, use
the [streaming log API](../guides/applications.md#logs).

