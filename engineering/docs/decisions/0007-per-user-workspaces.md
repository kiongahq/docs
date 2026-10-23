---
description: Give each provisioned user an isolated workspace reconciled from their access grant on Kubernetes, and keep one shared workbench in the single-host Compose stack.
status: "accepted"
date: 2026-07-20
---

# 0007 Per-user workspaces on Kubernetes, a shared workbench in Compose

## Context and problem statement

Workspaces run user code: notebooks, terminals, coding agents, scaffolding jobs. In a
team installation one user's code must not read another user's files, credentials or
compute, and revoking a grant must stop the workspace. On a single developer machine
the same isolation would cost resources and add nothing. How should Kionga provision
workspaces?

## Decision drivers

- Isolation between users where several users share an installation.
- Workspace lifecycle driven by the administrator's grant: create, resize, suspend,
  revoke.
- Bounded compute and storage per user.
- Separate browser origins so one workspace cannot use another user's cookies.
- A simple single-user experience in Compose.

## Considered options

- One `KiongaWorkspace` per access grant on Kubernetes, a shared workbench in Compose
- A shared workbench everywhere
- Per-user containers on the Docker host

## Decision outcome

Chosen option: **One `KiongaWorkspace` per access grant on Kubernetes, a shared
workbench in Compose**, because isolation is enforced where several users exist and
the single-user stack stays simple.

A change to a user's access writes a command to `mlaiops.workspace.commands` through
the outbox. The integration worker creates or updates the `KiongaWorkspace` (and
deletes it when access is deleted). The `WorkspaceReconciler` in
`platform/go/internal/operator/workspace_controller.go` turns it into one Deployment
with Jupyter and the IDE sharing a PVC, a Service, and a credentials Secret, with the
granted CPU, memory and GPU split between the containers. A suspended grant scales the
pod to zero.

### Consequences

- Good, because each workspace has its own PVC, credentials and resource limits, runs
  as non-root with the runtime-default `seccomp` profile, and lives in a namespace with a
  ResourceQuota and default-deny network policies.
- Good, because revocation is part of reconciliation, not a manual step.
- Good, because with `KIONGA_WORKSPACE_BASE_DOMAIN` each workspace gets its own host;
  production startup checks require that domain to be distinct from the console host
  and to share its registrable site.
- Good, because tenant storage admission rejects `hostPath` and limits StorageClasses
  (`WORKSPACE_ALLOWED_STORAGE_CLASSES`).
- Bad, because isolation requires Kubernetes. Compose shares one `jupyter-data`
  volume between the workbench and the IDE, and is not a multi-user boundary.
- Bad, because a workspace volume is `ReadWriteOnce`; on zonal block storage it is tied
  to one availability zone.

### Confirmation

`platform/go/internal/operator/workspace_controller_test.go` and
`platform/go/internal/operator/storage_admission_test.go` cover reconciliation and
storage admission; `TestProductionWorkspaceDomains` covers the domain rules;
`deploy/scripts/e2e-kind.sh` exercises workspaces on a kind cluster.

## Pros and cons of the options

### Per-grant `KiongaWorkspace` on Kubernetes

- Good, because Kubernetes provides the isolation primitives (namespaces, quotas,
  network policies, PVCs).
- Bad, because it needs a cluster, an Ingress with wildcard TLS, and storage classes.

### Shared workbench everywhere

- Good, because it is the simplest setup.
- Bad, because users would share files and credentials.

### Per-user containers on the Docker host

- Bad, because provisioning them would need the Docker socket, which is
  root-equivalent on the host, so the isolation would be weaker than the trust it
  needs.

## More information

Written after the fact. Evidence: `platform` commit `f82e768` (2026-07-20) added the
workspace reconciler; the CRD is `deploy/config/crd/mlaiops.io_kiongaworkspaces.yaml`;
the dispatcher mapping is in `platform/go/internal/integrations/dispatcher.go`. The
per-user Docker container option is not recorded in the history; it is listed because
the Compose stack's Docker socket boundary
([risk R1](../architecture/11-risks-and-technical-debt.md#risks)) rules it out.
