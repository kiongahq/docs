# Configuration reference

The local Compose stack uses environment variables and development defaults. This
page lists those settings and service-specific variables. The recommended public
VM and managed Kubernetes packages use versioned non-secret configuration plus
mounted secret files; see [Public hosting](../hosting.md) for their requirements.

!!! danger "Secrets"
    Never commit `.env` or put provider API keys or internal tokens in Compose
    files. Local credentials shown here are development defaults, not public
    deployment credentials.

## Published ports

Every port is overridable via the `*_PORT` variable, set in `deploy/.env` or
exported before `make -C deploy local-up`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_BIND_ADDRESS` | `127.0.0.1` | Host address every published port below binds to. Set `0.0.0.0` (or one interface address) only on a trusted network; see [Network exposure](../operations/local.md#network-exposure) |

Ports that follow `KIONGA_BIND_ADDRESS`:

| Variable | Default | Service |
| --- | --- | --- |
| `GATEWAY_PORT` | `8080` | Console + API |
| `DEX_PORT` | `5556` | Dex, the single sign-on broker |
| `MLFLOW_PORT` | `15000` | MLflow (container listens on 5000) |
| `PREFECT_PORT` | `4200` | Prefect |
| `LANGFUSE_PORT` | `3000` | Langfuse |
| `OBJECTSTORE_PORT` / `OBJECTSTORE_CONSOLE_PORT` | `9000` / `9001` | RustFS S3 / console |
| `OBJECTSTORE_ACCESS_KEY` / `OBJECTSTORE_SECRET_KEY` | `mlaiops` / `mlaiops-local-secret` | RustFS root credentials (development defaults) |
| `POSTGRES_PORT` | `5432` | PostgreSQL |
| `REDIS_PORT` | `6379` | Redis |
| `KAFKA_PORT` | `9092` | Kafka broker |
| `KAFKA_REST_PORT` | `8082` | Kafka REST proxy |
| `FEATURE_GATEWAY_PORT` | `8083` | Feature gateway |
| `STORAGE_PROXY_PORT` | `8084` | Storage proxy |
| `SERVING_MANAGER_PORT` | `8085` | Serving manager |
| `TRACE_PROXY_PORT` | `8081` | Trace proxy |
| `AGENT_RUNTIME_PORT` | `19000` | Agent runtime (container listens on 9000; the object store owns host 9000) |

Ports that always bind to `127.0.0.1`, whatever `KIONGA_BIND_ADDRESS` says:

| Variable | Default | Service |
| --- | --- | --- |
| `JUPYTER_PORT` | `8888` | Jupyter workbench (diagnostics; use it through the gateway) |
| `LOG_EXPORTER_PORT` | `8086` | Log exporter status (`log-export` profile) |

The browser IDE (`ide` profile) publishes no port; the gateway proxies it. In the
public overlay (`compose.public.yaml`) only Caddy publishes ports (80 and 443).

## Gateway (control plane)

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` | Listen port |
| `DATABASE_URL` | *(set in compose)* | Postgres DSN. When unset, the gateway uses a **local JSON file** instead |
| `MLAIOPS_DATA_PATH` | `data/platform.json` | File-store path (file mode only) |
| `MLAIOPS_TENANT` | `local` | Tenant scoping |
| `KAFKA_REST_URL` | `http://kafka-rest:8082` | Outbox delivery target |
| `AGENT_RUNTIME_URL` | `http://agent-runtime:9000` in Compose; unset on Kubernetes | Static shared-runtime override. When non-empty it takes precedence over per-agent Kubernetes routing |
| `MLAIOPS_AGENT_NAMESPACE` | `default` | Kubernetes namespace used to derive each agent Service endpoint when `AGENT_RUNTIME_URL` is unset |
| `STORAGE_PROXY_URL` | `http://storage-proxy:8084` | Storage browse proxy target |
| `PREFECT_API_URL` | `http://prefect-server:4200/api` | Pipeline engine |
| `SERVING_MANAGER_URL` | `http://serving-manager:8085` | Model serving control |
| `LANGFUSE_URL` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | local defaults | Prompt library proxy |
| `MLAIOPS_LOCAL_ROLE` | `admin` | Role of the local login account (`MLAIOPS_LOCAL_USERNAME`); every API request still needs a credential |
| `MLAIOPS_ALLOWED_ORIGIN` | `*` | CORS origin (pinned to your domain in public) |
| `MLAIOPS_INTERNAL_TOKEN` | `kionga-local-service-token` in Compose | Shared bearer token granting the `service` role; set your own outside local development |

## RBAC

