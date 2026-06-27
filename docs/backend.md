# Backend architecture

The repository implements the platform-owned services from the PRD. Large upstream systems
remain independently deployable dependencies and are reached through their standard APIs.

## Service inventory

| Binary | Default port | Responsibility |
|---|---:|---|
| `mlaiops-gateway` | 8080 | Projects, runs, models, agents, tools, connections, audit |
| `mlaiops-operator` | 8082 | Deterministic CRD-to-workload reconciliation plans |
| `mlaiops-feature-gateway` | 8083 | Feast-compatible online feature retrieval |
| `mlaiops-storage-proxy` | 8084 | Short-lived AWS SigV4 S3 URLs |
| `mlaiops-trace-proxy` | 8081 | OpenAI-compatible reverse proxy and trace emission |
| `mlaiops-metrics-collector` | 9090 | Prometheus component health metrics |
| `mlaiops` | n/a | Operator and engineer CLI |

All services are built from the root `Dockerfile`:

```bash
docker build --build-arg SERVICE=gateway -t mlaiops/gateway .
docker build --build-arg SERVICE=feature-gateway -t mlaiops/feature-gateway .
```

## Control-plane API

Resource mutations produce durable audit events. State is atomically persisted to
`MLAIOPS_DATA_PATH`; local mode defaults to `data/platform.json`.

| Resource | Operations |
|---|---|
| Projects | create, list |
| Pipelines | submit, list runs |
| Models | register, list, promote |
| Agents | deploy, list, set canary traffic |
| Tools | register typed schema, list |
| Connections | create secret reference, list |
| Audit | ordered event list |

Set `X-MLAIOps-Actor` on mutation requests for audit attribution. Secrets are represented only
by Kubernetes Secret references; raw credentials are never accepted by the control-plane API.

## Integration contracts

- Kubeflow Pipelines v2: `/apis/v2beta1/runs`
- MLflow: `/api/2.0/mlflow/model-versions/transition-stage`
- Langfuse: `/api/public/ingestion`
- Kafka REST Proxy: `/topics/{topic}`
- S3/MinIO: AWS Signature Version 4 presigned URLs
- Agent serving: OpenAI-compatible LLM calls through the trace proxy

The integration clients fail closed when their base URL is absent or an upstream returns a
non-2xx response.

## Kubernetes resources

CRDs live in `config/crd`, RBAC in `config/rbac`, workload manifests in `config/deploy`, and
default isolation in `config/network`.

The current durable gateway store is a single-writer local/PVC implementation and therefore
the supplied manifest runs one gateway replica. A PostgreSQL repository is required before
raising the gateway replica count. The PRD's upstream PostgreSQL, Kafka, KFP/Argo, MLflow,
Feast/Redis, KServe/Knative, MinIO, and Langfuse installations are intentionally not vendored.

## Configuration

| Variable | Component | Meaning |
|---|---|---|
| `MLAIOPS_DATA_PATH` | gateway | Durable control-plane state file |
| `MLAIOPS_INTERNAL_TOKEN` | feature/storage | Internal API bearer token |
| `S3_ENDPOINT` | storage proxy | MinIO or S3-compatible endpoint |
| `S3_REGION` | storage proxy | S3 signing region |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | storage proxy | Inject from Vault/Kubernetes Secret |
| `LLM_UPSTREAM_URL` | trace proxy | KServe/vLLM or external compatible endpoint |
| `TRACE_SINK_URL`, `TRACE_SINK_TOKEN` | trace proxy | Langfuse/event ingestion target |
| `MLAIOPS_METRICS_TARGETS` | metrics collector | `name=url` comma-separated health endpoints |
| `MLAIOPS_URL` | CLI | Gateway base URL |

## Production gates

Before production rollout:

1. Replace file persistence with PostgreSQL and row-level tenant isolation.
2. Attach OIDC/JWKS validation and namespace RBAC at the gateway.
3. Run operator reconciliation from Kubernetes watches with leader election.
4. Inject storage and integration credentials through Vault.
5. Install upstream operators and pin versions from the PRD matrix.
6. Execute load, failure, recovery, and security tests against a real cluster.
