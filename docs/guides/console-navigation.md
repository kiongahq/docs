---
icon: material/view-dashboard-outline
description: Filter the console by project, bookmark and share views, open workspaces, create a personal API key, and choose the Prefect or OpenFaaS runtime for new operations.
---

# Navigate the console

The Kionga console groups its pages into **Build** (Overview, Projects,
Pipelines, Functions), **Models & data** (Models, Agents, Features, Storage,
Real-time, Catalog), **Operate** (Logs, Platform, Users & access) and
**Account** (My access, Settings, Engineering blog). You see a page when you
have its service, and related panels appear only when you have their services
too. This guide covers the everyday navigation tasks.

## Before you begin

- Sign in to the console at `/console.html`. If your session expires, Kionga
  returns you to sign-in and then back to the page you were on.
- To change the pipeline or function runtime, you need the `admin` or
  `operator` role.

## Work in one project at a time

1. In the page header, open the **Project** selector.
2. Choose a project. Projects, pipelines, functions, models, agents and
   workspace launches now show only that project.
3. To clear the filter, choose **All assigned projects**.

Feature definitions, shared infrastructure and the catalog stay platform-wide.
The selector lists only the projects assigned to you or owned by you.

**Verify:** the page lists only resources from the selected project, and the
address bar contains `project=<project-id>`.

## Bookmark or share a view

Every page has its own address, so you can bookmark it or send it to a teammate
who has the same access:

```text
/console.html?view=pipelines&project=PROJECT_ID
```

Pages that open one item, such as a project, run, model, agent or feature,
add `resource=<id>`. Refreshing the page and the browser's back and forward
buttons restore the view, the project filter and the open item. A project page
links straight to its runs, functions, models, agents, Jupyter and IDE.

If a page fails to load, it shows the error and a **Retry** button; the rest of
the console keeps working.

## Open a workspace

Open JupyterLab or the browser IDE from any of these places:

- The sidebar links **Jupyter workbench ↗** and **IDE workspace ↗**.
- A project's **Open in Jupyter ↗** and **Open in IDE ↗** buttons, which open the
  project's folder.
- **Settings > Developer workspaces**.

The sidebar's **Developer workspaces** status shows whether each workspace is
ready. When you open a project, Kionga creates its folder,
`projects/<namespace>`, if it does not exist. The workspace toolbar keeps the
project when you switch between JupyterLab and the IDE.

Kionga checks your access on every workspace request and every new WebSocket
connection. If an administrator removes your access, new requests are refused
at once, but a connection that is already open stays open until it closes.

For details, see [Work in the Jupyter workbench](workbench.md) and
[Use the browser IDE](coding-workspace.md).

## Create a personal API key

Use a personal API key for the SDK, the `mlaiops` CLI or automation that runs
outside Kionga. JupyterLab and the browser IDE do not need one.

1. Open **Settings > Personal API keys** and click **＋ Create key**.
2. Enter a **Key name**, choose when it **Expires after** (7 days, 30 days,
   90 days or 1 year), select the **Service scopes** it needs and, optionally,
   limit it to **Project IDs**. A key can never exceed your own access.
3. Click **Create key**, copy the key, and click **I have saved it**. Kionga
   shows the key only once.
4. Export it where your tool runs:

    ```bash
    export MLAIOPS_URL=https://kionga.example.com
    export MLAIOPS_TOKEN="your-key"
    mlaiops project list
    ```

**Verify:** `mlaiops project list` prints the projects the key's scopes allow.

Personal API keys cannot open workspaces, run scaffold jobs, change personal
settings or use the editorial workspace. Store keys in a secret manager or your
operating system's keychain, never in source control.

## Choose the runtime for new pipeline runs and functions

Kionga sends container pipelines to Prefect and functions to OpenFaaS. An
administrator can switch to another Prefect or OpenFaaS deployment without
restarting the gateway.

1. Open **Platform** and click **＋ Add connection**.
2. Choose the **Service** (**Prefect** or **OpenFaaS**) and enter a
   **Connection name**.
3. Enter the **Service address**: the Prefect API base address, or the OpenFaaS
   gateway address.
4. Enter the **Credential reference**: `none`, or `env:VARIABLE` naming a
   variable set on the gateway. Prefect uses it as a bearer token; OpenFaaS uses
   it as the gateway password, with the user from `OPENFAAS_USER` (default
   `admin`). Never paste a secret into this field.
5. Click **Save and test**. A check passes only on a successful HTTP response;
   redirects, missing routes and authentication failures count as failures.
6. On the connection card, click **Use for new operations**.

Kionga refuses to switch while any pipeline run is queued or running, so a run
never changes its destination. When several connections of a type have been
activated, the most recent one wins. Register your Prefect workers and
deployments, or your OpenFaaS functions, with the new engine before you switch.

Connections of other types (Kubernetes, MLflow, object storage, Kafka REST,
Langfuse, Redis or Feast) are availability monitors: they report health, and
their runtime settings stay in your deployment configuration.

**Verify:** the card's label changes to `prefect · Active runtime` or
`openfaas · Active runtime`.

## Next steps

- [Create a project from a template](project-templates.md).
- [Define and run pipelines](pipelines.md).
- [Manage users, groups and policies](access-control.md).
