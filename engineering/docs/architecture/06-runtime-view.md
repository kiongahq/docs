---
description: arc42 section 6. Sequence diagrams for single sign-on, a pipeline run, model promotion and serving, and an agent turn with trace capture.
---

# 6. Runtime view

Four scenarios cover the paths that matter most: how a person signs in, how a
pipeline runs, how a model is promoted and served, and how an agent turn is executed
and traced. Each step names the route or function that implements it, so you can
follow it in the code.

## Sign-in through single sign-on

The gateway runs the OIDC authorization code flow against the configured issuer (Dex
in the local stack). The implementation is `platform/go/internal/auth/session.go` and
`platform/go/internal/auth/authenticator.go`.

```mermaid
sequenceDiagram
    autonumber
    actor U as Browser
    participant G as Gateway
    participant D as Dex (OIDC issuer)
    participant I as Upstream identity provider
    U->>G: GET /console.html (no session)
    G-->>U: 302 /auth/login?return_to=/console.html
    U->>G: GET /auth/login
    G-->>U: 302 /login.html, or straight to the only provider
    U->>G: GET /auth/sso/login?connector=ldap
    Note over G: Set state, PKCE verifier, nonce and<br/>return-to cookies (10 minutes)
    G-->>U: 302 issuer authorize URL<br/>(S256 challenge, nonce, connector_id)
    U->>D: Authorization request
    D->>I: Authenticate (LDAP bind, SAML, OAuth)
    I-->>D: Identity and groups
    D-->>U: 302 /auth/callback?code&state
    U->>G: GET /auth/callback
    G->>G: Compare state cookie with state parameter
    G->>D: Exchange code with PKCE verifier (OIDC_TOKEN_URL)
    D-->>G: ID token
    G->>D: Fetch signing keys (OIDC_JWKS_URL, cached 10 minutes)
    G->>G: Verify signature, issuer, audience and tenant, then check nonce
    G->>G: Sign-up policy (KIONGA_SIGNUP) for a first-time subject
    G-->>U: Set kionga_session (ID token, HttpOnly, 8 hours)<br/>302 to return_to
    U->>G: GET /api/v1/me (cookie)
    G->>G: Authenticator verifies the token, RBAC loads the access profile
    G-->>U: Identity and effective permissions
```

What to know:

- The callback host decides where the login cookies live. If the browser starts on a
  different host (for example `127.0.0.1` while the callback is `localhost`), the
  gateway first redirects to the callback's host.
- `KIONGA_SSO_GROUP_ROLES` maps identity-provider groups to platform roles. A signed-in
  subject with no mapped group and no access profile gets the `user` role and reaches
  only `/api/v1/me`, access requests and personal settings until provisioned.
- The session cookie is `Secure` when the callback URL is HTTPS. Production refuses a
  plain-HTTP `OIDC_REDIRECT_URL`.
- Local accounts use `/auth/local/login` instead. The gateway checks a `bcrypt` hash
  (or the bootstrap administrator from `MLAIOPS_LOCAL_USERNAME` and
  `MLAIOPS_LOCAL_PASSWORD`), throttles per account after five failures, and issues an
  in-memory session cookie `kionga_local_session` for eight hours.
- `/auth/logout` ends both kinds of session and revokes the subject's workspace
  sessions.

## Pipeline run

This is the Compose path, where Prefect executes the run. Handlers are in
`platform/go/internal/httpapi/server.go` (`submitPipeline`) and
`platform/go/internal/httpapi/pipeline_dispatch.go` (`dispatchPipeline`); the flows
are in the `pipeline-runner` repository.

```mermaid
sequenceDiagram
    autonumber
    actor U as Console or SDK
    participant G as Gateway
    participant P as PostgreSQL
    participant F as Prefect server
    participant R as Pipeline runner
    participant M as MLflow
    participant K as Kafka (via REST proxy)
    U->>G: POST /api/v1/pipelines/submit
    G->>G: RBAC, then IAM gate for pipelines run and each override
    G->>G: Preflight: project access, parameters, images, quotas, concurrency
    G->>P: One transaction: run (queued) + audit event + outbox rows
    G->>F: Create flow run (training-pipeline or pipeline-definition,<br/>deployment mlaiops, run_id, project_id)
    F-->>G: Flow run ID
    G->>P: Link run to engine ID
    G-->>U: 202 Accepted (run)
    loop Outbox worker, every second
        G->>P: Pending outbox rows
        G->>K: Publish audit and command events
        G->>P: Mark published
    end
    F->>R: Run the flow
    loop Each step
        R->>G: POST /api/v1/pipelines/runs/{id}/steps (service token)
        G->>P: Update step, recompute run status
        R->>G: POST /api/v1/pipelines/runs/{id}/logs
    end
    R->>M: Log run and model artifacts
    R->>G: POST /api/v1/models (register the version)
    U->>G: GET /api/v1/events (SSE digest every 3 seconds)
    G-->>U: Digest changed: reload the run view
```

Variations:

