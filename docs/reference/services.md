# Services overview

The default stack declares 21 regular and one-shot services on one Compose network
(`deploy/compose.yaml`), plus four optional profiles (`ide`, `log-export`,
`log-export-es`, `log-export-os`) and dynamically launched model-serving
containers. This section documents each one.

Host ports bind to `127.0.0.1` by default (`KIONGA_BIND_ADDRESS` widens them; see
[Network exposure](../operations/local.md#network-exposure)).

## Full inventory

| Service | Image / build | Host port | Group | Role |
| --- | --- | --- | --- | --- |
| **gateway** | `platform/go/Dockerfile` (`SERVICE=gateway`) | 8080 | Control plane | REST API + embedded console |
| **dex** | `ghcr.io/dexidp/dex:v2.46.0` | 5556 | Control plane | Single sign-on broker (OIDC issuer) |
| **glauth** | `glauth/glauth:v2.5.4` | none | Control plane | Local LDAP test directory for Dex |
| **postgres** | `pgvector/pgvector:pg16` | 5432 | Data plane | Control-plane, MLflow, Langfuse, checkpoints, vectors |
| **redis** | `redis:7.4.5-alpine` | 6379 | Data plane | Online feature store |
| **kafka** | `apache/kafka:3.9.1` | 9092 | Data plane | Events, traces, real-time topics |
| **kafka-rest** | `ghcr.io/aiven-open/karapace:6.1.4` | 8082 | Data plane | Confluent-compatible HTTP access to Kafka |
| **objectstore** | `rustfs/rustfs:1.0.1` | 9000 / 9001 | Data plane | S3 object storage + console |
| **objectstore-init** | `mlaiops-mlflow` (boto3) | none | Data plane | One-shot bucket creation |
| **mlflow** | `mlaiops-mlflow` (`deploy/mlflow/Dockerfile`) | 15000 | Data plane | Tracking + registry |
| **feature-gateway** | `platform/go/Dockerfile` (`SERVICE=feature-gateway`) | 8083 | Data plane | Online feature retrieval |
| **storage-proxy** | `platform/go/Dockerfile` (`SERVICE=storage-proxy`) | 8084 | Data plane | SigV4 S3 URLs + browse |
| **prefect-server** | `prefecthq/prefect:3-latest` | 4200 | Execution | Pipeline engine |
| **pipeline-runner** | `pipeline-runner/Dockerfile` | none | Execution | Serves + runs platform flows |
| **serving-manager** | `serving/Dockerfile` | 8085 | Execution | Launches model-serving containers |
| **agent-runtime** | `agent-runtime/Dockerfile` | 19000 | AI | Serves LangGraph agents |
| **trace-proxy** | `trace-proxy/Dockerfile` | 8081 | AI | LLM egress + trace capture |
| **langfuse** | `langfuse/langfuse:2` | 3000 | AI | LLM/agent observability |
| **realtime-processor** | `agent-runtime/Dockerfile` | none | AI | Kafka stream scoring |
| **feature-materializer** | `mlaiops-agent-runtime` (the agent-runtime image) | none | Data plane | One-shot feature materialization |
| **jupyter** | `workspace/jupyter/Dockerfile` | 8888 (always `127.0.0.1`) | Dev | Notebooks + terminal, opened through the gateway |
| **ide** *(profile `ide`)* | `workspace/ide/Dockerfile` | none (gateway proxy) | Dev | Browser IDE sharing the Jupyter workspace |
| **log-exporter** *(profile `log-export`)* | `platform/go/Dockerfile` (`SERVICE=log-exporter`) | 8086 (always `127.0.0.1`) | Observability | Ships logs to Elasticsearch or OpenSearch |

## The four groups

- **[Gateway (control plane)](https://kiongahq.github.io/docs/engineering/components/gateway/)**: the single service that owns the API,
  serves the console, and orchestrates everything else, plus the supporting Go
  services (operator, integration worker, metrics collector) used on Kubernetes.
- **[Data & messaging](https://kiongahq.github.io/docs/engineering/components/data-plane/)**: Postgres, Redis, Kafka, RustFS, MLflow,
  and the two Go data services (feature gateway, storage proxy).
- **[Execution & serving](https://kiongahq.github.io/docs/engineering/components/execution/)**: Prefect, the pipeline runner, and the
  serving manager.
- **[AI & observability](https://kiongahq.github.io/docs/engineering/components/ai-observability/)**: the agent runtime, trace proxy,
  Langfuse, and the real-time processor.

Dex and GLAuth are covered in [Single sign-on](../operations/single-sign-on.md).

## Health checks

Docker health checks cover postgres, redis, kafka, kafka-rest, objectstore, mlflow,
dex, prefect-server, and jupyter. Go services expose `GET /healthz`; the gateway exposes
`GET /api/v1/health`; the agent runtime exposes `GET /healthz`. Check everything at
once:

```bash
docker compose -f deploy/compose.yaml ps
```

## Dependency & startup order

Compose `depends_on` enforces the boot order: Postgres, Kafka, the object store,
and Dex come up first, then MLflow and the Go and Python services that need them. `objectstore-init` and
`feature-materializer` are **one-shot** jobs (`restart: "no"`) that complete and
exit. `pipeline-runner`, `realtime-processor`, `serving-manager`, and `agent-runtime`
run continuously (`restart: unless-stopped` where applicable).

OpenFaaS/faasd is not a Compose service. It is an external function engine connected
with `OPENFAAS_URL`. Model-serving containers are created dynamically by the
serving manager and therefore do not appear as static Compose services.
