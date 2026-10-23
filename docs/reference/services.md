---
description: Every service in the Kionga local stack and Kubernetes package, with its role, image, published port and health check.
---

# Services and ports

The local stack is defined in `deploy/compose.yaml`. It runs 21 services by
default, adds optional services through Compose profiles, and starts one model
server container for each deployed model. To connect to these services, see
[Service endpoints](service-endpoints.md).

## Local stack

Host ports bind to `127.0.0.1` unless `KIONGA_BIND_ADDRESS` is set; see
[Network exposure](../operations/local.md#network-exposure). Each port variable
changes the host port only; services keep talking to each other on the
container port.

| Service | Role | Image or build | Host port (variable) |
| --- | --- | --- | --- |
| `gateway` | Kionga console and API | Built from `platform` | 8080 (`GATEWAY_PORT`) |
| `dex` | Single sign-on broker (OIDC issuer) | `ghcr.io/dexidp/dex:v2.46.0` | 5556 (`DEX_PORT`) |
| `glauth` | Test LDAP directory for Dex | `glauth/glauth:v2.5.4` | None |
| `postgres` | PostgreSQL with pgvector: Kionga records, MLflow, Langfuse, agent checkpoints and memory | `pgvector/pgvector:pg16` | 5432 (`POSTGRES_PORT`) |
| `redis` | Online feature store | `redis:7.4.5-alpine` | 6379 (`REDIS_PORT`) |
| `kafka` | Events, LLM traces and real-time streams | `apache/kafka:3.9.1` | 9092 (`KAFKA_PORT`) |
| `kafka-rest` | HTTP access to Kafka (Karapace, Confluent-compatible) | `ghcr.io/aiven-open/karapace:6.1.4` | 8082 (`KAFKA_REST_PORT`) |
| `objectstore` | S3-compatible object storage (RustFS) and its web console | `rustfs/rustfs:1.0.1` | 9000 (`OBJECTSTORE_PORT`), 9001 (`OBJECTSTORE_CONSOLE_PORT`) |
| `objectstore-init` | Creates the storage buckets, then exits | `mlaiops-mlflow`, built from `deploy/mlflow` | None |
| `mlflow` | Experiment tracking and model registry | `mlaiops-mlflow`, built from `deploy/mlflow` | 15000 (`MLFLOW_PORT`); container port 5000 |
| `feature-gateway` | Online feature lookups | Built from `platform` | 8083 (`FEATURE_GATEWAY_PORT`) |
| `storage-proxy` | Object storage browsing and signed URLs | Built from `platform` | 8084 (`STORAGE_PROXY_PORT`) |
| `prefect-server` | Pipeline engine | `prefecthq/prefect:3-latest` | 4200 (`PREFECT_PORT`) |
| `pipeline-runner` | Runs Kionga's pipeline flows, including container steps | Built from `pipeline-runner` | None |
| `serving-manager` | Starts and stops model server containers | Built from `serving` | 8085 (`SERVING_MANAGER_PORT`) |
| `agent-runtime` | Shared agent runtime | Built from `agent-runtime` | 19000 (`AGENT_RUNTIME_PORT`); container port 9000 |
| `trace-proxy` | LLM egress that records OpenAI-protocol calls | Built from `trace-proxy` | 8081 (`TRACE_PROXY_PORT`) |
| `langfuse` | LLM and agent observability, prompt library | `langfuse/langfuse:2` | 3000 (`LANGFUSE_PORT`) |
| `realtime-processor` | Kafka stream scoring for the real-time examples | Built from `agent-runtime` | None |
| `feature-materializer` | Applies feature definitions and fills the online store, then exits | The `agent-runtime` image | None |
| `jupyter` | Jupyter workbench, opened through the console | Built from `workspace` | 8888 (`JUPYTER_PORT`), always `127.0.0.1` |

### Optional services

| Service | Profile | Role | Host port |
| --- | --- | --- | --- |
| `ide` | `ide` | Browser IDE sharing the workbench files, opened through the console. Start it with `make -C deploy ide-up`. | None |
| `log-exporter` | `log-export` | Ships Kionga logs to Elasticsearch or OpenSearch | 8086 (`LOG_EXPORTER_PORT`), always `127.0.0.1` |
| `elasticsearch` | `log-export-es` | Local Elasticsearch to try log export | 9200, always `127.0.0.1` |
| `opensearch` | `log-export-os` | Local OpenSearch to try log export | 9201, always `127.0.0.1` |

See [Log export](../operations/log-export.md).

### Services outside the stack

- **Model servers** are containers that the serving manager starts for each
  deployed model version. They do not appear in `deploy/compose.yaml`.
- **OpenFaaS or faasd** runs functions. It is not part of the stack; connect one
  with `OPENFAAS_URL`.

## Health checks

| Service | Health check |
| --- | --- |
| `gateway` | `GET /api/v1/health` (process is up) and `GET /api/v1/ready` (includes the database) |
| `feature-gateway`, `storage-proxy`, `serving-manager`, `trace-proxy`, `agent-runtime` | `GET /healthz` |
| `postgres`, `redis`, `kafka`, `kafka-rest`, `objectstore`, `mlflow`, `dex`, `prefect-server`, `jupyter` | Docker health check, shown by `docker compose ps` |

```bash
make -C deploy local-status
```

## Startup order and restarts

Compose starts services in dependency order: PostgreSQL, Kafka, object storage
and Dex first, then MLflow and the services that need them. `objectstore-init`
and `feature-materializer` run once and exit; `make -C deploy local-status`
shows them as exited. Every other service restarts automatically
(`restart: unless-stopped`) unless you stop the stack.

## Kubernetes package

The Helm chart in `deploy/helm/kionga` runs these components. The database,
identity provider, Kafka REST, MLflow, pipeline engine and object storage are
prerequisites you provide.

| Component | Replicas (default) | Port | Health, readiness |
| --- | --- | --- | --- |
| `gateway` | 3, autoscaling to 10 | 8080 | `/api/v1/health`, `/api/v1/ready` |
| `operator` | 2 | 8082 | `/healthz`, `/readyz` |
| `integration-worker` | 2 | 8086 | `/healthz`, `/readyz` |
| `feature-gateway` | 2 | 8083 | `/healthz` |
| `storage-proxy` | 2 | 8084 | `/healthz` |
| `trace-proxy` | 2 | 8081 | `/healthz` |

The operator also creates a workspace for each user and a runtime for each agent.
See [Deploy on Kubernetes](../operations/managed-kubernetes.md).
