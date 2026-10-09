# Jupyter workbench

The workbench is a JupyterLab service that runs **inside the platform network**, so
every service is one hostname away. It also provides the **terminal** for
shell-based dev work. Sign in to Kionga and open Jupyter or the browser IDE from
the console. Inside either workspace, the SDK uses a loopback helper configured
through `MLAIOPS_URL` and acts as the workspace owner without a personal API key.
The browser session is never copied into notebook kernels; the gateway checks
current user grants on each API request. Personal API keys are for tools running
outside Kionga, such as your own laptop IDE or external automation.

```python
from mlaiops_sdk import MLAIOpsClient

with MLAIOpsClient() as client:
    print(client.list_projects())
```

- **URL:** [Open Jupyter through Kionga](http://localhost:8080/workspace.html?tool=workbench)
- **Login:** your Kionga session; the gateway keeps the notebook token server-side
- **Direct local diagnostics:** `http://127.0.0.1:8888/workspaces/workbench/`, with `JUPYTER_TOKEN`; the port is bound to loopback
- **Build:** `workspace/jupyter/Dockerfile` (Python 3.11)
- **Persistence:** your work lives in the `jupyter-data` volume across restarts
- **Notebook file IDs:** Jupyter keeps its file-ID database at `/workspace/.jupyter/file_id_manager.db` on that same volume, so open notebooks retain their IDs across image rebuilds
- **Object store mount:** `/workspace/object-store/<bucket>`
- **AI chat:** Jupyter AI chat panel in the left sidebar
- **JupyterLab extensions:** the Extension Manager lists installed extensions in [read-only mode](https://jupyterlab.readthedocs.io/en/stable/user/extensions.html#configuring-the-extension-manager). PyPI's [removed XML-RPC `browse` method](https://warehouse.pypa.io/api-reference/xml-rpc/#browse-classifiers) breaks JupyterLab's PyPI search; install trusted, prebuilt Python extensions from the Jupyter terminal instead. Reload an already-open JupyterLab tab after upgrading the image to clear the old PyPI Manager view.
- **Coding agents:** `codex`, `claude`, and the `kionga` scaffolder in terminals

## Install your own coding tools

Jupyter AI is preinstalled. To add another compatible, prebuilt JupyterLab
extension or Python coding package, use **File → New → Terminal**:

```bash
python -m pip install --user PACKAGE_NAME
```

`PYTHONUSERBASE` is set to `/workspace/.kionga/jupyter/python-user`, so the
package remains available after the workbench image is rebuilt. Restart the
workbench to load newly installed server extensions; reload the browser tab for
frontend-only extensions. User settings, Jupyter data and workspace layouts are
also stored under `/workspace/.kionga/jupyter`. Avoid replacing Kionga's pinned
MLflow and scikit-learn versions in this environment; use a project virtual
environment when dependencies conflict.

The Codex and Claude Code command-line agents are already in the Jupyter image.
Their user-level npm update location is `/workspace/.kionga/jupyter/npm`; for
example, `npm install --global @anthropic-ai/claude-code` persists across image
rebuilds. Installing a VS Code `.vsix` in JupyterLab is not supported: use the
[browser IDE](coding-workspace.md) for VS Code extensions.

Each object-store bucket is mounted as a directory, so notebook code can use normal
filesystem APIs:

```python
from pathlib import Path

features = Path("/workspace/object-store/mlaiops-features")
print(list(features.iterdir()))
```

Writes through these paths persist directly to object storage. Only the
workbench receives the FUSE device and `SYS_ADMIN` capability required by
S3FS; these permissions must not be copied to other platform services.

## What's preloaded

- **The platform SDK** (`mlaiops_sdk`) and the runnable modules (`pipelines`,
  `features`, `realtime`, `agents`).
- **ML libraries pinned to the serving image** (`scikit-learn==1.7.0`,
  `mlflow==3.1.1`), so a model you train in a notebook deploys to a live endpoint
  without training-serving skew.
- **Every connection, preconfigured via environment:**

  | Environment variable | Points to |
  | --- | --- |
  | `MLAIOPS_URL` | Loopback workspace API helper (forwards as your platform identity) |
  | `MLFLOW_TRACKING_URI` | MLflow |
  | `MLFLOW_S3_ENDPOINT_URL` + `AWS_*` | RustFS (S3) |
  | `MLAIOPS_FEATURE_GATEWAY_URL` | Feature gateway |
  | `KAFKA_REST_URL` | Kafka REST proxy |
  | `PREFECT_API_URL` | Prefect |
  | `DATABASE_URL` | PostgreSQL + pgvector |
  | `REDIS_URL` | Redis |
  | `LANGFUSE_HOST` + keys | Langfuse |

## The terminal

**File → New → Terminal** gives you a bash shell with the same environment, plus
`git` and `curl`. Everything the platform modules expose is available:

```bash
python -m realtime.produce --demo fraud --count 5
python -m realtime.produce --demo callcenter --count 2
curl -s "$MLAIOPS_URL/api/v1/models" | python -m json.tool
kionga agents
kionga scaffold fraud-api --template fullstack-ai --prompt "Create a fraud scoring API"
```

Use `--agent codex` or `--agent claude` to let the selected coding agent
complete the generated starter:

```bash
kionga scaffold support-agent \
  --template production-agent \
  --agent codex \
  --prompt "Build a tested support agent with retrieval and escalation"
```

The command confines the agent to the newly generated project directory.
Provider credentials come from `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

The five canonical project templates are discoverable through the control plane.
For heavyweight ML, create a `distributed-training` project with a GPU profile and
run its returned scaffold command. For agents, `production-agent` produces a
runnable graph/runtime and offline test/evaluation path rather than an empty stub.
See [Project templates](project-templates.md).

## Natural-language coding

Open the **Jupyter AI** chat panel from the left sidebar, select the OpenAI or
Anthropic provider, and describe the analysis or code you need. The chat can
reference notebook cells and generate code without leaving JupyterLab. For
repository-wide edits, open a terminal and run `codex`, `claude`, or
`kionga scaffold`.

## The seeded quickstart

A `quickstart.ipynb` is seeded into the workspace on first start (it never
overwrites your edits). It walks the whole platform in code:

1. **Identity & health** — `GET /me`, `GET /health`.
2. **Browse** — projects, registered models, feature views.
3. **Train & log** — a scikit-learn model logged to MLflow.
4. **Register** — the model version registered with the control plane (shows up in
   the console's Models tab).
5. **Online features** — a real lookup from Redis via the feature gateway.
6. **Real-time** — produce fraud events and read live stream stats.

## From notebook to live endpoint

Because the workbench pins match the serving image, the round trip works end to end:

```python
import os, httpx, mlflow
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

X, y = make_classification(n_samples=1200, n_features=12, n_informative=6,
                           n_clusters_per_class=1, class_sep=1.5, random_state=7)
model = LogisticRegression(max_iter=500).fit(X, y)

mlflow.set_experiment("workbench")
with mlflow.start_run():
    logged = mlflow.sklearn.log_model(model, name="model",
                                      registered_model_name="notebook-classifier")

gateway = os.environ["MLAIOPS_URL"]
version = mlflow.MlflowClient().get_latest_versions("notebook-classifier")[0].version
httpx.post(f"{gateway}/api/v1/models", json={
    "project_id": httpx.get(f"{gateway}/api/v1/projects").json()[0]["id"],
    "name": "notebook-classifier", "version": version,
    "artifact_uri": logged.model_uri, "metrics": {"accuracy": 0.9},
})
```

Then open the console's **Models** tab, deploy `notebook-classifier`, and hit it
from the predict console.

## Public deployments

In the public overlay the workbench port is **closed** — reach it over an SSH
tunnel to the VM rather than exposing 8888 to the internet. For multi-user
Kubernetes deployments, each authorized subject receives an isolated
`KiongaWorkspace` instead of this shared Compose volume.
