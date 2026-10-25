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
- **Kionga Tools** lists registered tool schemas. Registered tools are catalog entries; invoke a function through **Kionga Function**.

The components call a loopback helper in the same workspace pod. The helper holds the revocable workspace API credential and forwards requests through Kionga's existing authorization checks. A flow contains resource IDs and inputs, not the helper credential. A model must have an active endpoint before inference works; a function needs an active OpenFaaS deployment.

Langflow's own canvas supports building and testing flows. Its flow database and configuration are stored on the workspace volume. Publishing a Langflow flow as a Kionga agent, running it independently of the workspace, and mapping its execution telemetry into Kionga are still being developed under [workspace issue #39](https://github.com/kiongahq/workspace/issues/39). Until those are available, use [Kionga agent deployment](agents.md) for managed runtime endpoints, scaling, and rollback.

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

Build and publish `workspace/langflow/Dockerfile` and `workspace/langflow/Dockerfile.sidecar`. Set `images.langflow` and `images.langflow-sidecar` in your Helm values to those images. Install the updated KiongaWorkspace CRD and chart; the gateway service account needs create, update, and delete access to KiongaWorkspace resources. Configure an isolated workspace base domain and wildcard TLS as described in [Kubernetes workspace access](../operations/managed-kubernetes.md#how-workspace-access-works).

The operator creates one Deployment, Service, Secret, and persistent volume claim per Langflow instance. Langflow has readiness, liveness, and startup probes. The workload namespace's network policy allows ingress from Kionga's control namespace and limits egress; permit only the external model or data endpoints your flows require. Langflow runs user-authored flow code, so grant the service to trusted users and apply the same workload isolation controls used for code workspaces.
