---
icon: material/graph-outline
description: Launch a project-scoped Langflow canvas alongside Kionga's native agent designer.
---

# Build flows with Langflow

Open a Langflow canvas in a project-scoped workspace, build a flow with Kionga resources, capture it as a versioned snapshot, and publish it as a managed agent. Kionga offers two agent-building entry points: **Agent designer** for Kionga's native versioned graph drafts, and **Langflow** for a full Langflow canvas. Langflow workspaces keep their own flows and files. They do not change the native designer's drafts.

## Before you begin

- You need the `langflow` service, project access, and workspace capacity. Ask an administrator for them. Operators and administrators can manage workspaces without a user grant.
- To publish a flow as a managed agent, you also need the `agents` service, and the install must run on Kubernetes.
- To register datasets, knowledge bases, object storage, or external agent APIs, you need the `admin` or `operator` role.

## Open a workspace

1. In the sidebar, open **Langflow** under **Models and data**, or select **Langflow canvas** in the links below the navigation.
2. On Kubernetes, select **Create workspace**. In the **Create Langflow workspace** dialog, enter a **Name**, choose a **Project**, and set **CPU**, **Memory (GB)**, and **Storage (GB)**, then select **Create workspace**. Each instance has its own persistent volume. You can create several within your assigned `max_vms` limit.
3. When the instance's **State** is `ready`, select **Open canvas** in its row. Kionga signs you in through the workspace session.
4. To manage the instance, use **Stop**, **Start**, **Restart**, or **Delete** in its row. **Delete** asks you to confirm and removes the persistent volume and saved flows. Viewers do not see these buttons.

A stopped workspace does not erase its volume. Restarting replaces its pod. The console's project selector filters the workspace list.

## Use Kionga resources in a flow

The Kionga Langflow image includes a **Kionga** component category:

- **Kionga Models** lists models assigned to the workspace project.
- **Kionga Model Inference** lists deployed model IDs when you toggle **Refresh Kionga models**, then invokes the selected model.
- **Kionga Function** invokes an authorized Kionga function.
- **Kionga Storage** lists authorized object storage buckets.
- **Kionga Objects** browses dataset and artifact keys within an authorized bucket.
- **Kionga Object Text** reads a bounded text preview from an authorized object.
- **Kionga Datasets** lists named project datasets in authorized storage buckets.
- **Kionga Dataset Objects** browses a selected dataset prefix; **Kionga Dataset Text** reads a bounded text preview from that prefix.
- **Kionga Registered Storage** lists existing S3-compatible connections assigned to one of your projects. **Kionga Registered Objects** browses their keys; **Kionga Registered Object Text** reads a bounded preview.
- **Kionga Feature Views** lists available feature view metadata.
- **Kionga Tools** lists registered tool schemas. Registered tools are catalog entries; invoke a function through **Kionga Function**.
- **Kionga Knowledge Bases** lists Qdrant and pgvector bases assigned to the project.
- **Kionga Knowledge Search** searches a selected base using a JSON embedding from the same embedding model used to index it.
- **Kionga Knowledge Chunk** stores text with a matching JSON embedding in an authorized base.
- **Kionga API Connections** lists administrator-approved external API operations for the project.
- **Kionga API Invoke** sends a JSON body to one approved operation. Kionga adds the server-side bearer credential.
- **Kionga Chat API** sends messages to an approved OpenAI-compatible chat-completions operation and returns its text. The selected provider model ID and connection ID are saved in the flow; the API key stays on the gateway.

The components call a loopback helper in the same workspace pod. The helper holds the revocable workspace API credential and forwards requests through Kionga's existing authorization checks. A flow contains resource IDs and inputs, not the helper credential. A model must have an active endpoint before inference works; a function needs an active OpenFaaS deployment.

An administrator can select **Register** in the **Project datasets** section of the **Langflow** page. The form takes a **Project**, **Name**, **Bucket**, **Object prefix**, and **Description**. The API equivalent is `POST /api/v1/admin/datasets`. Kionga lists a dataset only when the user has both project access and a grant for its bucket. Browsing appends a relative prefix, and object previews cannot read a key outside the registered prefix. The gateway uses the existing storage proxy; credentials never enter the Langflow flow.

