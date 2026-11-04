---
icon: material/tune-variant
description: Every environment variable and configuration file setting Kionga services read, with defaults and purpose.
---

# Configuration reference

Kionga services are configured with environment variables. Defaults in this page
are the values the local stack (`deploy/compose.yaml`) uses. The single-server and
Kubernetes packages use a non-secret configuration file plus mounted secret files;
see [Configuration files and secret files](#configuration-files-and-secret-files)
and [Production readiness](../operations/production-operations.md).

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
| `DATABASE_URL` | *(set in compose)* | PostgreSQL DSN. When unset, the gateway uses a **local JSON file** instead |
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
| `MLAIOPS_ALLOWED_ORIGIN` | *(unset)* | Console origin. Unset, the gateway answers cross-origin requests with `Access-Control-Allow-Origin: *` and never allows credentials, so browsers do not send the session cookie to it from other sites; a caller that already holds an API key can still call it from any origin. Production requires your HTTPS console origin, which also restricts workspace framing |
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

See [RBAC & security](rbac.md) for the full model and
[Single sign-on](../operations/single-sign-on.md) for LDAP, SAML and OAuth providers.

Personal API keys for local CLI/SDK use are managed in the console under
**Settings**. They are separate from the internal service token and OIDC
browser session.

## Gateway: deployment and security

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_ENVIRONMENT` | *(unset)* | `production` turns on startup validation (see below) |
| `KIONGA_CONFIG_FILE` | *(unset)* | Path to a JSON object of non-secret settings |
| `KIONGA_CREDENTIAL_KEY` | *(empty)* | Base64-encoded 32-byte key that encrypts stored Hugging Face tokens; required in production |
| `KIONGA_TRUSTED_PROXY` | *(unset)* | `true` trusts `X-Forwarded-For` for policy source-IP conditions |
| `KIONGA_TRUSTED_WORKSPACE_PROXY` | *(unset)* | `true` when a trusted proxy in front of Kionga serves workspaces |
| `KIONGA_WORKSPACE_BASE_DOMAIN` | *(unset)* | Separate DNS base domain for isolated per-user workspaces (Kubernetes) |
| `KIONGA_SCHEDULER` | *(on)* | `off` disables the pipeline scheduler and scheduled blog publishing on this replica |
| `KIONGA_LOG_RETENTION_DAYS` | `30` | Days of logs Kionga keeps |
| `KIONGA_LOG_EXPORTER_URL` | `http://log-exporter:8086` | Log exporter status endpoint |
| `KIONGA_IMAGE_REGISTRIES` | *(unset)* | Comma-separated registries allowed for per-run image overrides |
| `KIONGA_EXECUTOR` | *(unset)* | `kubernetes` runs container pipeline steps as Kubernetes Jobs |
| `KAFKA_REST_TOKEN` | *(empty)* | Optional bearer token for Kafka REST |
| `METRICS_PORT` | *(unset)* | Port for a separate metrics listener |
| `KIONGA_BLOG_MEDIA_BACKEND` | `s3` | Blog image storage; with `s3`, set `KIONGA_BLOG_MEDIA_S3_ENDPOINT`, `KIONGA_BLOG_MEDIA_S3_ACCESS_KEY`, `KIONGA_BLOG_MEDIA_S3_SECRET_KEY`, `KIONGA_BLOG_MEDIA_BUCKET` (`kionga-blog-media`) and optionally `KIONGA_BLOG_MEDIA_S3_REGION` |

### Configuration files and secret files

`KIONGA_CONFIG_FILE` points to a JSON object of string values, at most 64 KiB.
Keys must be uppercase variable names; a key already set in the environment wins.
Secrets are rejected in this file: names containing `PASSWORD`, `SECRET`,
`TOKEN` (except `OIDC_TOKEN_URL`) or `API_KEY`, names ending in `_FILE`, and the
secret variables below.

Each secret variable can instead be read from a file named by `<NAME>_FILE`
(set only one of the two): `DATABASE_URL`, `OIDC_CLIENT_SECRET`,
`MLAIOPS_INTERNAL_TOKEN`, `KIONGA_CREDENTIAL_KEY`, `S3_ACCESS_KEY`,
`S3_SECRET_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `REDIS_URL`,
`KAFKA_REST_TOKEN`, `KFP_TOKEN`, `MLFLOW_TOKEN`, `OPENFAAS_PASSWORD`,
`LANGFUSE_SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`LLM_UPSTREAM_API_KEY`, `KIONGA_JUPYTER_TOKEN`, `KIONGA_IDE_PASSWORD`,
`TRACE_SINK_TOKEN`, `MLAIOPS_LOCAL_PASSWORD`, `TRACE_PROXY_KEYS`.

### Production validation

With `KIONGA_ENVIRONMENT=production`, the gateway refuses to start unless:

- `DATABASE_URL`, every `OIDC_*` sign-in setting, `MLAIOPS_INTERNAL_TOKEN`,
  `KIONGA_CREDENTIAL_KEY` and `MLAIOPS_ALLOWED_ORIGIN` are set;
- the OIDC URLs and `MLAIOPS_ALLOWED_ORIGIN` use HTTPS, and `OIDC_REDIRECT_URL`
  is the allowed origin plus `/auth/callback`;
- `DATABASE_URL` is PostgreSQL with `sslmode=verify-full`;
- `OIDC_CLIENT_SECRET` and `MLAIOPS_INTERNAL_TOKEN` are at least 24 characters
  and contain neither `local` nor `change-me`;
- with `KIONGA_LOCAL_LOGIN=true`, `MLAIOPS_LOCAL_PASSWORD` is at least 16
  characters and contains none of `local`, `change-me` or `password`;
- `KIONGA_CREDENTIAL_KEY` decodes to 32 bytes.

## Pipeline runner

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_PIPELINE_JOB_TIMEOUT_SECONDS` | `3600` | Default timeout per container step (maximum 86400) |
| `MLAIOPS_PIPELINE_LOG_LIMIT_BYTES` | `65536` | Log bytes kept per step (maximum 1 MiB) |
| `MLAIOPS_PIPELINE_PIDS_LIMIT` | `256` | Process limit per step container (maximum 4096) |
| `MLAIOPS_PIPELINE_MAX_PARALLEL` | `8` | Steps run at the same time (maximum 64) |
| `MLAIOPS_PIPELINE_NETWORK` | `mlaiops_default` | Docker network for step containers |

## LLM providers

Used by the agent runtime and trace proxy.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_LLM_BACKEND` | `mock` | `openai` \| `anthropic` \| `openai-compatible` \| `mock` |
| `MLAIOPS_LLM_MODEL` | *(empty)* | Model name for the chosen backend |
| `MLAIOPS_LLM_BASE_URL` | `http://trace-proxy:8081/v1` | Base URL for the `openai` and `openai-compatible` backends; Compose points it at the trace proxy for capture |
| `OPENAI_API_KEY` | *(empty)* | The key the `openai` and `openai-compatible` backends send. Behind the trace proxy this is your Kionga project key, not a provider key; see [Project keys](../guides/agents.md#project-keys) |
| `ANTHROPIC_API_KEY` | *(empty)* | Provider key for the `anthropic` backend, which calls Anthropic directly (env-only; never logged or traced) |
| `LLM_UPSTREAM_URL` | `https://api.openai.com` | Where the trace proxy forwards calls |
| `LLM_UPSTREAM_API_KEY` | *(empty)* | Provider key the trace proxy sends upstream |
| `MLAIOPS_COST_PER_1K_INPUT` / `MLAIOPS_COST_PER_1K_OUTPUT` | `0` | USD per 1k tokens for cost accounting |

The `anthropic` backend calls Anthropic directly with `ANTHROPIC_API_KEY`; it does
not use `MLAIOPS_LLM_BASE_URL`, so the trace proxy does not capture those calls.
Langfuse tracing still records them when its keys are set.

!!! example "Enable real OpenAI-backed agents"
    ```bash
    # deploy/.env
    MLAIOPS_LLM_BACKEND=openai
    MLAIOPS_LLM_MODEL=gpt-4o
    LLM_UPSTREAM_API_KEY=sk-...
    ```

    Calls go to the trace proxy, which forwards them to `LLM_UPSTREAM_URL` with
    the provider key. Agents hold only a project key. For
    Anthropic, set `MLAIOPS_LLM_BACKEND=anthropic`, `MLAIOPS_LLM_MODEL`, and
    `ANTHROPIC_API_KEY` instead.

## Agent runtime

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_GRAPH_MODULE` | `agents.customer_support.graph:build` | The graph to serve (`module:function`) |
| `MLAIOPS_AGENT_NAME` / `MLAIOPS_AGENT_ID` | `customer-support` / *(empty)* | Default identity (overridden per request by the gateway) |
| `MLAIOPS_URL` | `http://gateway:8080` | Where the runtime reports sessions |
| `DATABASE_URL` / `MLAIOPS_CHECKPOINT_DSN` | PostgreSQL DSN | Session checkpoint storage |
| `MLAIOPS_FEATURE_GATEWAY_URL` | `http://feature-gateway:8083` | Feature retrieval for tools/memory |
| `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | local defaults | Tracing |
| `MLAIOPS_RUNTIME_HOST` / `MLAIOPS_RUNTIME_PORT` | `0.0.0.0` / `9000` | Bind address |

## Sandbox manager

See [Sandboxes and gVisor](../operations/sandboxes.md).

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_SANDBOX_TOKEN` | Generated by `make local-up` | Bearer token shared by the gateway and the manager. |
| `KIONGA_SANDBOX_URL` | `http://sandbox-manager:8088` | Where the gateway reaches the manager. |
| `KIONGA_SANDBOX_RUNTIME` | `runsc` | Container runtime, or the RuntimeClass name on Kubernetes. |
| `KIONGA_SANDBOX_ALLOW_UNSAFE_RUNTIME` | Empty | `1` permits another runtime for local development only. Refused in production. |
| `KIONGA_SANDBOX_IMAGES` | Empty | Comma-separated allowlist of images pinned by digest. Creates return 503 while it is empty. |
| `KIONGA_SANDBOX_HELPER_IMAGE` | First allowed image | Image for git helpers, pinned by digest. |
| `KIONGA_SANDBOX_GIT_HOSTS` | Empty | Comma-separated hosts git can reach over HTTPS. Empty refuses git tools. |
| `KIONGA_SANDBOX_GIT_NETWORK` | `bridge` | Engine network for git helpers. |
| `KIONGA_SANDBOX_TTL_SECONDS` | `86400` | Removes sandboxes older than this. |
| `KIONGA_SANDBOX_DRIVER` | `docker` | `docker` or `kubernetes`. |
| `KIONGA_SANDBOX_NAMESPACE` | Set by the chart | Sandbox namespace on Kubernetes. |
| `KIONGA_SANDBOX_NAME_PREFIX` | `kionga-sandbox-` | Prefix for the objects the manager creates. |
| `KIONGA_SANDBOX_STORAGE_CLASS` | Set by the chart | Storage class for workspace volumes on Kubernetes. |

## Agent teams

Set these on the gateway. Empty uses the default. On a single server, use the
`deployment.json` key shown. On Kubernetes, use the `agentTeams` chart value.

| Variable | `agent_teams.tuning` key | `agentTeams` value | Purpose |
| --- | --- | --- | --- |
| `KIONGA_AGENT_TURN_TIMEOUT_SECONDS` | `turn_timeout_seconds` | `turnTimeoutSeconds` | How long the gateway waits for one model call. |
| `KIONGA_TEAM_COMPACT_THRESHOLD_TOKENS` | `compact_threshold_tokens` | `compactThresholdTokens` | Input size that triggers transcript compaction. Default 120,000. A worker over this size with only its 10 protected recent turns left fails with `context_exhausted`. |
| `KIONGA_TEAM_WORKER_POOL` | `worker_pool` | `workerPool` | Workers one gateway runs at a time. |
| `KIONGA_TEAM_SANDBOX_RETENTION_SECONDS` | `sandbox_retention_seconds` | `sandboxRetentionSeconds` | How long sandboxes stay after a run ends. Default 24 hours. |
| `KIONGA_TEAM_SCHEDULER` | `scheduler` | `scheduler` | `off` stops the team scheduler on this gateway. |

## Secret references

Knowledge bases and agent API connections name their credential as `env:NAME`. Kionga
resolves a name only if it is permitted for that resource.

| Resource | Prefix | Other permitted names | Allowlist variable |
| --- | --- | --- | --- |
| Knowledge base | `KIONGA_KB_SECRET_*` | `KIONGA_QDRANT_KEY`, `KIONGA_KNOWLEDGE_DSN` | `KIONGA_KB_SECRET_REFS` |
| Agent API connection | `KIONGA_CONNECTION_SECRET_*` | `KIONGA_AGENT_API_TOKEN` | `KIONGA_CONNECTION_SECRET_REFS` |

The allowlists are comma-separated names. The gateway's own secrets are refused even when you
allowlist them, and neither resource can read the other's variables.

Supply the values for your deployment:

| Deployment | How |
| --- | --- |
| Single server | Put one file per name in `secrets_directory`, and list the names in `secret_references.files` in `deployment.json`. Use `secret_references.knowledge_allowlist` and `connection_allowlist` for the allowlists. The installer refuses names that are not permitted. |
| Kubernetes | Create the Secret `secretReferences.secretName` with one key per name, and list the names in `secretReferences.names`. Use `knowledgeAllowlist` and `connectionAllowlist` for the allowlists. |
| Local | Put `NAME=value` lines in `deploy/config/secrets/gateway.env`, which Git ignores. Set the allowlists in `deploy/.env`. |

To change a stored reference that uses another name, see
[Migrate a stored reference](../guides/langflow.md#migrate-a-stored-reference).

## Serving manager

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_INTERNAL_TOKEN` | *(required)* | The manager refuses to start without it, in every environment. With `KIONGA_ENVIRONMENT=production` it needs at least 24 characters and must contain neither `local` nor `change-me` |
| `SERVE_IMAGE` | `mlaiops-mlflow` | Fallback for models registered without a framework-specific `serving_image`. Always allowed |
| `SERVE_IMAGE_ALLOWED_PREFIXES` | *(empty: only `SERVE_IMAGE`)* | Image prefixes a model's `serving_image` may use. Anything else returns `422` before any engine call |
| `SERVE_IMAGE_REQUIRE_DIGEST` | `true` in production, otherwise `false` | Require a `serving_image` to carry an `@sha256:` digest. Production refuses `false` |
| `SERVE_FETCH_IMAGE` | `SERVE_IMAGE` | Trusted image with MLflow and boto3 that downloads model artifacts. A request's `serving_image` never runs this step |
| `SERVE_READY_TIMEOUT_SECONDS` | `80` | One budget for the download and model load. Keep it below the gateway's 90-second call |
| `SERVE_PIDS_LIMIT` | `256` | Serving-container process/thread limit (manager caps it at `4096`) |
| `PLATFORM_NETWORK` | `mlaiops_default` | Docker network to attach serving containers to |
| `DOCKER_API_VERSION` | *(unset = negotiate)* | Pin the Docker Engine API version if needed |
| `MLFLOW_TRACKING_URI` / `MLFLOW_S3_ENDPOINT_URL` / `AWS_*` | compose defaults | Model source. These reach only the short-lived fetch container, never the model server |

Each deploy downloads the artifact into a per-deployment volume with a short-lived
fetch container, then starts the model server with an empty environment and that
volume mounted read-only. A deploy returns only when the server is healthy; a
failed deploy removes its containers and volume. Model servers deployed before
this behavior keep their credentials until you redeploy them.

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
| `TRACE_PROXY_KEYS` / `TRACE_PROXY_KEYS_FILE` | *(required)* | JSON array of accepted project keys, stored as SHA-256 hashes; see [Project keys](../guides/agents.md#project-keys). Without keys the proxy refuses to start |
| `TRACE_PROXY_ALLOW_UNAUTHENTICATED` | `false` | Development only: accept unauthenticated callers and pass their credentials through. Refused with `KIONGA_ENVIRONMENT=production` and together with `LLM_UPSTREAM_API_KEY` |
| `LLM_UPSTREAM_API_KEY` / `LLM_UPSTREAM_API_KEY_FILE` | *(empty)* | Provider key sent upstream. Empty sends no credential, for a self-hosted server that needs none. The caller's credentials are always removed |
| `LLM_UPSTREAM_AUTH_HEADER` | `Authorization` | Header for that key: `x-api-key` for Anthropic, `api-key` for Azure OpenAI |
| `LLM_UPSTREAM_AUTH_SCHEME` | `Bearer` for `Authorization`, otherwise none | Prefix for that key |
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

## Compose public overlay

The variables below apply only to the `deploy/compose.public.yaml` overlay. Do
not use this overlay for a production deployment. Use the [public VM](../operations/public-vm.md) or
[managed Kubernetes](../operations/managed-kubernetes.md) package instead.

| Variable | Purpose |
| --- | --- |
| `MLAIOPS_DOMAIN` | DNS name; Caddy provisions TLS for it |
| `MLAIOPS_ACME_EMAIL` | Let's Encrypt account email |
| `DEX_ADMIN_EMAIL` / `DEX_ADMIN_PASSWORD_HASH` | Console login (a `bcrypt` hash) |
| `DEX_CLIENT_SECRET` | Console OAuth client secret |
| `MLAIOPS_LOCAL_PASSWORD` | Break-glass local administrator password (required) |
| `MLAIOPS_INTERNAL_TOKEN` | Protects internal service APIs |
| `LANGFUSE_NEXTAUTH_SECRET` / `LANGFUSE_SALT` | Langfuse hardening |
| `POSTGRES_PASSWORD`, `OBJECTSTORE_ACCESS_KEY` / `OBJECTSTORE_SECRET_KEY` | Database password and object store keys (hex, for example `openssl rand -hex 24`) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_INIT_USER_PASSWORD` | Langfuse project keys and administrator password; Langfuse is published at `/langfuse` |
| `JUPYTER_TOKEN`, `IDE_PASSWORD`, `KIONGA_WORKSPACE_JOB_TOKEN`, `KIONGA_WORKSPACE_API_TOKEN`, `KIONGA_DESIGNER_RUNNER_TOKEN` | Workspace and runner credentials |
| `LANGFLOW_SUPERUSER_PASSWORD` / `LANGFLOW_SECRET_KEY` | Langflow credentials |
| `DEX_LDAP_BIND_PASSWORD` | Required only with `KIONGA_SSO_LDAP=true` |

The overlay refuses to start when any of these is unset or equal to a local
default: a preflight check runs before Caddy, Dex, the gateway, Langfuse,
PostgreSQL, the object store and Jupyter start.

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

## Tests

| Variable | Purpose |
| --- | --- |
| `TEST_DATABASE_URL` | PostgreSQL DSN for the Go integration lane (`make -C platform test-integration` sets it) |
| `TEST_MEMORY_DSN` | pgvector DSN for the SDK's agent-memory round-trip test (`sdk-python`) |
| `MLAIOPS_RUN_EVALS` | Set to `1` to run the paid agent evaluation lane (needs a real provider key) |

## Kubernetes scale path (optional)

Read by the operator and integration worker only:

| Variable | Default | Purpose |
| --- | --- | --- |
| `KFP_URL` / `KFP_TOKEN` / `KFP_EXPERIMENT_ID` | installation-specific | Kubernetes pipeline execution |
| `MLFLOW_URL` | in-cluster MLflow | Model lifecycle integration |
| `WORKBENCH_IMAGE` | `ghcr.io/kiongahq/jupyter:latest` | Image for provisioned Jupyter containers |
| `IDE_IMAGE` | `ghcr.io/kiongahq/ide:latest` | Image for provisioned IDE containers |
| `KIONGA_IMAGE_PULL_SECRETS` | unset | Comma-separated Secret names referenced by every workspace and agent pod (private registries). The Secrets must exist in the workload namespace. Helm sets it from `imagePullSecrets` |
| `WORKSPACE_STORAGE_CLASS` | cluster default | Storage class for per-user PVCs |
| `WORKSPACE_FEATURE_URL` / `WORKSPACE_STORAGE_URL` | in-cluster platform services | Feature and object access injected into each workspace |
| `WORKSPACE_MLFLOW_URL` / `WORKSPACE_PREFECT_URL` | in-cluster upstreams | Experiment and orchestration endpoints injected into each workspace |
| `WORKSPACE_LANGFUSE_URL` / `WORKSPACE_KAFKA_REST_URL` | in-cluster upstreams | Observability and event endpoints injected into each workspace |
| `MLAIOPS_TARGET_NAMESPACE` | `default` | Namespace where lifecycle CRDs and workspaces are created |
| `MLAIOPS_AGENT_NAMESPACE` | `default` | Namespace the gateway uses for ID-derived agent Service DNS; keep equal to the agent lifecycle target namespace |
| `TRACE_PROXY_IMAGE` | `ghcr.io/kiongahq/trace-proxy:latest` | Sidecar image reconciled into every Kubernetes agent pod |

These configure the Kubernetes fidelity path and are not needed for local or
single-VM use. If `AGENT_RUNTIME_URL` remains set in a Kubernetes gateway it
deliberately disables per-agent Service selection, so reserve that override for the
shared Compose topology. Elastic agents additionally require a working Kubernetes
resource-metrics API (normally metrics-server). A `KiongaWorkspace` receives a
generated authentication secret; put its internal service behind the organization's
authenticated ingress before exposing it outside the cluster.