| Variable | Values | Purpose |
| --- | --- | --- |
| `MLAIOPS_LOCAL_ROLE` | `admin` \| `operator` \| `user` \| `engineer` \| `viewer` | Role for the authenticated local login; `user` requires a grant keyed by `MLAIOPS_LOCAL_USERNAME` |
| `MLAIOPS_LOCAL_USERNAME` / `MLAIOPS_LOCAL_PASSWORD` | `admin` / `mlaiops-local` | Local console login; change outside throwaway development. The password can also be delivered as a file with `MLAIOPS_LOCAL_PASSWORD_FILE` |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | provider client | Browser authorization-code flow |
| `OIDC_AUTH_URL` / `OIDC_TOKEN_URL` / `OIDC_REDIRECT_URL` | provider URLs | Browser login endpoints and callback |
| `MLAIOPS_INTERNAL_TOKEN` | random secret | Presenting it as a bearer token grants the `service` role (reporting endpoints only) |
| `OIDC_ISSUER` | URL | Enables OIDC auth; when set, roles come from token claims |
| `OIDC_JWKS_URL` | URL | Required with `OIDC_ISSUER`; JWKS for signature verification |
| `OIDC_AUDIENCE` | string | Expected token audience |
| `KIONGA_SSO_PROVIDERS` | JSON list of `{id, name, type}` | Sign-in buttons on the login page; `id` is the Dex connector id |
| `KIONGA_SSO_PROVIDERS_FILE` | path | The same list from a file, re-read when it changes (the Compose stack's Dex writes it) |
| `OIDC_SCOPES` | space-separated | Scopes requested at sign-in. Compose sets `openid profile email groups federated:id`; `federated:id` is Dex-only |
| `KIONGA_SIGNUP` | `approval` \| `open` \| `off` | What a first single sign-on creates: an access request (default), a starter account, or nothing. See [Sign-up](../operations/single-sign-on.md#sign-up) |
| `KIONGA_SIGNUP_EMAIL_DOMAINS` | comma-separated | Only verified emails at these domains sign up |
| `KIONGA_SIGNUP_PROFILE` | resource profile | Profile for `open` sign-up (default `starter`) |
| `KIONGA_SIGNUP_SERVICES` | comma-separated | Services a sign-up requests or gets |
| `KIONGA_SSO_GROUP_ROLES` | JSON object, group to role | Maps identity-provider groups to platform roles when the token has no `roles` claim |
| `KIONGA_SSO_SINGLE_TENANT` | `true` | Tokens without a `tenant` claim belong to `MLAIOPS_TENANT` (Dex cannot add one) |
| `KIONGA_LOCAL_LOGIN` | `true` | Keeps local accounts next to single sign-on as break-glass access; requires `MLAIOPS_LOCAL_PASSWORD`. With `KIONGA_ENVIRONMENT=production` the password must be at least 16 characters and must not contain `local`, `change-me`, or `password` |

Local sign-in is throttled per account: after 5 failed attempts each further
attempt waits a doubling delay (1 s, 2 s, 4 s, up to 60 s). Failures are
forgotten after 15 minutes or on a successful sign-in. The local session cookie
is HttpOnly and SameSite=Lax, and Secure when the gateway is reached over HTTPS
(directly or with `X-Forwarded-Proto: https`).

See [RBAC & security](../reference/rbac.md) for the full model and
[Single sign-on](../operations/single-sign-on.md) for LDAP, SAML and OAuth providers.

Personal API keys for local CLI/SDK use are managed in the console under
**Settings**. They are separate from the internal service token and OIDC
browser session.

## LLM providers

Used by the agent runtime and trace proxy.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_LLM_BACKEND` | `mock` | `openai` \| `anthropic` \| `openai-compatible` \| `mock` |
| `MLAIOPS_LLM_MODEL` | *(empty)* | Model name for the chosen backend |
| `MLAIOPS_LLM_BASE_URL` | `http://trace-proxy:8081/v1` | Base URL for the `openai` and `openai-compatible` backends; Compose points it at the trace proxy for capture |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | *(empty)* | Provider keys (env-only; never logged or traced) |
| `LLM_UPSTREAM_URL` | `https://api.openai.com` | Where the trace proxy forwards calls |
| `MLAIOPS_COST_PER_1K_INPUT` / `MLAIOPS_COST_PER_1K_OUTPUT` | `0` | USD per 1k tokens for cost accounting |

The `anthropic` backend calls Anthropic directly with `ANTHROPIC_API_KEY`; it does
not use `MLAIOPS_LLM_BASE_URL`, so the trace proxy does not capture those calls.
Langfuse tracing still records them when its keys are set.

!!! example "Enable real OpenAI-backed agents"
    ```bash
    # deploy/.env
    MLAIOPS_LLM_BACKEND=openai
    MLAIOPS_LLM_MODEL=gpt-4o
    OPENAI_API_KEY=sk-...
    ```

    Calls go to the trace proxy, which forwards them to `LLM_UPSTREAM_URL`. For
    Anthropic, set `MLAIOPS_LLM_BACKEND=anthropic`, `MLAIOPS_LLM_MODEL`, and
    `ANTHROPIC_API_KEY` instead.

## Agent runtime

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_GRAPH_MODULE` | `agents.customer_support.graph:build` | The graph to serve (`module:function`) |
| `MLAIOPS_AGENT_NAME` / `MLAIOPS_AGENT_ID` | `customer-support` / *(empty)* | Default identity (overridden per request by the gateway) |
| `MLAIOPS_URL` | `http://gateway:8080` | Where the runtime reports sessions |
| `DATABASE_URL` / `MLAIOPS_CHECKPOINT_DSN` | Postgres DSN | Session checkpoint storage |
| `MLAIOPS_FEATURE_GATEWAY_URL` | `http://feature-gateway:8083` | Feature retrieval for tools/memory |
| `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | local defaults | Tracing |
| `MLAIOPS_RUNTIME_HOST` / `MLAIOPS_RUNTIME_PORT` | `0.0.0.0` / `9000` | Bind address |

## Serving manager

| Variable | Default | Purpose |
| --- | --- | --- |
| `SERVE_IMAGE` | `mlaiops-mlflow` | Fallback for models registered without a framework-specific `serving_image` |
| `SERVE_PIDS_LIMIT` | `256` | Serving-container process/thread limit (manager caps it at `4096`) |
| `PLATFORM_NETWORK` | `mlaiops_default` | Docker network to attach serving containers to |
| `DOCKER_API_VERSION` | *(unset = negotiate)* | Pin the Docker Engine API version if needed |
| `MLFLOW_TRACKING_URI` / `MLFLOW_S3_ENDPOINT_URL` / `AWS_*` | compose defaults | Model source |

## Storage proxy

| Variable | Default | Purpose |
| --- | --- | --- |
| `S3_ENDPOINT` | `http://objectstore:9000` | Object store endpoint |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `mlaiops` / `mlaiops-local-secret` | Credentials (sole holder) |

## Feature gateway

| Variable | Default | Purpose |
| --- | --- | --- |
| `REDIS_URL` | `redis://redis:6379` | Online store |

## Trace proxy

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_UPSTREAM_URL` | `https://api.openai.com` | Forward target |
| `TRACE_SINK_FORMAT` | `kafka-rest` | Trace sink format |
| `TRACE_SINK_URL` | `http://kafka-rest:8082/topics/mlaiops.llm.traces` | Where traces are published |
| `TRACE_SINK_TOKEN` | *(empty)* | Optional sink auth |

## Real-time demos

| Variable | Default | Purpose |
| --- | --- | --- |
| `KAFKA_REST_URL` | `http://kafka-rest:8082` | Kafka access |
| `MLAIOPS_FEATURE_GATEWAY_URL` | `http://feature-gateway:8083` | Online feature enrichment |
| `FRAUD_MODEL_ENDPOINT` | *(empty)* | Live fraud model; falls back to a built-in rule when unset |
| `CALLCENTER_AGENT_ID` | *(empty)* | Deployed agent for transcript analysis; falls back to keyword sentiment |

## Serverless (OpenFaaS)

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENFAAS_URL` | *(unset)* | faasd/OpenFaaS gateway; unset means serverless is "not configured" |
| `OPENFAAS_USER` / `OPENFAAS_PASSWORD` | *(unset)* | Basic auth |

## Legacy Compose/Dex demo overlay

The variables below apply only to `deploy/compose.public.yaml`, retained for
compatibility testing. Do not use this overlay as the recommended public
deployment. Use the [public VM](../operations/public-vm.md) or
[managed Kubernetes](../operations/managed-kubernetes.md) package instead.

| Variable | Purpose |
| --- | --- |
| `MLAIOPS_DOMAIN` | DNS name; Caddy provisions TLS for it |
| `MLAIOPS_ACME_EMAIL` | Let's Encrypt account email |
| `DEX_ADMIN_EMAIL` / `DEX_ADMIN_PASSWORD_HASH` | Console login (bcrypt hash) |
| `DEX_CLIENT_SECRET` | Console OAuth client secret |
| `MLAIOPS_LOCAL_PASSWORD` | Break-glass local administrator password (required) |
| `MLAIOPS_INTERNAL_TOKEN` | Protects internal service APIs |
| `LANGFUSE_NEXTAUTH_SECRET` / `LANGFUSE_SALT` | Langfuse hardening |

## Jupyter workbench

| Variable | Default | Purpose |
| --- | --- | --- |
| `JUPYTER_TOKEN` | `mlaiops-local` | Login token |
| `S3_ENDPOINT` | `http://objectstore:9000` | S3-compatible endpoint mounted through S3FS |
| `S3_MOUNT_ROOT` | `/workspace/object-store` | Filesystem root for bucket mounts |
| `S3_MOUNT_BUCKETS` | platform bucket list | Space-separated buckets to mount |
| `KIONGA_WORKSPACE` | `/workspace` | Root in which the project generator and Git sync command may write |
| `KIONGA_CUSTOM_AGENT_COMMAND` | *(unset)* | Optional non-interactive coding-agent command used by the scaffolder |

## Browser IDE (optional profile)

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_IDE_UPSTREAM` | `http://ide:8080` in Compose | Internal address, accessed through the authenticated gateway |
| `KIONGA_JUPYTER_UPSTREAM` | `http://jupyter:8888` in Compose | Internal Jupyter address, using base URL `/workspaces/workbench/` |
| `KIONGA_JUPYTER_TOKEN` | `JUPYTER_TOKEN` in Compose | Upstream credential injected by the gateway, never returned to the browser |
| `KIONGA_WORKSPACE_NAMESPACE` | `default` in Kubernetes manifests | Discover the subject's KiongaWorkspace and generated credential in this namespace |
| `KIONGA_IDE_AUTH_MODE` | `password`; `none` inside Compose | Compose authenticates through the gateway and does not publish the IDE port; Kubernetes retains its generated password |
| `KIONGA_CUSTOM_AGENT_COMMAND` | *(unset)* | Optional non-interactive coding-agent command used by the scaffolder |

`KIONGA_SUBJECT` is injected into reconciled Kubernetes workspaces for identity
context; users should not override it. The platform API remains configured by
`MLAIOPS_URL` and `MLAIOPS_TOKEN`.

## Local file mode & tests

| Variable | Purpose |
| --- | --- |
| `TEST_DATABASE_URL` | Postgres DSN for the Go integration lane (`make -C platform test-integration` sets it) |
| `TEST_MEMORY_DSN` | pgvector DSN for the SDK's agent-memory round-trip test (`sdk-python`) |
| `MLAIOPS_RUN_EVALS` | Set to `1` to run the paid agent eval lane (needs a real provider key) |

## Kubernetes scale path (optional)

Read by the operator and integration worker only:

| Variable | Default | Purpose |
| --- | --- | --- |
| `KFP_URL` / `KFP_TOKEN` / `KFP_EXPERIMENT_ID` | installation-specific | Kubernetes pipeline execution |
| `MLFLOW_URL` | in-cluster MLflow | Model lifecycle integration |
| `WORKBENCH_IMAGE` | `ghcr.io/kiongahq/jupyter:latest` | Image for provisioned Jupyter containers |
| `IDE_IMAGE` | `ghcr.io/kiongahq/ide:latest` | Image for provisioned IDE containers |
| `WORKSPACE_STORAGE_CLASS` | cluster default | Storage class for per-user PVCs |
| `WORKSPACE_FEATURE_URL` / `WORKSPACE_STORAGE_URL` | in-cluster platform services | Feature and object access injected into each workspace |
| `WORKSPACE_MLFLOW_URL` / `WORKSPACE_PREFECT_URL` | in-cluster upstreams | Experiment and orchestration endpoints injected into each workspace |
| `WORKSPACE_LANGFUSE_URL` / `WORKSPACE_KAFKA_REST_URL` | in-cluster upstreams | Observability and event endpoints injected into each workspace |
| `MLAIOPS_TARGET_NAMESPACE` | `default` | Namespace where lifecycle CRDs and workspaces are created |
| `MLAIOPS_AGENT_NAMESPACE` | `default` | Namespace the gateway uses for ID-derived agent Service DNS; keep equal to the agent lifecycle target namespace |
| `TRACE_PROXY_IMAGE` | `ghcr.io/mlaiops/trace-proxy:latest` | Sidecar image reconciled into every Kubernetes agent pod |

These configure the Kubernetes fidelity path and are not needed for local or
single-VM use. If `AGENT_RUNTIME_URL` remains set in a Kubernetes gateway it
deliberately disables per-agent Service selection, so reserve that override for the
shared Compose topology. Elastic agents additionally require a working Kubernetes
resource-metrics API (normally metrics-server). A `KiongaWorkspace` receives a
generated authentication secret; put its internal service behind the organization's
authenticated ingress before exposing it outside the cluster.