- **Engine missing.** Without `PREFECT_API_URL` the run is recorded and immediately
  marked failed at the `submit-to-engine` step with an explanation. It is never left
  queued as if work were pending.
- **Function DAGs.** A definition in `functions` mode runs through OpenFaaS. The gateway
  executes ready jobs from a `goroutine` started by the submit request. Without
  OpenFaaS, every job is marked failed with the reason.
- **Kubernetes Jobs.** With the opt-in Kubernetes executor, container definitions run
  as one hardened Job per node attempt instead of through Prefect.
- **Kubernetes lifecycle path.** The outbox also carries `mlaiops.pipeline.commands`.
  On Kubernetes the integration worker turns it into a `KiongaPipelineRun`, and the
  operator submits that run to KFP.

## Model promotion and serving

Promotion changes the model's stage; deployment starts a live endpoint. Locally the
serving manager runs containers on the Docker host. On Kubernetes, promotion also
drives MLflow and KServe through the operator.

```mermaid
sequenceDiagram
    autonumber
    actor U as Console or SDK
    participant G as Gateway
    participant P as PostgreSQL
    participant K as Kafka
    participant W as Integration worker (Kubernetes)
    participant O as Operator (Kubernetes)
    participant S as Serving manager (Compose)
    participant C as mlflow models serve container
    U->>G: POST /api/v1/models/{id}/promote {stage}
    G->>P: Model + audit + outbox (model.promoted)
    G-->>U: 200 OK (model)
    G->>K: Publish mlaiops.model.commands
    K->>W: Poll batch (auto-commit off)
    W->>O: Create or update KiongaModelPromotion
    O->>O: MLflow stage transition, then create KServe InferenceService
    W->>K: Commit offsets after the whole batch succeeds
    U->>G: POST /api/v1/models/{id}/deploy
    G->>P: Model + audit + outbox (model.deployed)
    G->>S: POST /deployments {name, artifact_uri, serving_image}
    S->>C: Replace container, create and start (no capabilities,<br/>no-new-privileges, PID limit)
    S-->>G: Endpoint URL
    G->>P: Record endpoint, status serving
    G-->>U: 202 Accepted (model)
    U->>G: POST /api/v1/models/{id}/predict
    G->>C: POST /invocations
    C-->>G: Predictions
    G-->>U: Predictions
```

Failure behavior: if the serving manager rejects the deployment or is unreachable, the
gateway records status `failed` and returns `502 serving_failed`. A prediction for a
model without a live endpoint returns `409 not_serving`. Rollback removes the serving
container on a best-effort basis and logs a failed removal.

## Agent turn with trace capture

The gateway proxies a turn to the agent runtime after a readiness gate. The runtime
calls the model through the trace proxy and reports the session back.

```mermaid
sequenceDiagram
    autonumber
    actor U as Console or SDK
    participant G as Gateway
    participant A as Agent runtime
    participant DB as PostgreSQL
    participant T as Trace proxy
    participant L as LLM provider
    participant K as Kafka (via REST proxy)
    participant LF as Langfuse
    U->>G: POST /api/v1/agents/{id}/invoke {message, session_id}
    G->>G: RBAC and project scope (404 if not visible)
    G->>A: GET /healthz (3 seconds)
    alt Runtime not healthy
        G-->>U: 503 agent_not_ready
    else Healthy
        G->>A: POST /invoke with X-MLAIOps-Agent-ID,<br/>X-MLAIOps-Agent-Name, X-MLAIOps-Graph-Module
        A->>DB: Load the session checkpoint
        A->>T: Chat completion (OpenAI-compatible)
        T->>L: Forward to LLM_UPSTREAM_URL
        L-->>T: Completion with usage
        T-->>A: Completion
        T--)K: Trace event to mlaiops.llm.traces (asynchronous)
        A--)LF: LangChain callback trace (when keys are set)
        A->>DB: Save the checkpoint
        A-->>G: Reply, tokens, cost, duration
        G-->>U: Reply
        A--)G: POST /api/v1/traces (background task, service token)
        G->>DB: Upsert session and trace
    end
```

What to know:

- The runtime endpoint is `AGENT_RUNTIME_URL` in Compose (one shared runtime). On
  Kubernetes it is the per-agent Service named from the immutable agent ID in
  `MLAIOPS_AGENT_NAMESPACE`.
- Token counts come from the model's usage metadata, never from an estimate. Cost is
  computed from `MLAIOPS_COST_PER_1K_INPUT` and `MLAIOPS_COST_PER_1K_OUTPUT`.
- The trace proxy's event carries the agent, version, session ID, HTTP status and
  duration, not the prompt or the provider key. It is sent from a `goroutine` after the
  response, and a failed send is dropped.
- The `anthropic` backend calls Anthropic directly and does not pass through the trace
  proxy. The default `mock` backend makes no network call.
- Session reporting is best effort: `record_trace` in the SDK uses a two-second
  timeout and ignores HTTP errors, so observability never fails a turn.
