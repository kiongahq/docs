---
icon: material/folder-plus-outline
description: Generate a project's starter code in your Jupyter or IDE workspace, from the console, a workspace terminal, or the REST API.
---

# Scaffold a project into your workspace

Generate the starter code for a project you created from a
[template](project-templates.md). The scaffold writes a package, tests, CI, a
Dockerfile and a platform manifest that match the project's stored template,
framework, accelerator and resource profile.

You can run the scaffold from the console with one click, or paste the
project's command into a workspace terminal. Both write to the same folder:

| Where | Path |
| --- | --- |
| Project folder on disk | `/workspace/projects/<namespace>` |
| JupyterLab, when you open the project | `projects/<namespace>` in the file browser |
| Browser IDE, when you open the project | `/workspace/projects/<namespace>` as the open folder |

`/workspace` is the persistent workspace volume, so JupyterLab, the browser IDE
and the scaffold always see the same files.

## Before you begin

- You can see the project: you own it, it is assigned to you, or your role is
  `admin`, `operator` or `engineer` without a project restriction.
- You can open a workspace: the `workbench` or `ide` service for a normal user,
  or the `engineer`, `operator` or `admin` role. Viewers, personal API keys and
  service identities cannot run scaffold jobs, because they cannot drive a
  workspace.
- To run the scaffold from the console or the API, a normal user also needs the
  `projects` service.
- The project folder is empty or does not exist yet. The scaffold never
  overwrites files.

## Run the scaffold from the console

1. Open **Projects** and select **Open project** in the project's row.
2. In the **Generate starter code** panel, click **Run in workspace**.
3. Review the **Run scaffold in workspace** dialog. It shows the workspace that
   runs the command, the working and output folders, and the exact command with
   every argument.
4. Click **Run command**.

The panel updates while the job runs. When it finishes, the **Last scaffold
run** section lists the produced files, the output of the command and the `git
status` of the new folder, with secret-looking values redacted.

## Run the scaffold in a workspace terminal

Use this when you want to add a coding agent with `--agent` and `--prompt`, which
the console does not run for you.

1. Open the project and click **Copy command** in the **Generate starter code**
   panel. The command looks like this:

    ```bash
    kionga scaffold churn-model --template production-ml --template-version 1.0.0 \
      --framework xgboost --accelerator cpu --profile team
    ```

2. Open a terminal in JupyterLab (**File > New > Terminal**) or in the browser
   IDE.
3. Run the command with `KIONGA_WORKSPACE=/workspace/projects`, so the files land
   in the folder that the project page's **Open JupyterLab** and **Open IDE**
   buttons open:

    ```bash
    KIONGA_WORKSPACE=/workspace/projects kionga scaffold churn-model \
      --template production-ml --template-version 1.0.0 \
      --framework xgboost --accelerator cpu --profile team
    ```

    `kionga scaffold` writes to `$KIONGA_WORKSPACE/<name>` whatever your
    current directory is, and `KIONGA_WORKSPACE` defaults to `/workspace`.

## Run the scaffold through the API

