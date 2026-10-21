# Connecting all the services

The local platform is one Compose stack. This guide covers the three ways things
connect:

1. **Service to service** inside the stack (already wired; reference below).
2. **You to services** from the browser, the Jupyter workbench, or any local tool.
3. **Console connections** (Platform page): registering services with the
   control plane so their availability is checked and onboarding turns green.

## The map

```
                    you (browser / notebook / CLI)
                                  │
      ┌───────────┬───────────┬───┴────────┬───────────┬───────────┐
   console      MLflow      Prefect     Langfuse    RustFS console Dex (SSO)
   :8080*       :15000      :4200       :3000       :9001          :5556
      │  (Jupyter and the IDE open through the gateway)
   gateway ──► Prefect API ──► pipeline-runner (trains, logs to MLflow)
      │  ╲───► serving-manager ──► mlflow-serve containers (live endpoints)
      │  ╲───► agent-runtime ──► LLM via trace-proxy ──► Kafka traces
      │  ╲───► storage-proxy ──► RustFS       │
      │  ╲───► feature-gateway ──► Redis      └─► Langfuse (traces)
      │  ╲───► Langfuse API (prompts)
   Postgres (control plane, MLflow, Langfuse, agent checkpoints, pgvector)
   Kafka ◄── realtime-processor ──► feature-gateway, models, agents
```

Two DNS worlds:

- **Inside the stack** services reach each other by Compose service name:
  `http://gateway:8080`, `http://mlflow:5000`, `http://objectstore:9000`, …