The **Registered storage** section of the **Langflow** page lists the object storage connections that a project can use. An administrator or operator selects **Register storage** to open the **Connect object storage** dialog, the same dialog that **Add object storage** opens under **Platform > Object storage connections**, and **Save and test** saves the connection and checks it. The dialog fills in **Allowed project IDs** with the project you selected in the console. A connection is visible only to the projects listed in **Allowed project IDs**, which is `allowed_projects` in the API, and an empty list makes it visible to no project. To change a connection later, select **Edit** in its row under **Platform > Object storage connections**; the **Secret reference** field shows the stored `env:VARIABLE` reference, and credentials are never returned. The Langflow components call `GET /api/v1/registered-storage` and its object routes through the gateway; the response contains source IDs, names, and buckets, never endpoints or secret references. The gateway resolves the source credential for each request, signs S3 reads, and caps text previews at 64 KiB. This also supports external S3-compatible data sources without entering credentials in a flow. For the fields, see [Connect external object storage](../operations/external-storage.md).

!!! info "Available in a later release"
    In platform v0.2.1 and earlier, the **Registered storage** section is read-only and the console cannot edit a saved connection. Register a connection with **Add object storage** under **Platform > Object storage connections**. To change one, call `PUT /api/v1/admin/storage-connections/{id}`.

## Capture a flow

Langflow's canvas supports building and testing flows. Its flow database and configuration are stored on the workspace volume.

1. Save the flow in the Langflow canvas.
2. Return to the **Langflow** page in Kionga and select **Capture flow** in the row of the workspace. If the workspace has no saved flow, the console shows `Save a flow in the Langflow canvas before capturing it.`
3. In the **Capture saved flow** dialog, choose the **Saved flow** and the **Project**, leave **Snapshot** on **New snapshot**, and select **Save snapshot revision**. Kionga stores a versioned snapshot, lists it under **Flow snapshots**, and rejects exports that contain embedded credentials.
4. To save a new revision later, capture the same flow again and choose the existing snapshot in **Snapshot**. Kionga retains the current revision and up to 20 earlier revisions.

## Publish a flow as a managed agent

On Kubernetes, a user with both `langflow` and `agents` access can publish a snapshot.

1. In **Flow snapshots**, select **Publish** in the snapshot's row. The button appears only for snapshots you own, and only if you can write agents.
2. In the **Publish flow snapshot** dialog, choose the **Revision** (the current or a retained earlier one) and set **Minimum replicas**, **Maximum replicas**, **CPU**, and **Memory**, then select **Publish**. Kionga creates a managed agent with an independent flow artifact, API endpoint, autoscaler, and project-scoped resource sidecar.
3. Open **Agents** to check status, invoke the agent, and inspect sessions and usage.
4. When the deployment is ready, select **Activate revision N** next to it in the **Deployments** column of **Flow snapshots**, where N is its revision number. This assigns the stable authenticated path `POST /api/v1/langflow-snapshots/{snapshot-id}/invoke` to that deployment.
5. To roll back, select **Roll back to revision N** next to a ready older deployment. The same path switches to it. The **Stable API** column shows the path, or `Not activated`.

Publishing an earlier revision creates a separate deployment, and activation never sends traffic to an unready runtime. Publish is unavailable in local Compose because that profile has only a shared agent runtime.

The managed image executes the exported JSON with LFX 1.13.x and pinned OpenAI, OpenAI-compatible, Anthropic, and Ollama extensions. Other provider bundles require an extended runtime image before publishing. Kionga resource components use a separate, revocable agent identity to reach the internal gateway; flow JSON must not contain raw credentials. The current capture validator checks common credential fields, so review custom components before publishing.

## Monitor a published flow

