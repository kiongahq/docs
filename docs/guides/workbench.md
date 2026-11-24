---
icon: material/notebook-outline
description: Open the JupyterLab workbench, call Kionga from notebooks without an API key, use object storage as files, install your own tools, and train and register a model.
---

# Work in the Jupyter workbench

Open the JupyterLab workbench, call Kionga from notebooks, read object storage,
install your own tools, and take a model from a notebook to a live endpoint. The
workbench is JupyterLab running next to the platform services, with the Kionga
SDK, pinned ML libraries and a terminal. Use it to explore data, train models and
call the platform from notebooks.

## Before you begin

- You can open the workbench: the `workbench` service for a normal user, or the
  `engineer`, `operator` or `admin` role. Viewers and personal API keys cannot
  open workspaces.
- Calls you make from the workbench run as you, with your current grants.
  Registering a model needs the `models` service (or a role that can write
  models), and the [feature](features.md) and
  [real-time](realtime.md) examples need those services.

## Open the workbench

1. Sign in to the Kionga console.
2. Open the workbench in one of these ways:
    - In the sidebar, click **JupyterLab**.
    - Open a project and click **Open JupyterLab** to open its folder,
      `projects/<namespace>`.
    - Open **Settings > Developer workspaces** and choose **JupyterLab**.

The workbench opens through the gateway at `/workspace?tool=workbench`
with your console session. You do not need a Jupyter token. The workspace
toolbar has an **Open in** list that switches between JupyterLab and the browser
IDE, and a **Back to console** link.

## Call Kionga from a notebook

Inside the workbench, the SDK reaches the platform through a local helper set in
`KIONGA_URL` and acts as you. You do not need a personal API key, and your
browser session is never copied into the notebook kernel.

1. In a notebook cell, run:

    ```python
    from kionga import KiongaClient

    with KiongaClient() as client:
        for project in client.list_projects():
            print(project.id, project.name)
    ```

Personal API keys are for tools that run outside Kionga, such as an IDE on your
laptop or external automation.

## Run the guided quickstart notebook

1. Open `quickstart.ipynb` in the file browser and run the cells. Kionga copies it
into your workspace the first time the workbench starts and never overwrites
your edits. It walks through the platform in code:

- Check your identity and platform health.
- List projects, registered models and feature views.
- Train a scikit-learn model and log it to MLflow.
- Register the model with Kionga, so it appears under **Models**.
- Read online features through the feature gateway.
- Produce real-time fraud events and read the stream statistics.

## Read and write object storage as files

Each platform bucket is mounted under `/workspace/object-store/<bucket>`, so you
can use ordinary file APIs:

1. In a notebook cell, run:

    ```python
    from pathlib import Path

    features = Path("/workspace/object-store/kionga-features")
    print(list(features.iterdir()))
    ```

Files you write under these paths go straight to object storage. The mounted
buckets are `kionga-models`, `kionga-artifacts`, `kionga-features`,
`kionga-traces`, `kionga-agents` and `kionga-pipeline-logs`.

## Install your own packages and extensions

Your installs live on the persistent workspace volume, so they survive restarts
and image upgrades.

1. Open a terminal with **File > New > Terminal**.
2. Install a Python package or a prebuilt JupyterLab extension:

    ```bash
    python -m pip install --user PACKAGE_NAME
    ```

    User packages go to `/workspace/.kionga/jupyter/python-user`. Settings,
    Jupyter data and layouts are kept under `/workspace/.kionga/jupyter`.

3. Restart the workbench to load a new server extension, or reload the browser
   tab for a frontend-only extension.

To update the Codex or Claude Code command-line tools for your user, install
them with `npm install --global`, for example
`npm install --global @anthropic-ai/claude-code`. They go to
`/workspace/.kionga/jupyter/npm`.

Keep these limits in mind:

- Do not replace the pinned MLflow and scikit-learn versions in the workbench
  environment. Use a project virtual environment when dependencies conflict.
- The JupyterLab **Extension Manager** is read-only. JupyterLab's PyPI search
  does not work because PyPI removed the API it uses, so install extensions from
  the terminal.
- JupyterLab cannot install VS Code extensions (`.vsix`). Use the
  [browser IDE](coding-workspace.md) for those.

## Code with AI assistants

The workbench includes three kinds of coding help. Use the one that fits:

- **Jupyter AI chat:** open the chat panel in the left sidebar, choose a
  provider, and describe the code or analysis you need. It can reference
  notebook cells.
- **Command-line agents:** run `codex` or `claude` in a terminal for
  repository-wide changes. Provider credentials come from `OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY`, which an operator sets for the workspace.
- **Scaffold with an agent:** generate a starter and let a coding agent extend
  it, confined to the new project folder:

    ```bash
    kionga scaffold support-agent \
      --template production-agent \
      --agent codex \
      --prompt "Build a tested support agent with retrieval and escalation"
    ```

Run `kionga agents` to see which agents are installed and whether their
credentials are set. For the full scaffold workflow, see
[Scaffold a project](scaffolding.md).

## Train a model and serve it

