---
icon: material/view-dashboard-outline
description: Filter the console by project, bookmark and share views, open workspaces, create a personal API key, and choose the Prefect or OpenFaaS runtime for new operations.
---

# Navigate the console

The Kionga console groups its pages into **Build** (Overview, Projects,
Pipelines, Functions, Applications), **Models and data** (Models, Agents, Agent
designer, Agent definitions, Agent teams, Team runs, Langflow, Feature stores,
Storage, `Realtime`, Catalog) and **Operate** (Logs, Platform, Access, Publishing,
My access, Settings). You see a page when you have its service, and related
panels appear only when you have their services too. This guide covers the everyday navigation tasks.

## Before you begin

- Sign in to the console at `/console`. If your session expires, Kionga
  returns you to sign-in and then back to the page you were on.
- To change the pipeline or function runtime, you need the `admin` or
  `operator` role.

## Work in one project at a time

1. In the page header, open the **Project** selector. It appears on the
   project-scoped pages, such as Pipelines, Functions, Applications, Models and
   Agents.
2. Choose a project. The page and workspace launches now show only that project.
3. To clear the filter, choose **All assigned projects**.

Feature definitions, shared infrastructure and the catalog stay platform-wide.
The selector lists only the projects assigned to you or owned by you.

**Verify:** the page lists only resources from the selected project, and the
address bar contains `project=<project-id>`.

## Bookmark or share a view

Every page has its own address, so you can bookmark it or send it to a teammate
who has the same access:

```text
/console/pipelines?project=PROJECT_ID
```

Pages that open one item, such as a project, run, model, agent or feature,
add `resource=<id>`. Refreshing the page and the browser's back and forward
buttons restore the view, the project filter and the open item. A project page
has **Related resources** links to its pipelines, functions, models and agents, and
buttons that open JupyterLab and the IDE.

If a page fails to load, it shows the error and a **Retry** button; the rest of
the console keeps working.

## Open a workspace

Open JupyterLab or the browser IDE from any of these places:

- The sidebar links **JupyterLab** and **Browser IDE**.
- A project's **Open JupyterLab** and **Open IDE** buttons, which open the
  project's folder. A button is disabled, with the reason as its hover text, when
  the workspace is unavailable.