Scaffold jobs need an interactive session, because they run in your workspace.
Call the API with the session cookie from a browser sign-in (see
[Authentication](../reference/api.md#authentication)), not with a personal API
key.

1. Check what would run and whether a workspace can run it:

    ```bash
    curl -s -b kionga.cookies \
      "$KIONGA_URL/api/v1/projects/<project-id>/scaffold-plan" | python -m json.tool
    ```

    The plan returns the `command`, `working_dir`, `output_dir`, the chosen
    `workspace`, and `available` with a `reason` when no workspace can run it.

2. Start a job. The body is optional; set `options.workspace` to `workbench` or
   `ide` to choose the workspace:

    ```bash
    curl -s -b kionga.cookies -X POST \
      -H 'Content-Type: application/json' \
      -d '{"options": {"workspace": "workbench"}}' \
      "$KIONGA_URL/api/v1/projects/<project-id>/scaffold-jobs"
    ```

3. Poll the job until its `status` is `succeeded` or `failed`:

    ```bash
    curl -s -b kionga.cookies \
      "$KIONGA_URL/api/v1/projects/<project-id>/scaffold-jobs/<job-id>"
    ```

A job moves through `queued`, `running`, and then `succeeded` or `failed`. It
reports `started_at`, `ended_at`, `exit_code`, `output_tail`, `files`,
`git_status`, `error` and `requested_by`. `GET
/api/v1/projects/<project-id>/scaffold-jobs` lists a project's jobs, newest
first.

## How Kionga runs the scaffold safely

- **The browser never sends a command.** A request can only choose the
  workspace. Kionga builds the command from the project's stored template
  settings and rejects any value that is not a plain lowercase name or version.
- **The command runs in your own workspace**, without a shell, with a minimal
  environment and a time limit. It cannot pass `--agent` or `--prompt`, so the
  console never starts a coding agent for you.
- **Your workspace is the limit.** The job can only do what you could already do
  from a terminal in that workspace.
- **One job per project at a time.** A second request while a job runs returns
  `409`. A job that does not report back within 5 minutes, for example because
  the gateway restarted, is marked failed as interrupted.
- **Project access applies.** A project you cannot see returns `404`.

For the full design, see the gateway section of the
[engineering handbook](https://kiongahq.github.io/docs/engineering-access/).

## Verify

1. **Console:** the **Last scaffold run** section shows the status `succeeded`,
   the `output_dir` `/workspace/projects/<namespace>`, and the **Produced files**
   list. Click **Open JupyterLab** or **Open IDE** to open the folder.
2. **Terminal:** the command prints `Created /workspace/projects/churn-model`,
   and `ls /workspace/projects/churn-model` lists `pyproject.toml`, `Dockerfile`
   and `tests`.
3. **API:** the job's `status` is `succeeded`, its `exit_code` is `0`, and
   `files` lists the generated files.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `target already exists and is not empty: <path>` | The project folder already has files, and the scaffold never overwrites them. | Open the folder in JupyterLab or the IDE, or sync it from Git with `kionga project sync`. |
| `this project has no template; add your own files or connect a repository` | You created the project without a template, so there is no command to run. | Add your own files, or [connect a repository](distributed-workspaces.md#connect-a-project-to-git). |
| `No workspace is assigned to you. Request JupyterLab or the IDE from My access.` | You have neither the `workbench` nor the `ide` service. | Ask an administrator for the service, or request it from **My access**. |
| `This workspace image has no scaffold runner. Rebuild it (make -C deploy local-rebuild) so it includes the Kionga workspace sidecar.` | The workspace image predates the scaffold runner. | An operator rebuilds the workspace images, for example with `make -C deploy local-rebuild`. |
| `The workspace rejected the scaffold credential. KIONGA_WORKSPACE_JOB_TOKEN must match on the gateway and the workspace.` | The two tokens differ. | An operator sets the same `KIONGA_WORKSPACE_JOB_TOKEN` on the gateway and the workspaces, then restarts them. |
| `Scaffold jobs need KIONGA_WORKSPACE_JOB_TOKEN set on the gateway and the workspace.` | The token is empty. | An operator sets `KIONGA_WORKSPACE_JOB_TOKEN`. `deploy/scripts/local-up.sh` generates one for local installs; set your own in any shared deployment. |
| `The workspace did not answer. Make sure it is running, then run the job again.` | The workspace is stopped or unreachable. | Check the state of the workspace under **Settings > Developer workspaces**, where an unavailable workspace shows as a disabled button with its state. Ask an operator to start it, then run the job again. |
| `409 conflict`, `a scaffold job is already running for this project` | A job is still queued or running for the project. | Wait for it to finish, then retry. |
| `The job was interrupted before it reported a result (the gateway restarted or the workspace stopped responding). Run it again.` | The job reported nothing for 5 minutes. | Run the job again. |
| `404 not_found`, `project not found` | The project does not exist, or you cannot see it. | Check the project ID and your project access. |

On Kubernetes, each user's workspace uses its own generated credential instead
of `KIONGA_WORKSPACE_JOB_TOKEN`.

## Related pages

- [Work in the Jupyter workbench](workbench.md) or the
  [browser IDE](coding-workspace.md).
- [Connect the project to Git](distributed-workspaces.md#connect-a-project-to-git).
- [Define a pipeline](pipelines.md) for the generated code.
- [Create a project from a template](project-templates.md).