Kionga records execution summaries and LFX component durations through its agent tracing path. Open **Agents** and read the **Recent traces** table to inspect status, duration, tokens, and **Component timing**. The console shows `Unavailable` for tokens when the LFX result does not provide usage metadata. Component timing traces contain names and durations, not flow inputs or outputs. On Kubernetes, the **Resource usage** column of the agent list shows live CPU, memory, and pod count for the runtime containers when metrics-server is available, and `Unavailable` otherwise. For an agent that requests at least one GPU, the column also shows `GPU` and a percentage when the gateway has a GPU sample, and `GPU utilization unavailable` when it has none. Agents that request no GPU show no GPU text. The gateway reports a sample through the agent metrics API when it has a Prometheus GPU telemetry source.

To report GPU utilization:

1. Deploy a DCGM exporter scraped by Prometheus with `namespace` and `pod` labels.
2. Set the gateway's `KIONGA_GPU_METRICS_URL` to that Prometheus base URL. The gateway queries `DCGM_FI_DEV_GPU_UTIL` for pods owned by the agent and reports the average percentage across their GPUs.
3. If your exporter uses another Prometheus metric name with the same 0–100 percentage meaning, set `KIONGA_GPU_METRIC_NAME`.
4. Read the value with `GET /api/v1/agents/{id}/metrics`. The response has `gpu_utilization_available` and `gpu_utilization_percent`.

Keep the Prometheus endpoint on a trusted internal network. When it is absent or has no samples, `gpu_utilization_available` is `false` instead of reporting zero. The gateway reports a sample only when `KIONGA_GPU_METRICS_URL` is set and Prometheus returns exactly one valid sample for the agent's pods, a percentage from 0 to 100.

!!! info "Available in a later release"
    In platform v0.2.1 and earlier, the **Resource usage** column does not show GPU utilization. Read it with `GET /api/v1/agents/{id}/metrics`.

## Configure project knowledge bases

An administrator can register a Qdrant or pgvector backend for a project with **Register** in the **Knowledge bases** section of the **Langflow** page, or through `POST /api/v1/admin/knowledge-bases`. The form has a **Project** selector, a **Backend** selector (**Qdrant** or **PostgreSQL pgvector**) and the fields **Name**, **Dimensions**, **Qdrant endpoint**, **Qdrant secret reference**, and **PostgreSQL DSN reference**. Set the credential on the **gateway** first. Kionga stores only an `env:VARIABLE` reference and keeps the endpoint and credential out of the project-facing catalog and flow JSON. Use a separate Qdrant API key or PostgreSQL role with the minimum access needed for each deployment.