- **Settings > Developer workspaces**, which lists the workspaces you can open
  with a status for each. On Kubernetes it also has **Start** and **Stop**; see
  [Start and stop your workspace](workbench.md#start-and-stop-your-workspace).
  In platform v0.2.1 and earlier, it shows an unavailable workspace as a
  disabled button with its state.

When you open a project, Kionga creates its folder,
`projects/<namespace>`, if it does not exist. The workspace toolbar keeps the
project when you switch between JupyterLab and the IDE.

Kionga checks your access on every workspace request and every new WebSocket
connection. If an administrator removes your access, new requests are refused
at once, but a connection that is already open stays open until it closes.

For details, see [Work in the Jupyter workbench](workbench.md) and
[Use the browser IDE](coding-workspace.md).

## Create a personal API key

Use a personal API key for the SDK, the `kionga` CLI or automation that runs
outside Kionga. JupyterLab and the browser IDE do not need one.

1. Open **Settings**. Under **Personal API keys**, click **Create API key**.
2. Enter a **Key name**, set **Expires in days** (1 to 365, default 30), select
   the **Service scopes** it needs (at least one) and, optionally, enter
   comma-separated **Project IDs**. An empty list uses your assigned projects. A
   key can never exceed your own access.
3. Click **Create key**, then click **Copy API key** in the **Copy your API
   key** window. Kionga shows the key only once.
4. Export it where your tool runs:

    ```bash
    export KIONGA_URL=https://kionga.example.com
    export KIONGA_TOKEN="your-key"
    kionga-cli project list
    ```

**Verify:** `kionga-cli project list` prints the projects the key's scopes allow.

Personal API keys cannot open workspaces, run scaffold jobs, change personal
settings or use the editorial workspace. Store keys in a secret manager or your
operating system's keychain, never in source control.

## Choose the runtime for new pipeline runs and functions

On Compose and single-server installs, Kionga sends container pipelines to
Prefect and functions to OpenFaaS. On Kubernetes, container pipelines run as
Kubernetes Jobs and functions run in Kionga, so these connections don't apply
there. An administrator can switch to another Prefect or OpenFaaS deployment without
restarting the gateway.

1. Open **Platform**. Under **Components**, click **Add connection**.
2. Choose the **Service** (`prefect` or `openfaas`) and enter a
   **Connection name**.
3. Enter the **Service address**: the Prefect API base address, or the OpenFaaS
   gateway address.
4. Enter the **Credential reference**: `none`, or `env:VARIABLE` naming a
   [permitted variable](../reference/configuration.md#secret-references) set on
   the gateway. Prefect uses it as a bearer token; OpenFaaS uses
   it as the gateway password, with the user from `OPENFAAS_USER` (default
   `admin`). Never paste a secret into this field.
5. Click **Save and test**. A check passes only on a successful HTTP response;
   redirects, missing routes and authentication failures count as failures.
6. In the **Connected infrastructure** table, click **Use for new operations** on
   the connection's row.

Kionga refuses to switch while any pipeline run is queued or running, so a run
never changes its destination. When several connections of a type have been
activated, the most recent one wins. Register your Prefect workers and
deployments, or your OpenFaaS functions, with the new engine before you switch.

Connections of other types (Kubernetes, MLflow, object storage, Kafka REST,
Langfuse, Redis or Feast) are availability monitors: they report health, and
their runtime settings stay in your deployment configuration.

**Verify:** the connection's **Active runtime** column shows `Yes`.

## Verify

- **Project filter:** after you choose a project, the page lists only that project's
  resources, and the address bar contains `project=<project-id>`. Choosing **All
  assigned projects** removes the parameter.
- **Bookmarks:** open a saved address in a new tab. The same page, project filter and
  open item appear.
- **Personal API key:** run `kionga-cli project list`. It prints the projects that the
  key's scopes allow.
- **Runtime:** on **Platform**, the connection you activated shows `Yes` in the
  **Active runtime** column, and the confirmation reads "Runtime activated for new
  operations."
- **Workspaces:** under **Settings > Developer workspaces**, a workspace that is
  `ready` has an **Open** link, such as **Open JupyterLab**. Any other workspace shows its
  status instead of a link.

## Troubleshooting

- *A page shows an error and a **Retry** button.* That page failed to load, and the rest
  of the console keeps working. Click **Retry**. If it keeps failing, check the
  gateway's availability.
- *A project's **Open IDE** button is disabled, with the hover text "IDE is offline. Run make -C deploy
  ide-up from the Kionga workspace folder, then retry."* The IDE is not running on Compose. An operator runs
  `make -C deploy ide-up`. In a production install the message reads "Workspace is
  offline. Ask your administrator to start it."
- *Under **Settings > Developer workspaces**, your workspace shows `stopped`.* On
  Kubernetes, click **Start** and wait for `ready`.
- *The project selector does not list a project.* It lists only the projects assigned
  to you or owned by you. Ask an administrator to assign the project; see
  [Manage users, groups and policies](access-control.md).
- *Activating a runtime fails with `runs_active`: "Wait for running and queued pipelines
  to finish before changing runtimes."* A pipeline run is queued or running. Wait for it
  to finish, then activate again.
- *Activating a runtime fails with `connection_failed`.* The service did not answer the
  check with a successful HTTP response. Redirects, missing routes and authentication
  failures count as failures. Check the **Service address** and credential, then click
  **Test**.
- *Activating a runtime fails with `credential_unavailable`.* The **Credential
  reference** names an environment variable that the gateway does not have, or that is
  not permitted. Set it on the gateway, or use one of the
  [permitted variables](../reference/configuration.md#secret-references).
- *Activating a connection fails with `monitor_only`: "This connection monitors
  availability. Configure its deployment settings to change its runtime."* Only **Prefect** and **OpenFaaS** connections change the runtime.
  Change the other types in your deployment configuration.

## Related pages

- [Create a project from a template](project-templates.md)
- [Define and run pipelines](pipelines.md)
- [Manage users, groups and policies](access-control.md)
- [Work in the Jupyter workbench](workbench.md)
- [Use the browser IDE and coding agents](coding-workspace.md)
