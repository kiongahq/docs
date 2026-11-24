---
icon: material/account-wrench-outline
description: How the Enterprise plan works, where Kionga's team installs and operates Kionga inside your own cloud with the same Helm chart, what access you grant, and how upgrades, backups and support work.
---

# Managed operations

This page shows you how to start, check and end a managed operations
engagement, and explains who does what during it. Managed operations is part of
the Enterprise plan. Kionga's team installs and
operates Kionga **inside your own cloud**, in your cluster and your account, with
the same Helm chart that anyone can install. You get the platform without staffing
its upgrades, backups and on-call, as agreed in the contract. Kionga runs in your
account, and your data is stored there.

If you run Kionga yourself, nothing on this page applies, and you can skip it.
For the self-managed install, see [Deploy on Kubernetes](managed-kubernetes.md).

!!! info "Available in a later release"
    The access grant (`operations.access`) and the support bundle script are
    part of the chart changes that come after deploy v0.2.0. This page describes
    them as designed. Check the [release notes](../changelog.md) for the release
    that includes them before you rely on them. Prices, service levels,
    response times, certifications and contract terms are not part of this
    documentation. They are agreed in the contract.

## Before you begin

- An Enterprise plan contract that covers managed operations. It sets the
  prices, service levels, response times and support channel.
