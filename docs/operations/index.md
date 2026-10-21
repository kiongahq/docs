# Operations

Kionga is self-hosted open-source software, with packages for local onboarding
and hosted deployments. Choose a path before following an installation procedure:
the packages have different trust and availability boundaries.

| Environment | Use | Start here |
| --- | --- | --- |
| Private development | Bundled Compose services with local credentials | [Local operations](local.md) |
| Public gateway pilot | Gateway and Caddy on one VM; identity, database, and ML services operated separately | [Public VM](public-vm.md) |
| Distributed team | Managed Kubernetes with workload isolation and external dependencies | [Managed Kubernetes](managed-kubernetes.md) |

For a first team rollout on Amazon EKS, the
[first-iteration deployment plan](first-iteration-deployment.md) sets the scope,
topology, phased runbook, and release gates.

Read [public hosting](../hosting.md) for the comparison, then complete the
[production acceptance checklist](production-operations.md) before admitting
users. A successful package build or health check is not evidence of a secure or
highly available production installation.

## Day-two topics

- [Troubleshoot](troubleshooting.md) startup, connectivity, and service failures.
- [Configure single sign-on](single-sign-on.md) with LDAP, SAML, OAuth, or OIDC.
- [Export logs](log-export.md) to an external search cluster.
- [Connect external object storage](external-storage.md).
- For managed clusters, follow the provider-specific [EKS](providers/aws-eks.md),
  [GKE](providers/gcp-gke.md), or [AKS](providers/azure-aks.md) guide.
