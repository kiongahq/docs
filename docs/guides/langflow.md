---
icon: material/graph-outline
description: Launch a project-scoped Langflow canvas alongside Kionga's native agent designer.
---

# Build flows with Langflow

Kionga offers two agent-building entry points: **Agent designer** for Kionga's native versioned graph drafts, and **Langflow** for a full Langflow canvas. Langflow workspaces keep their own flows and files. They do not change the native designer's drafts.

## Open a workspace

1. Ask an administrator for the `langflow` service, project access, and workspace capacity. Operators and administrators can manage workspaces without a user grant.
2. Open **Agents > Langflow canvas** or choose **Langflow** in the navigation.
3. On Kubernetes, choose a project, name, CPU, memory, and storage allocation, then select **Create workspace**. Each instance has its own persistent volume. You can create several within your assigned `max_vms` limit.
4. When the instance is ready, select **Open canvas**. Kionga signs you in through the workspace session. Use **Stop**, **Start**, **Restart**, or **Delete** on the instance card. Deleting removes its persistent volume and saved flows.

A stopped workspace does not erase its volume. Restarting replaces its pod. The console's project selector filters the instance list.

## Use Kionga resources in a flow

The Kionga Langflow image includes a **Kionga** component category:

- **Kionga Models** lists models assigned to the workspace project.
- **Kionga Model Inference** lists deployed model IDs when you toggle **Refresh Kionga models**, then invokes the selected model.
- **Kionga Function** invokes an authorized Kionga function.
- **Kionga Storage** lists authorized object storage buckets.
- **Kionga Objects** browses dataset and artifact keys within an authorized bucket.
- **Kionga Object Text** reads a bounded text preview from an authorized object.
- **Kionga Feature Views** lists available feature view metadata.
- **Kionga Tools** lists registered tool schemas. Registered tools are catalog entries; invoke a function through **Kionga Function**.
- **Kionga Knowledge Bases** lists Qdrant and pgvector bases assigned to the project.
- **Kionga Knowledge Search** searches a selected base using a JSON embedding from the same embedding model used to index it.
- **Kionga Knowledge Chunk** stores text with a matching JSON embedding in an authorized base.

The components call a loopback helper in the same workspace pod. The helper holds the revocable workspace API credential and forwards requests through Kionga's existing authorization checks. A flow contains resource IDs and inputs, not the helper credential. A model must have an active endpoint before inference works; a function needs an active OpenFaaS deployment.

Langflow's canvas supports building and testing flows. Its flow database and configuration are stored on the workspace volume. After saving a flow, return to **Langflow** in Kionga and select **Capture flow**. Choose the saved flow and a project; Kionga stores a versioned snapshot and rejects exports that contain embedded credentials. Select an existing snapshot to save a new revision. Kionga retains the current revision and up to 20 earlier revisions.

On Kubernetes, a user with both `langflow` and `agents` access can select **Publish** on a snapshot, choose its current or retained earlier revision, and set CPU, memory, and replica limits. Kionga creates a managed agent with an independent flow artifact, API endpoint, autoscaler, and project-scoped resource sidecar. Open **Agents** to check status, invoke it, and inspect sessions and usage. Publishing an earlier revision creates a new deployment and endpoint; it does not replace the current deployment in place. Publish is unavailable in local Compose because that profile has only a shared agent runtime.

The managed image executes the exported JSON with LFX 1.13.x and pinned OpenAI, OpenAI-compatible, Anthropic, and Ollama extensions. Other provider bundles require an extended runtime image before publishing. Kionga resource components use a separate, revocable agent identity to reach the internal gateway; flow JSON must not contain raw credentials. The current capture validator checks common credential fields, so review custom components before publishing. Kionga records execution summaries through its agent tracing path; token counts are shown as unavailable when the LFX result does not provide usage metadata.

## Configure project knowledge bases

An administrator can register a Qdrant or pgvector backend for a project through `POST /api/v1/admin/knowledge-bases`. Set the credential on the **gateway** first. Kionga stores only an `env:VARIABLE` reference and keeps the endpoint and credential out of the project-facing catalog and flow JSON. Use a separate Qdrant API key or PostgreSQL role with the minimum access needed for each deployment.

For Qdrant, set `KIONGA_QDRANT_KEY` on the gateway and register:

```json
{
  "project_id": "prj-example",
  "name": "support-docs",
  "backend": "qdrant",
  "dimensions": 1536,
  "endpoint": "http://qdrant:6333",
  "secret_ref": "env:KIONGA_QDRANT_KEY"
}
```

For pgvector, enable PostgreSQL's `vector` extension in the target database, grant the gateway's database role permission to create and use the `kionga_knowledge_chunks` table, set `KIONGA_KNOWLEDGE_DSN` on the gateway, and register:

```json
{
  "project_id": "prj-example",
  "name": "support-docs",
  "backend": "pgvector",
  "dimensions": 1536,
  "dsn_ref": "env:KIONGA_KNOWLEDGE_DSN"
}
```

The `dimensions` value must match your embedding model. In Langflow, refresh **Kionga Knowledge Search**, select the base ID, and pass a JSON array of numbers in **Embedding JSON**. **Kionga Knowledge Chunk** accepts the same array with text to index. The gateway checks the caller's current project grant on every list, write, and search, limits text and metadata size, and returns only the authorized base's matches. This integration uses Kionga's gateway API; Langflow's built-in Qdrant and pgvector components remain available for separately managed connections, but their own credential fields are not suitable for Kionga flow publishing.

## Local Compose

On macOS, Linux, or Windows with WSL 2, use the configured Docker or Podman Compose engine:

```bash
cd deploy
make langflow-up
# Later: make langflow-down
```

The target uses whichever engine you selected for the rest of Kionga (`KIONGA_ENGINE=podman` for Podman; Docker is the default).

Open `http://localhost:8080/console.html?view=langflow`. Local Compose provides one optional Langflow instance for the local administrator. Hosted multi-instance provisioning requires Kubernetes. Local Compose stores flows in `langflow-data`; keep that volume when recreating containers. The Langflow image is pinned to 1.13.0 in `workspace/langflow/Dockerfile` and should be upgraded with a database backup.

## Kubernetes setup

Build and publish `workspace/langflow/Dockerfile`, `workspace/langflow/Dockerfile.sidecar`, and the Langflow flavor of `agent-runtime/Dockerfile` (`RUNTIME_FLAVOR=langflow`). Set `images.langflow`, `images.langflow-sidecar`, and `images.langflow-agent-runtime` in Helm values to immutable image references. Install the updated KiongaWorkspace and KiongaAgent CRDs and chart; the gateway service account needs create, update, and delete access to KiongaWorkspace resources. Configure an isolated workspace base domain and wildcard TLS as described in [Kubernetes workspace access](../operations/managed-kubernetes.md#how-workspace-access-works).

The operator creates one Deployment, Service, Secret, and persistent volume claim per Langflow instance. Langflow has readiness, liveness, and startup probes. The workload namespace's network policy allows ingress from Kionga's control namespace and limits egress; permit only the external model or data endpoints your flows require. Langflow runs user-authored flow code, so grant the service to trusted users and apply the same workload isolation controls used for code workspaces.

Kionga enables Langflow's API auto-login mode so its gateway can capture saved flows. Keep the Langflow service private to the Compose network or Kubernetes workload namespace and expose it to users only through Kionga's authenticated workspace route.
