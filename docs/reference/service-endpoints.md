---
description: Addresses and local credentials for every Kionga service, from your machine and from inside the stack, and the values to register as console connections.
---

# Service endpoints

Use this page to connect to Kionga's services from your browser, a notebook, a
local tool, or another container, and to register services as connections in
the console.

## Two sets of addresses

- **From your machine**, services are on `localhost` ports. Each port can be
  changed in `deploy/.env` (for example, `GATEWAY_PORT`), and ports bind to
  `127.0.0.1` unless `KIONGA_BIND_ADDRESS` says otherwise; see
  [Network exposure](../operations/local.md#network-exposure).
- **Inside the stack**, services reach each other by service name and container
  port, for example `http://mlflow:5000` or `http://objectstore:9000`. The
  Jupyter workbench and browser IDE also use these addresses.

## Endpoints

The credentials are the local stack's development defaults. Production
deployments replace all of them; see [Choose a deployment](../operations/index.md).

| Service | From your machine | Inside the stack | Credentials (local defaults) |
| --- | --- | --- | --- |
| Landing page | `http://localhost:8080` | `http://gateway:8080` | None |
| Console and API | `http://localhost:8080/console.html` | `http://gateway:8080` | `admin` / `mlaiops-local` (role from `MLAIOPS_LOCAL_ROLE`), or single sign-on |
| Dex (single sign-on) | `http://localhost:5556/dex` | `http://dex:5556/dex` | Test directory password `kionga-sso-dev` |
| Jupyter workbench | `http://localhost:8080/workspace.html?tool=workbench` | `http://jupyter:8888` | Your console session. For diagnostics only: `http://127.0.0.1:8888/workspaces/workbench/` with token `mlaiops-local` (`JUPYTER_TOKEN`). |
| Browser IDE (optional) | `http://localhost:8080/workspace.html?tool=ide` | `http://ide:8080` | Your console session; no published port |
| MLflow | `http://localhost:15000` | `http://mlflow:5000` | None |
| Prefect | `http://localhost:4200` | `http://prefect-server:4200` | None |
| Langfuse | `http://localhost:3000` | `http://langfuse:3000` | `admin@local.dev` / `mlaiops-local-admin`; API keys `pk-lf-local-dev` / `sk-lf-local-dev` |
| Object storage (S3 API) | `http://localhost:9000` | `http://objectstore:9000` | `mlaiops` / `mlaiops-local-secret` |
| Object storage console | `http://localhost:9001` | Not used inside the stack | Same as the S3 API |
| Kafka | `localhost:9092` | `kafka:9092` | None |
| Kafka REST | `http://localhost:8082` | `http://kafka-rest:8082` | None |
| PostgreSQL (with pgvector) | `localhost:5432` | `postgres:5432` | User `mlaiops`, password `mlaiops-local`, database `mlaiops` |
| Redis (online features) | `localhost:6379` | `redis:6379` | None |
| Feature gateway | `http://localhost:8083` | `http://feature-gateway:8083` | None locally |
| Storage proxy | `http://localhost:8084` | `http://storage-proxy:8084` | None locally |
| Serving manager | `http://localhost:8085` | `http://serving-manager:8085` | None locally |
| Trace proxy (LLM egress) | `http://localhost:8081` | `http://trace-proxy:8081` | None |
| Agent runtime | `http://localhost:19000` | `http://agent-runtime:9000` | None |

## Connect from the Jupyter workbench

Open the workbench from the console sidebar (**Jupyter workbench**). It includes:

- The Python SDK (`mlaiops_sdk`) with the `agents` and `huggingface` extras, and
  Kionga's example modules (`pipelines`, `features`, `realtime`, `agents`).
- A terminal (**File → New → Terminal**) with `git`, `curl` and the `kionga`
  command.
- The same `scikit-learn` and `mlflow` versions as the model server image, so a
  model you train in a notebook serves without version mismatches.
- Every connection preset in environment variables: `MLAIOPS_URL`,
  `MLFLOW_TRACKING_URI`, `MLFLOW_S3_ENDPOINT_URL` with `AWS_ACCESS_KEY_ID` and
  `AWS_SECRET_ACCESS_KEY`, `MLAIOPS_FEATURE_GATEWAY_URL`, `KAFKA_REST_URL`,
  `PREFECT_API_URL`, `DATABASE_URL`, `REDIS_URL`, and `LANGFUSE_HOST`,
  `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.
- The storage buckets mounted under `/workspace/object-store`.
- A `quickstart.ipynb` notebook that walks through identity, the registry,
  training with MLflow, model registration, online features and real-time events.

Notebooks are stored in the `jupyter-data` volume and survive restarts. See
[Jupyter workbench](../guides/workbench.md).

## Connect from tools on your machine

| Tool | Settings |
| --- | --- |
| MLflow client | `MLFLOW_TRACKING_URI=http://localhost:15000`; for artifacts, `MLFLOW_S3_ENDPOINT_URL=http://localhost:9000`, `AWS_ACCESS_KEY_ID=mlaiops`, `AWS_SECRET_ACCESS_KEY=mlaiops-local-secret` |
| S3 clients (AWS CLI, `boto3`, `rclone`) | Endpoint `http://localhost:9000`, the same keys, path-style addressing |
| `psql` | `psql postgres://mlaiops:mlaiops-local@localhost:5432/mlaiops` |
| Kafka clients | Brokers `localhost:9092`, or REST at `http://localhost:8082` |
| Kionga API, SDK and CLI | `MLAIOPS_URL=http://localhost:8080` (or your port), authenticated as described in [REST API authentication](api.md#authentication) |

## Register connections in the console

A connection tells Kionga to health-check a service. Open **Platform**, click
**Add infrastructure**, and enter the service, a name, its address and a
credential reference. Kionga tests it immediately and again whenever you click
**Test**.

Kionga runs the check from inside the stack, so use the inside-the-stack
addresses:

| Service | Suggested name | Service address | Credential reference |
| --- | --- | --- | --- |
| MLflow | `local-mlflow` | `http://mlflow:5000/health` | `none` |
| RustFS (local) | `local-objectstore` | `http://objectstore:9000/health` | `none` |
| Kafka REST | `local-kafka` | `http://kafka-rest:8082/topics` | `none` |
| Langfuse | `local-langfuse` | `http://langfuse:3000/api/public/health` | `none` |
| Prefect | `local-prefect` | `http://prefect-server:4200/api` | `none` |
| Redis / Feast | `local-features` | `http://feature-gateway:8083/healthz` | `none` |
| Kubernetes | `kind-cluster` | Your cluster API health URL | `env:VARIABLE` naming a variable that holds a bearer token |

- For Prefect, enter the API base address; Kionga checks `/api/health` under it.
  For OpenFaaS, enter the gateway address; Kionga checks `/system/functions` with
  basic authentication (`OPENFAAS_USER`, default `admin`, and
  `OPENFAAS_PASSWORD`). For every other type, enter a health endpoint.
- The credential reference is `none` or `env:VARIABLE`, naming an environment
  variable set on the gateway. Kionga sends its value as a bearer token. Never
  paste a secret into the form; Kionga stores only the reference.
- Only a `2xx` response counts as healthy. Redirects, missing routes and
  authentication failures are reported as failures, with the reason.
- You can make a Prefect or OpenFaaS connection the engine for new operations
  with **Use for new operations**. Other types only monitor availability.
- Creating, testing and activating connections needs the `infra:Provision`
  permission, which `admin` and `operator` have.

**Onboarding readiness** on the Overview page turns green when a project exists
and healthy `mlflow`, storage (`s3` or `rustfs`), `kafka` and `kubernetes`
connections are registered. The local stack has no Kubernetes cluster, so that
item stays pending unless you connect one, for example a Kind cluster.

## Connect more services

- **A real language model for agents**: in `deploy/.env`, set
  `MLAIOPS_LLM_BACKEND` (`openai`, `anthropic` or `openai-compatible`), the
  provider key, and optionally `MLAIOPS_LLM_MODEL`, then recreate the agent
  runtime. The `openai` and `openai-compatible` backends go through the trace
  proxy, so every call is recorded; `anthropic` calls Anthropic directly. See
  [LLM providers](configuration.md#llm-providers).
- **Live models and agents in the real-time examples**: set
  `FRAUD_MODEL_ENDPOINT` to a deployed model's endpoint URL and
  `CALLCENTER_AGENT_ID` to a deployed agent ID, then run
  `docker compose -f deploy/compose.yaml up -d realtime-processor`.
- **Serverless functions**: connect an OpenFaaS or faasd gateway with
  `OPENFAAS_URL`, `OPENFAAS_USER` and `OPENFAAS_PASSWORD`; see
  [Connect OpenFaaS functions](../operations/local.md#connect-openfaas-functions).

## Use external services

Every service address is configuration, so you can replace a bundled service
without changing images:

| Replace | With | Set |
| --- | --- | --- |
| RustFS | Amazon S3, Google Cloud Storage or Azure through an S3-compatible API | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` on `storage-proxy`; `MLFLOW_S3_ENDPOINT_URL` and `AWS_*` on `mlflow`, `pipeline-runner` and `serving-manager` |
| PostgreSQL | A managed PostgreSQL | `DATABASE_URL` on `gateway` and `agent-runtime`, and the MLflow and Langfuse database URLs |
| Redis | A managed Redis | `REDIS_URL` on `feature-gateway` |
| Kafka | A managed Kafka with a REST proxy | `KAFKA_REST_URL` wherever it is set |
| LLM provider | Any OpenAI-compatible provider | `LLM_UPSTREAM_URL` on `trace-proxy` |

To let teams use their own buckets, see
[External object storage](../operations/external-storage.md).

## Troubleshooting

- **A connection shows unhealthy**: its address must resolve from inside the
  stack. Test it from a temporary container on the stack's network, for example
  `docker run --rm --network mlaiops_default curlimages/curl -fsS http://mlflow:5000/health`.
- **It works in the console but fails from your laptop, or the reverse**: you used
  an inside-the-stack address outside the stack, or a `localhost` address inside
  it. Swap it using the table above.
- **It works on this machine but not from another**: ports bind to `127.0.0.1` by
  default; see [Network exposure](../operations/local.md#network-exposure).
- **Several services are down**: run `make -C deploy local-up` again (it is safe
  to repeat), check `make -C deploy local-status`, and run
  `./deploy/scripts/demo-smoke.sh` to test every capability.

See [Troubleshooting](../operations/troubleshooting.md) for more.