- **From your machine** the same services are on published localhost ports
  (table below). Every port is overridable in `deploy/.env` (for example
  `GATEWAY_PORT`). Ports bind to `127.0.0.1` unless `KIONGA_BIND_ADDRESS` says
  otherwise; see [Network exposure](operations/local.md#network-exposure).

## Service reference

| Service | From your machine | Inside the stack | Credentials (local defaults) |
| --- | --- | --- | --- |
| Landing page (gateway) | http://localhost:8080 | `http://gateway:8080` | none |
| Console + API (gateway) | http://localhost:8080/console.html | `http://gateway:8080` | `admin` / `mlaiops-local` (role from `MLAIOPS_LOCAL_ROLE`), or single sign-on |
| Dex (single sign-on) | http://localhost:5556/dex | `http://dex:5556/dex` | test directory password `kionga-sso-dev` |
| Jupyter workbench | http://localhost:8080/workspace.html?tool=workbench | `http://jupyter:8888` | Kionga session; diagnostics at `http://127.0.0.1:8888/workspaces/workbench/` with token `mlaiops-local` (`JUPYTER_TOKEN`) |
| MLflow tracking/registry | http://localhost:15000 | `http://mlflow:5000` | none |
| Prefect UI/API | http://localhost:4200 | `http://prefect-server:4200` | none |
| Langfuse | http://localhost:3000 | `http://langfuse:3000` | `admin@local.dev` / `mlaiops-local-admin`; API keys `pk-lf-local-dev` / `sk-lf-local-dev` |
| RustFS S3 API | http://localhost:9000 | `http://objectstore:9000` | `mlaiops` / `mlaiops-local-secret` |
| RustFS web console | http://localhost:9001 | — | same as S3 |
| Kafka broker | localhost:9092 | `kafka:9092` | none |
| Kafka REST proxy | http://localhost:8082 | `http://kafka-rest:8082` | none |
| Postgres (+pgvector) | localhost:5432 | `postgres:5432` | `mlaiops` / `mlaiops-local` / db `mlaiops` |
| Redis (online features) | localhost:6379 | `redis:6379` | none |
| Feature gateway | http://localhost:8083 | `http://feature-gateway:8083` | internal token in public mode |
| Storage proxy | http://localhost:8084 | `http://storage-proxy:8084` | internal token in public mode |
| Serving manager | http://localhost:8085 | `http://serving-manager:8085` | internal token in public mode |
| Trace proxy (LLM egress) | http://localhost:8081 | `http://trace-proxy:8081` | none |
| Agent runtime | http://localhost:19000 | `http://agent-runtime:9000` | none |
| Browser IDE (optional) | http://localhost:8080/workspace.html?tool=ide | `http://ide:8080` | Kionga session; no published port |

All local defaults are development-only. Public deployments replace them; see
[Public hosting](hosting.md).

## Registering connections in the console

**Platform → Add infrastructure** registers a service with the control plane.
The gateway tests it at once and on every **Test** click. **The gateway
performs the check from inside the stack, so use in-stack hostnames**, not
localhost.

| Service | Connection name (suggested) | Service address | Credential reference |
| --- | --- | --- | --- |
| MLflow | `local-mlflow` | `http://mlflow:5000/health` | `none` |
| RustFS (local) | `local-objectstore` | `http://objectstore:9000/health` | `none` |
| Kafka REST | `local-kafka` | `http://kafka-rest:8082/topics` | `none` |
| Langfuse | `local-langfuse` | `http://langfuse:3000/api/public/health` | `none` |
| Prefect | `local-prefect` | `http://prefect-server:4200/api` | `none` |
| Redis / Feast | `local-features` | `http://feature-gateway:8083/healthz` | `none` |
| Kubernetes | `kind-cluster` | your cluster API health URL | `env:VARIABLE` holding a bearer token |

Notes:

- For Prefect, enter the API base address; the gateway appends `/api/health`.
  For OpenFaaS, enter the gateway address; the gateway checks
  `/system/functions` with basic auth (`OPENFAAS_USER`, default `admin`). Every
  other type takes a health endpoint.
- The **credential reference** is `none` or `env:VARIABLE`, naming an
  environment variable set on the gateway. The gateway sends its value as a
  bearer token. Never paste a secret into the form; the control plane stores
  only the reference.
- Only a `2xx` response counts as healthy. Redirects, missing routes, and
  authentication failures are reported as failures with the reason.
- Prefect and OpenFaaS connections can be activated with **Use for new
  operations**; other types monitor availability only.
- **Onboarding readiness** (Overview ring and Platform panel) turns green from
  these connections: workspace means any project exists, plus healthy `mlflow`,
  `s3` or `rustfs` (storage), `kafka` (events), and `kubernetes` connections.
  Kubernetes is the scale path. On the Compose stack the execution engine is
  Prefect plus the serving manager, so that one item stays pending unless you
  connect a real cluster (for example Kind).
- Creating, testing, and activating connections needs the `infra:Provision`
  permission (administrators and operators by default).

## Connecting from the Jupyter workbench

`make -C deploy local-up` includes a JupyterLab workbench. Open it from the
console (**Jupyter**) or at
<http://localhost:8080/workspace.html?tool=workbench>. It has:

- **Terminal included**: File → New → Terminal opens bash with `git`, `curl`,
  and every platform module (`python -m realtime.produce --demo fraud --count 3`).
- The platform SDK (`mlaiops_sdk`) and modules (`pipelines`, `features`,
  `realtime`, `agents`) preinstalled.
- ML pins identical to the serving image (`scikit-learn==1.7.0`,
  `mlflow==3.1.1`), so models trained in a notebook serve without skew.
- Every connection preconfigured via environment: `MLAIOPS_URL`,
  `MLFLOW_TRACKING_URI`, `MLFLOW_S3_ENDPOINT_URL` + `AWS_*`,
  `MLAIOPS_FEATURE_GATEWAY_URL`, `KAFKA_REST_URL`, `PREFECT_API_URL`,
  `DATABASE_URL`, `REDIS_URL`, `LANGFUSE_*`.
- `quickstart.ipynb` (seeded into the workspace volume) walks the platform:
  identity, registry, training logged to MLflow, registration with the control
  plane, online features, and real-time events.

Your notebooks persist in the `jupyter-data` volume across restarts.

## Connecting from external tools on your machine

- **MLflow**: `MLFLOW_TRACKING_URI=http://localhost:15000`, and for artifacts
  `MLFLOW_S3_ENDPOINT_URL=http://localhost:9000` with
  `AWS_ACCESS_KEY_ID=mlaiops` / `AWS_SECRET_ACCESS_KEY=mlaiops-local-secret`.
- **S3 clients** (aws cli, boto3, rclone): endpoint `http://localhost:9000`,
  same keys, path-style addressing.
- **psql**: `psql postgres://mlaiops:mlaiops-local@localhost:5432/mlaiops`.
- **Kafka**: brokers `localhost:9092`, or REST at `http://localhost:8082`.
- **Platform API**: set `MLAIOPS_URL=http://localhost:8080` (or your overridden
  gateway port) and authenticate as described in the
  [REST API reference](reference/api.md#authentication). `/api-docs.html` and
  `/api/openapi.json` describe the surface.

## Wiring the moving parts together

- **Real LLMs for agents**: in `deploy/.env` set `MLAIOPS_LLM_BACKEND=openai`
  (or `anthropic`), the API key, and optionally `MLAIOPS_LLM_MODEL`, then
  recreate `agent-runtime`. The `openai` and `openai-compatible` backends egress
  through the trace proxy, so every call lands in Kafka; the `anthropic` backend
  calls Anthropic directly. See [LLM providers](getting-started/configuration.md#llm-providers).
- **Real-time demos → live components**: set `FRAUD_MODEL_ENDPOINT` to a live
  model endpoint (Models tab → deploy → endpoint URL) and
  `CALLCENTER_AGENT_ID` to a deployed agent id, then
  `docker compose -f deploy/compose.yaml up -d realtime-processor`.
- **Serverless (OpenFaaS/faasd)**: install faasd on the host (see
  [Public hosting](hosting.md#openfaas-functions-on-a-vm-faasd)), then set
  `OPENFAAS_URL`, `OPENFAAS_USER`, and `OPENFAAS_PASSWORD`. The Functions view
  then lists, deploys, and invokes project-owned functions.

## Swapping in external / production services

Build once, point anywhere: set the URL and credentials, no image changes.

| Replace | With | How |
| --- | --- | --- |
| RustFS | AWS S3 / GCS / Azure (S3 API) | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` (storage-proxy), `MLFLOW_S3_ENDPOINT_URL` + `AWS_*` (mlflow, runner) |
| Postgres | RDS / Cloud SQL | `DATABASE_URL` on gateway, agent-runtime, langfuse, mlflow backend URI |
| Redis | managed Redis | `REDIS_URL` on feature-gateway |
| Kafka | managed Kafka + REST proxy | `KAFKA_REST_URL` everywhere it appears |
| Local LLM egress | any OpenAI-compatible provider | `LLM_UPSTREAM_URL` on trace-proxy |

## Troubleshooting

- **Connection shows unhealthy**: the URL must resolve *from the gateway
  network*. The gateway is distroless; use a disposable curl container on
  `mlaiops_default` to reproduce the check.
- **Works in console, fails from your laptop**: you used an in-stack hostname
  outside the stack (or the reverse). Swap it using the table above.
- **Works on this machine, fails from another**: ports bind to `127.0.0.1` by
  default. See [Network exposure](operations/local.md#network-exposure).
- **Everything down?** `make -C deploy local-up` is idempotent; `docker compose -f
  deploy/compose.yaml ps` shows per-service state; and
  `GATEWAY=http://localhost:8080 ./deploy/scripts/demo-smoke.sh` verifies the configured
  capabilities end to end.