Use a variable named `KIONGA_KB_SECRET_<NAME>`, or the existing `KIONGA_QDRANT_KEY` or `KIONGA_KNOWLEDGE_DSN`. Kionga refuses any other name with a 422 unless an operator allowlists it. To supply the value, see [Secret references](../reference/configuration.md#secret-references). To fix a saved record that uses another name, see [Migrate a stored reference](../operations/production-operations.md#migrate-a-stored-reference). The Langflow editor and agent runtime do not need the backend credentials.

### Register a Qdrant base

1. Set `KIONGA_QDRANT_KEY` on the gateway.
2. Register the base:

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

For an intentionally unauthenticated local Qdrant instance, set `secret_ref` to `none`. Production Qdrant should use an API key.

### Register a pgvector base

1. Enable PostgreSQL's `vector` extension in the target database.
2. Grant the gateway's database role permission to create and use the `kionga_knowledge_chunks` table.
3. Set `KIONGA_KNOWLEDGE_DSN` on the gateway.
4. Register the base:

    ```json
    {
      "project_id": "prj-example",
      "name": "support-docs",
      "backend": "pgvector",
      "dimensions": 1536,
      "dsn_ref": "env:KIONGA_KNOWLEDGE_DSN"
    }
    ```

### Use a base in a flow

1. Check that the `dimensions` value matches your embedding model.
2. In Langflow, refresh **Kionga Knowledge Search** and select the base ID.
3. Pass a JSON array of numbers in **Embedding JSON**. **Kionga Knowledge Chunk** accepts the same array with text to index.

The gateway checks the caller's current project grant on every list, write, and search, limits text and metadata size, and returns only the authorized base's matches. This integration uses Kionga's gateway API; Langflow's built-in Qdrant and pgvector components remain available for separately managed connections, but their own credential fields are not suitable for Kionga flow publishing.

## Register an external agent API

An administrator can assign a fixed HTTPS POST operation to a project.

1. Set the credential variable on the gateway before you invoke the operation.
2. In the **Approved API connections** section of the **Langflow** page, select **Register**. The form accepts a **Project**, **Name**, **Endpoint** (the full operation URL), **Secret reference**, and **Description**. Use a credential reference such as `env:KIONGA_CONNECTION_SECRET_SUPPORT` or `env:KIONGA_AGENT_API_TOKEN`; use `none` for an unauthenticated service. The API equivalent is `POST /api/v1/admin/agent-api-connections`:

    ```json
    {
      "project_id": "prj-example",
      "name": "support-lookup",
      "description": "Look up a support case",
      "endpoint": "https://api.example.com/cases/lookup",
      "secret_ref": "env:KIONGA_AGENT_API_TOKEN"
    }
    ```

3. In the canvas, use **Kionga API Connections** to list the connection.

The canvas lists the connection ID and description, never its URL or secret reference. **Kionga API Invoke** accepts a JSON body and calls only the registered URL. The gateway checks project membership on every call, sends the configured bearer token, blocks redirects, and limits request and response size. Configure narrowly scoped upstream credentials: anyone granted this project and Langflow access can call the approved operation.

To call an OpenAI-compatible language model:

1. Register its full chat-completions URL (for example, `https://api.example.com/v1/chat/completions`) as the operation.
2. In **Kionga Chat API**, refresh the approved connections and select that connection ID.
3. Enter the provider's model ID.

This also works with a self-hosted OpenAI-compatible inference server reachable from the gateway. Kionga sends the system and user messages through the approved connection and returns the first text completion. The registered endpoint controls which provider is called; changing the model ID does not change the destination.

## Run Langflow on local Compose

On macOS, Linux, or Windows with WSL 2, use the configured Docker or Podman Compose engine.

1. Start Langflow:

    ```bash
    cd deploy
    make langflow-up
    # Later: make langflow-down
    ```

    The target uses whichever engine you selected for the rest of Kionga (`KIONGA_ENGINE=podman` for Podman; Docker is the default).

2. Open `http://localhost:8080/console/langflow`.

Local Compose provides one optional Langflow instance for the local administrator. Hosted multi-instance provisioning requires Kubernetes. Local Compose stores flows in `langflow-data`; keep that volume when recreating containers. The Langflow image is pinned to 1.13.0 in `workspace/langflow/Dockerfile` and should be upgraded with a database backup.

## Set up Langflow on Kubernetes

1. Build and publish `workspace/langflow/Dockerfile`, `workspace/langflow/Dockerfile.sidecar`, and the Langflow flavor of `agent-runtime/Dockerfile` (`RUNTIME_FLAVOR=langflow`).
2. Set `images.langflow`, `images.langflow-sidecar`, and `images.langflow-agent-runtime` in Helm values to immutable image references.
3. Install the updated KiongaWorkspace and KiongaAgent CRDs and chart. The gateway service account needs create, update, and delete access to KiongaWorkspace resources.
4. Configure an isolated workspace base domain and wildcard TLS as described in [Kubernetes workspace access](../operations/managed-kubernetes.md#how-workspace-access-works).

The operator creates one Deployment, Service, Secret, and persistent volume claim per Langflow instance. Langflow has readiness, liveness, and startup probes. The workload namespace's network policy allows ingress from Kionga's control namespace and limits egress; permit only the external model or data endpoints your flows require. Langflow runs user-authored flow code, so grant the service to trusted users and apply the same workload isolation controls used for code workspaces.

Kionga enables Langflow's API auto-login mode so its gateway can capture saved flows. Keep the Langflow service private to the Compose network or Kubernetes workload namespace and expose it to users only through Kionga's authenticated workspace route.

## Verify

1. **Workspace:** on Kubernetes, `GET /api/v1/langflow-workspaces` returns `"mode": "kubernetes"` and your instance in `items` with `"ready": true`, and the row of the workspace offers **Open canvas**. On local Compose, the call returns `"mode": "local"` and, for the local administrator, one item named `Local Langflow` with the state `configured`.
2. **Capture:** the snapshot appears in `GET /api/v1/langflow-snapshots`, and its revision number grows each time you capture the same flow again.
3. **Publish:** the new deployment appears under **Agents**. After you select **Activate revision N**, `POST /api/v1/langflow-snapshots/{snapshot-id}/invoke` returns the agent's reply.
4. **Compose:** after `make langflow-up`, `http://localhost:8080/console/langflow` loads the Langflow page.
5. **Kubernetes setup:** for each instance, the workload namespace holds one Deployment, Service, Secret, and persistent volume claim.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `503 workspace_unavailable`, `Kubernetes workspace provisioning is not configured` or `Kubernetes workspace discovery is unavailable` | The gateway cannot reach the Kubernetes workspace resources. | Check the install steps in [Set up Langflow on Kubernetes](#set-up-langflow-on-kubernetes), including the gateway service account access. |
| `403 access_denied`, `Project is not assigned to this user` | You do not have access to the project. | Ask an administrator to assign the project. |
| `403 resource_not_provisioned`, `Workspace exceeds your assigned capacity` | The workspace needs more than your grant, or you reached your `max_vms` limit. | Choose smaller CPU, memory or storage, delete an instance, or ask for more capacity. |
| `422 validation_error`, `Workspace name must contain 1–80 characters` or `Workspace resources are outside the supported range` | The name or the resource sizes are invalid. | Correct the name or resources. |
| `409 workspace_stopped`, `Start the workspace before opening it` | The instance is stopped. | Select **Start**, then **Open canvas**. |
| `409 workspace_conflict`, `Workspace could not be updated; retry` | Another change updated the instance at the same time. | Retry. |
| `502 langflow_unavailable` when you list or capture flows | The Langflow instance did not answer. | Make sure the instance is ready, then try again. |
| `422 validation_error`, `flow export contains an embedded credential; use managed connections or variables` | The saved flow holds a credential field such as a password, API key or token. | Remove the credential from the flow and use a Kionga component or a variable. |
| `409 revision_conflict`, `Snapshot changed elsewhere; reload before saving` | Another session saved the snapshot. | Reload the snapshot, then capture again. |
| `503 managed_runtime_unavailable`, `Publishing Langflow flows requires a Kubernetes managed agent runtime` | You are on local Compose. | Publish from a Kubernetes install. |
| `503 managed_runtime_unavailable`, `KIONGA_LANGFLOW_AGENT_IMAGE is not configured` | The gateway has no managed Langflow runtime image. | Set `images.langflow-agent-runtime` in the Helm values. |
| `422 validation_error`, `flow exceeds the 512 KiB managed deployment limit` | The flow JSON is larger than 512 KiB. | Split the flow or remove unused components. |
| `403 access_denied`, `Agent deployment service is not assigned` | You have `langflow` but not `agents`. | Ask an administrator for the `agents` service. |
| `503 agent_not_ready`, `Wait for this deployment to pass its runtime health check` | You activated a deployment that is not ready. | Wait until the deployment is ready, then activate it. |
| `503 deployment_inactive`, `Activate a ready deployment before invoking this flow` | No deployment is active for the snapshot. | Select **Activate revision N** on a ready deployment. |
| `422 invalid_request`, `Qdrant requires an HTTP(S) endpoint and none or a permitted env: API-key reference (KIONGA_KB_SECRET_*)` (or the pgvector equivalent) | The secret reference uses a name that the gateway does not permit. | Use `KIONGA_KB_SECRET_<NAME>`, `KIONGA_QDRANT_KEY` or `KIONGA_KNOWLEDGE_DSN`. See [Secret references](../reference/configuration.md#secret-references). |

## Related pages

- [Build agents in the Agent Designer](agent-designer.md).
- [Build and deploy an agent](agents.md).
- [Set up managed Kubernetes workspaces](../operations/managed-kubernetes.md#how-workspace-access-works).
- [Secret references](../reference/configuration.md#secret-references).
