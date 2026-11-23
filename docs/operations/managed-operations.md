---
icon: material/account-wrench-outline
description: How the Enterprise plan works, where Kionga's team installs and operates Kionga inside your own cloud with the same Helm chart, what access you grant, and how upgrades, backups and support work.
---

# Managed operations

Managed operations is part of the Enterprise plan. Kionga's team installs and
operates Kionga **inside your own cloud**, in your cluster and your account, with
the same Helm chart that anyone can install. You get the platform without staffing
its upgrades, backups and on-call. Your data never leaves your account.

If you run Kionga yourself, nothing on this page applies, and you can skip it.
For the self-managed install, see [Deploy on Kubernetes](managed-kubernetes.md).

!!! info "Available in a later release"
    The access grant (`operations.access`) and the support bundle script are
    part of the chart changes that come after deploy v0.2.0. This page describes
    them as designed. Check the [release notes](../changelog.md) for the release
    that includes them before you rely on them. Prices, service levels,
    response times, certifications and contract terms are not part of this
    documentation. They are agreed in the contract.

## What stays with you and what Kionga runs

| | You | Kionga's team |
| --- | --- | --- |
| Cloud account and cluster | Own and pay for them. Create the cluster, or approve one | Installs into it |
| Data | Stored in your databases, object storage and secret manager, in your account | Operates the services that use them. Does not copy data out |
| Network, DNS and TLS | Provide the domain, the wildcard DNS record and certificate rules | Configures Kionga's side |
| Identity | Run your identity provider and decide who is in `subjects` | Signs in only through the identities you list |
| Install and configuration | Approve changes | Installs the chart and keeps its values current |
| Upgrades | Approve the window | Plans and applies them, and rolls back if needed |
| Backup and restore | Own the backup storage | Runs the backups and the restore |
| On-call | Reach the team through the agreed channel | Responds to incidents as the contract says |

## Same chart, your cluster

Managed installs use the [Kubernetes chart](managed-kubernetes.md) and the
[prerequisites](kubernetes-prerequisites.md). There is no separate managed build,
so you can leave the managed plan and keep running the same install yourself.
Anything the team does is a Helm release and Kubernetes objects that you can read.

## Grant access

Kionga's team needs access to your cluster to operate it. You grant it with one
chart value, `operations.access`. It is off by default, scoped, and easy to audit.

```yaml
operations:
  access:
    enabled: true
    subjects:
      - {kind: Group, name: kionga-operations}
    serviceAccount: {create: true, name: kionga-operations}
    allowSecretRead: false
```

- **Who.** `subjects` lists identities from your identity provider, as Kubernetes
  `User` or `Group` entries. The chart can also create a service account.
- **Where.** The grant covers only Kionga's namespaces: the release namespace and
  the workload namespace, and the pipeline, sandbox and build namespaces when you
  use them. A small read-only cluster role covers cluster-wide facts, such as
  nodes, storage classes and the resource definitions Kionga uses.
- **What it allows.** Read Kionga's objects, logs and events, and restart or roll
  out Kionga Deployments. The team can scale a Deployment and delete a pod so its
  controller replaces it.
- **What it never allows.** The grant has no Secret access unless you set
  `allowSecretRead: true`. It never allows `exec`, `attach`, `port-forward`,
  impersonation or RBAC changes.
- **Audit.** Every object of the grant carries the label
  `kionga.dev/access=operations`, so one command lists everything granted:

    ```bash
    kubectl get serviceaccounts,roles,rolebindings,clusterroles,clusterrolebindings \
      -A -l kionga.dev/access=operations
    ```

    The team's actions go through your Kubernetes API, so your cluster's audit log
    records them when you enable audit logging.
- **Revoke.** Set `operations.access.enabled` to `false` and upgrade the release.
  The chart removes every object of the grant.

**Verify:** the label command lists the grant, and
`kubectl auth can-i get secrets -n kionga-system --as <subject>` answers `no`
unless you allowed Secret reads.

Changes to the chart values, such as an upgrade or a new feature, are changes the
team makes through Helm. Review them in your own change process.

## Support bundle

When something is wrong, the team asks for a support bundle. It's a single archive
that a script writes from your cluster:

```bash
python3 scripts/support-bundle.py --context CONTEXT --namespace kionga-system
```

It is read-only. It collects tool and cluster versions, the Helm release and its
history, node and prerequisite details, Kionga resources with their status,
workloads, pods, events and recent logs. It never reads Secrets, removes every
literal environment value, and redacts credentials from text and logs. Read the
archive before you send it. You decide what leaves your account.

## Upgrades

The team plans each upgrade against the [release notes](../changelog.md) and
applies it with Helm, pinned to image digests, as described in
[Updates and rollback](updates.md). A failed upgrade is rolled back with
`helm rollback`, which restores Kubernetes manifests only. It doesn't restore
databases or custom resource definitions, so a backup comes before an upgrade.
The window and the approval process are agreed in the contract.

## Backup and restore

Your data lives in PostgreSQL, object storage and your secret manager. The team
runs the backups and the restores from them. Backup
schedules, retention and restore targets are agreed in the contract. For the
controls that any production install needs, see
[Production readiness](production-operations.md#backups-and-recovery).

## On-call

The team is reachable through the channel in your contract. Hours of coverage,
response times and escalation paths are agreed in the contract. Access during an
incident uses the same grant: the team can't reach more than `operations.access`
gives it.

## Runbook for your team

| Task | Steps |
| --- | --- |
| Start the engagement | Meet the [prerequisites](kubernetes-prerequisites.md). Create the cluster and the identity group. Set `operations.access` and install the chart. |
| Review what was granted | Run the label command above. |
| Allow a one-time Secret read | Set `allowSecretRead: true`, upgrade, and set it back to `false` afterward. |
| Collect evidence for support | Run the support bundle script and review the archive. |
| End access | Set `operations.access.enabled` to `false`, upgrade, and run the label command to confirm nothing remains. |
| Leave the managed plan | Keep the release as it is. It is the standard chart. Take over upgrades with [Updates and rollback](updates.md). |

## Next steps

- [Kubernetes prerequisites](kubernetes-prerequisites.md).
- [Production readiness](production-operations.md).
- [Roadmap](../roadmap.md): the Kionga-hosted option that is planned for later.
