---
icon: material/server-network-outline
description: Compare the three ways to run Kionga (local Compose stack, single server, managed Kubernetes) and pick the one that fits your users, infrastructure and trust boundary.
---

# Choose a deployment

Kionga runs in three supported ways. They differ in who can reach the platform,
what infrastructure you provide, and which features are available. Pick one
before you follow an installation guide.

| | Local (Compose) | Single server | Managed Kubernetes |
| --- | --- | --- | --- |
| **Who it is for** | One person evaluating or developing Kionga on their own machine | A pilot, or a control plane in front of infrastructure you already run | Teams in production, with notebooks, IDE workspaces and agents provisioned per user |
| **What runs** | Every service, including PostgreSQL, Kafka, MLflow, Prefect, Langfuse, Dex and the RustFS object store | The gateway (console and API) behind Caddy, from released images | Replicated gateway, operator, integration worker, feature gateway, storage proxy and trace proxy; user workloads in their own namespace |
| **What you provide** | Docker with Compose v2, about 8 GB of memory and 25 to 35 GB of disk for the first build | A Linux host, a DNS name, an OIDC identity provider, PostgreSQL with TLS, and secret files | A cluster (Kubernetes 1.29 or later), ingress, TLS, storage, PostgreSQL, Redis, object storage, Kafka with Kafka REST, an OIDC identity provider and a secret manager |
| **Images** | Built from source checkouts | Released gateway image from the private `ghcr.io/kiongahq` registry and a Caddy image, both pinned by digest | Released images from the private `ghcr.io/kiongahq` registry, pinned by digest |
| **Sign-in** | Local `admin` account plus Dex (LDAP test directory, demo account, optional OAuth providers) | Your OIDC identity provider | Your OIDC identity provider |
| **Notebooks and IDE** | Shared Jupyter and optional browser IDE on the same machine | Not available (no workload plane) | Per-user workspaces on isolated subdomains |
| **Availability** | None; one machine | One gateway; expect downtime during upgrades | Multiple replicas with disruption budgets and autoscaling; your dependencies must also be redundant |
| **Start here** | [Run locally](local.md) | [Single server](public-vm.md) | [Deploy on Kubernetes](managed-kubernetes.md) |

## Trust boundaries

**Local.** The stack ships well-known development credentials for every data
service. Every published port binds to `127.0.0.1`, so only the machine running
the stack can reach it. Widening that binding exposes the data services, not
only the console. Do not use the local stack to serve other people.

**Single server.** Caddy is the only public listener (ports 80 and 443) and
terminates TLS. The gateway runs as a non-root user with a read-only root
filesystem and refuses to start in production mode without HTTPS OIDC, TLS to
PostgreSQL and strong credentials. You operate the database, identity provider
and any ML engines, and you deliver secrets as files. There is no gateway
failover.

**Managed Kubernetes.** Platform components run in a release namespace and user
workloads in a separate namespace with restricted pod security, a resource
quota and network policies that allow traffic only to and from the platform
namespace and DNS. Workspaces get their own hostnames
and host-only session cookies. Namespace isolation is not a sandbox against
cluster administrators or hostile code; see
[Production readiness](production-operations.md).

!!! note "Requires infrastructure you provide"
    Neither hosted option creates cloud accounts, databases, an identity
    provider, ML engines or a secret manager. A successful install or health
    check does not prove that an installation is secure or highly available.
    Complete the [production readiness checklist](production-operations.md)
    before you admit users.

A fourth path, the [Compose public overlay](../hosting.md), exposes the local
stack through Caddy. It is a legacy demo path and is not supported for
production.

## After you deploy

- [Production readiness](production-operations.md): security, monitoring,
  backups, release controls and the acceptance checklist.
- [Single sign-on](single-sign-on.md): connect LDAP, SAML, OAuth or OIDC.
- [External object storage](external-storage.md): register S3-compatible
  buckets.
- [Log export](log-export.md): ship logs to Elasticsearch or OpenSearch.
- [Troubleshooting](troubleshooting.md): symptoms, causes and fixes for each
  deployment.