- A Kubernetes cluster in your cloud account that meets the
  [prerequisites](kubernetes-prerequisites.md), and the dependencies listed in
  [Deploy on Kubernetes](managed-kubernetes.md#before-you-begin).
- An identity provider, and a group or users in it for the people who will
  operate the installation. The cluster must accept their sign-in.
- A cluster-administrator identity to install the chart.
- `kubectl`, Helm and Python 3 on the machine you work from, and a checkout of
  the `deploy` repository.

## What stays with you and what Kionga runs

| | You | Kionga's team |
| --- | --- | --- |
| Cloud account and cluster | Own and pay for them. Create the cluster, or approve one | Installs into it |
| Data | Stored in your databases, object storage and secret manager, in your account | Operates the services that use them. Data handling terms are agreed in the contract |
| Network, DNS and TLS | Provide the domain, the wildcard DNS record and certificate rules | Configures Kionga's side |
| Identity | Run your identity provider and decide who is in `subjects` | Signs in only through the identities you list |
| Install and configuration | Approve changes | Installs the chart and keeps its values current |
| Upgrades | Approve the window | Plans and applies them, and rolls back if needed |
| Backup and restore | Own the backup storage | Backups and restores as agreed in the contract |
| On-call | Reach the team through the agreed channel | Coverage and response as agreed in the contract |

## Same chart, your cluster

Managed installs use the [Kubernetes chart](managed-kubernetes.md) and the
[prerequisites](kubernetes-prerequisites.md). There is no separate managed build,
so you can leave the managed plan and keep running the same install yourself.
Anything the team does is a Helm release and Kubernetes objects that you can read.

## Start the engagement

1. Meet the [prerequisites](kubernetes-prerequisites.md) and create the cluster.
2. Create the identity group for the people who will operate Kionga, in your
   identity provider.
3. Add the access grant to your values overlay. It is off by default:

    ```yaml
    operations:
      access:
        enabled: true
        subjects:
          - {kind: Group, name: kionga-operations}
        serviceAccount: {create: true, name: kionga-operations}
        allowSecretRead: false
    ```

4. Install or upgrade the chart with the script from
   [Deploy on Kubernetes](managed-kubernetes.md#install-the-chart):

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml --apply
    ```

5. Check the grant, as described in [Verify](#verify).

## What the access grant allows

Kionga's team needs access to your cluster to operate it. You grant it with one
chart value, `operations.access`. It is off by default, scoped, and easy to audit.

- **Who.** `subjects` lists identities from your identity provider, as Kubernetes
  `User` or `Group` entries. The chart can also create a service account.
- **Where.** The grant covers only Kionga's namespaces: the release namespace and
  the workload namespace, and the pipeline and sandbox namespaces when you
  use them. A small read-only cluster role covers cluster-wide facts, such as
  nodes, storage classes and custom resource definitions.
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

Changes to the chart values, such as an upgrade or a new feature, are changes the
team makes through Helm. Review them in your own change process.

## Support bundle

When something is wrong, the team asks for a support bundle. It's a single archive
that a script writes from your cluster:

```bash
python3 deploy/scripts/support-bundle.py --context CONTEXT --namespace kionga-system
```

It writes one `.tar.gz` file and prints its name, with the number of files and
of commands that failed.

It is read-only. It collects tool and cluster versions, the Helm release and its
history, node and prerequisite details, Kionga resources with their status,
workloads, pods, events and recent logs. It never reads Secrets, removes every
literal environment value, and redacts credentials it recognizes from text and logs. Redaction matches
known credential shapes and can't catch every secret a log might contain, so read
the archive before you send it. You decide what leaves your account.

## Upgrades

The team plans each upgrade against the [release notes](../changelog.md) and
applies it with Helm, pinned to image digests, as described in
[Updates and rollback](updates.md). A failed upgrade is rolled back with
`helm rollback`, which restores Kubernetes manifests only. It doesn't restore
databases or custom resource definitions, so a backup comes before an upgrade.
The window and the approval process are agreed in the contract.

## Backup and restore

Your data lives in PostgreSQL, object storage and your secret manager. Who runs the
backups and the restores from them, and the backup
schedules, retention and restore targets are agreed in the contract. For the
controls that any production install needs, see
[Production readiness](production-operations.md#backups-and-recovery).

## On-call

The team is reachable through the channel in your contract. Hours of coverage,
response times and escalation paths are agreed in the contract. Access during an
incident uses the same grant: the team can't reach more than `operations.access`
gives it.

## Common tasks

| Task | Steps |
| --- | --- |
| Review what was granted | Run the label command above. |
| Allow a one-time Secret read | Set `allowSecretRead: true`, upgrade, and set it back to `false` afterward. |
| Collect evidence for support | Run the support bundle script and review the archive. |
| End access | Set `operations.access.enabled` to `false`, upgrade, and run the label command to confirm nothing remains. |
| Leave the managed plan | Keep the release as it is. It is the standard chart. Take over upgrades with [Updates and rollback](updates.md). |

## Verify

1. List everything the grant created:

    ```bash
    kubectl get serviceaccounts,roles,rolebindings,clusterroles,clusterrolebindings \
      -A -l kionga.dev/access=operations
    ```

    The output has the service account (`kionga-operations` unless you renamed
    it), a role and a role binding in each Kionga namespace, and one cluster role
    and one cluster role binding. The roles and bindings are named
    `<release>-operations`. An empty result means the grant is off.

2. Check that a subject cannot read Secrets, unless you set `allowSecretRead`:

    ```bash
    kubectl auth can-i get secrets -n kionga-system --as <user>
    ```

    For a `Group` subject, add `--as-group <group>`. The answer is `no`.

3. Check what the grant allows:

    ```bash
    kubectl auth can-i delete pods -n kionga-system --as <user>
    kubectl auth can-i create pods/exec -n kionga-system --as <user>
    ```

    The first answer is `yes`, and the second is `no`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `operations.access needs subjects or serviceAccount.create` | The grant is on, with no subject and no service account | List at least one subject, or set `serviceAccount.create` to `true` |
| `operations.access.subjects entries must be kind User or Group (identities from your identity provider)` | A subject has another `kind`, such as `ServiceAccount` | Use `User` or `Group`. The chart creates the service account itself |
| `operations.access.subjects entries need a name` | A subject has no `name` | Add the identity's name |
| The label command lists nothing | `operations.access.enabled` is `false`, or you did not upgrade the release after you changed it | Set it to `true` and run the install script again |
| Objects with the label remain after you turned the grant off | The release was not upgraded | Upgrade the release. The chart removes every object of the grant |
| The team cannot read Secrets, for example to diagnose a failing install | `allowSecretRead` is `false`. This is the default | Allow a one-time read, as in [Common tasks](#common-tasks) |

## Related pages

- [Kubernetes prerequisites](kubernetes-prerequisites.md)
- [Deploy on Kubernetes](managed-kubernetes.md)
- [Updates and rollback](updates.md)
- [Production readiness](production-operations.md)
- [Roadmap](../roadmap.md): the Kionga-hosted option that is planned for later.