The workbench pins `scikit-learn==1.7.0` and `mlflow==3.17.2`, the same versions
as the default serving image, so a model you train here loads in a live
endpoint.

1. Train a model and log it to MLflow:

    ```python
    import mlflow
    from sklearn.datasets import make_classification
    from sklearn.linear_model import LogisticRegression

    X, y = make_classification(n_samples=1200, n_features=12, n_informative=6,
                               n_clusters_per_class=1, class_sep=1.5, random_state=7)
    model = LogisticRegression(max_iter=500).fit(X, y)

    mlflow.set_experiment("workbench")
    with mlflow.start_run():
        logged = mlflow.sklearn.log_model(model, name="model",
                                          registered_model_name="notebook-classifier")
    ```

2. Register the version with Kionga:

    ```python
    from kionga import KiongaClient

    version = mlflow.MlflowClient().get_latest_versions("notebook-classifier")[0].version
    with KiongaClient() as client:
        project_id = client.list_projects()[0].id
        registered = client.register_model(
            project_id, "notebook-classifier", version, logged.model_uri,
            metrics={"accuracy": 0.9},
        )
        print(registered.id, registered.stage)
    ```

3. Open **Models** in the console, deploy `notebook-classifier`, and send a
   request from its **Test** dialog. See [Deploy and serve models](models-serving.md).

## Environment reference

Every workbench kernel and terminal has these variables set:

| Variable | Points to |
| --- | --- |
| `KIONGA_URL` | The local helper that calls Kionga as you |
| `MLFLOW_TRACKING_URI` | MLflow |
| `MLFLOW_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | The object store used by MLflow |
| `KIONGA_FEATURE_GATEWAY_URL` | The feature gateway |
| `KAFKA_REST_URL` | The Kafka REST proxy |
| `PREFECT_API_URL` | Prefect |
| `DATABASE_URL` | PostgreSQL with pgvector |
| `REDIS_URL` | Redis |
| `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Langfuse |

The workbench runs Python 3.11 with the Kionga SDK (`kionga`) and the
platform modules `pipelines`, `features`, `realtime` and `agents`. The terminal
also has `git`, `curl`, `codex`, `claude` and `kionga`.

## Deployment notes

- **Compose:** everyone shares one workspace volume (`jupyter-data`). The direct
  Jupyter port, `127.0.0.1:8888`, is for local diagnostics only, and the public
  overlay does not publish it. Open the workbench through the console.
- **Kubernetes:** each provisioned user gets an isolated workspace with its own
  persistent volume. See
  [Provision a teammate's workspace](distributed-workspaces.md#provision-a-teammates-workspace).

## Verify

1. **Open:** JupyterLab opens, and the file browser shows `quickstart.ipynb`.
   Kionga copies it into `/workspace` the first time the workbench starts.
2. **SDK:** the cell prints the projects you see in the console.
3. **Object storage:** `ls /workspace/object-store` in a terminal lists the
   buckets. The directory is empty when the deployment has no object-store
   mount; see Troubleshooting.
4. **Packages:** `python -m pip list --user` shows the package you installed.
5. **Model:** `notebook-classifier` appears under **Models** with the version
   you registered, and its `stage` is `candidate`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The **Developer workspaces** panel shows `JupyterLab: <state>` as a disabled button | The workbench is not available, and the state says why. | Ask an operator to start the workbench, then reload. |
| No **JupyterLab** link in the sidebar | You do not have the `workbench` service. | Ask an administrator for the service, or request it from **My access**. |
| The workbench container exits with `Object-store filesystem mount requires S3_ENDPOINT and /dev/fuse` | The deployment gives the workbench no object-store endpoint or no `/dev/fuse` device. | An operator sets `S3_ENDPOINT` and the FUSE device, or sets `S3_MOUNT_OPTIONAL=true` to start without the mount. With the option set, `/workspace/object-store` stays empty and storage remains available through the platform API. |
| The workbench container exits with `Object-store filesystem mount requires S3_MOUNT_PREFIX, ...; refusing to mount whole buckets.` | The workbench has no prefix of its own in each bucket. | An operator sets `S3_MOUNT_PREFIX`, for example `projects/<namespace>`. |
| `KIONGA_JUPYTER_TRUST_XHEADERS must be true or false.` | The variable has another value. | Set it to `true` or `false`. |
| A server extension does not load | You did not restart the workbench. | Restart the workbench. Reload the browser tab for a frontend-only extension. |
| A model you trained fails to load in a live endpoint | The libraries in your environment differ from the serving image. | Keep the pinned MLflow and scikit-learn versions, or register a `serving_image`. See [Avoid training-serving skew](models-serving.md#avoid-training-serving-skew). |
| `kionga agents` shows `missing` or `login or API key required` | The agent's command-line tool is not installed, or its credential is not set. | Ask an operator to set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for the workspace. |

## Related pages

- [Use the browser IDE](coding-workspace.md) for VS Code extensions.
- [Define a pipeline](pipelines.md) to run your training code on a schedule.
- [Deploy and serve models](models-serving.md).
- [Scaffold a project](scaffolding.md).
