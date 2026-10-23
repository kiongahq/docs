---
description: Install Kionga on a managed Kubernetes cluster with the Helm chart, external dependencies, private images and secrets from your secret manager.
---

# Deploy on Kubernetes

This guide shows you how to install Kionga on a managed Kubernetes cluster with
the Helm chart in `deploy/helm/kionga`. It is the deployment for teams: it runs
the control plane with multiple replicas and provisions per-user notebooks,
IDE workspaces and agents in a separate namespace.

The chart installs Kionga's own components:

| Component | Replicas | Role |
| --- | --- | --- |
| Gateway | 3, autoscaled up to 10 | Console, API and workspace routing |
| Operator | 2, with leader election | Creates workspace and agent pods |
| Integration worker | 2 | Consumes platform events from Kafka |
| Feature gateway | 2 | Online feature lookups |
| Storage proxy | 2 | Object storage access for workspaces |
| Trace proxy | 2 | Agent and LLM tracing |

Every component has a disruption budget, a rolling update that keeps all
replicas available, and topology spread constraints. These help availability
but do not replace redundant dependencies.

For provider-specific steps, see [Amazon EKS](providers/aws-eks.md),
[Google GKE](providers/gcp-gke.md) or [Azure AKS](providers/azure-aks.md).

## Before you begin

**Cluster**

- Managed Kubernetes 1.29 or later, still supported by your provider, with at
  least three Ready nodes across two or more zones. Use node architectures your
  images support.
- A CNI that enforces NetworkPolicy, cluster DNS, metrics-server and an ingress
  controller.
- An encrypted StorageClass that allows volume expansion, and tested volume
  snapshots.
- For the supplied secret-manager integration:
  [External Secrets Operator](https://external-secrets.io/) with the
  `external-secrets.io/v1` API, installed separately.
- For `monitoring.enabled`: the Prometheus Operator and kube-state-metrics.

**Dependencies you operate**

- PostgreSQL (with TLS) and Redis, both redundant and private.
- S3-compatible object storage.
- Kafka and Kafka REST.
- The engines you offer, such as MLflow and Prefect.

The chart does not install databases or engines, and it does not install GPU
drivers, GPU node pools or cloud IAM.

**DNS and TLS**

- A console hostname, for example `console.example.com`, with a TLS Secret or
  certificate automation.
- For browser workspaces: a wildcard name such as `*.workspaces.example.com`
  pointing at the ingress, and a wildcard certificate. The console and
  workspace hosts must share a registrable domain so that workspace cookies
  stay first-party while each workspace has its own origin.

**Identity**

- An OIDC identity provider with HTTPS endpoints that issues RS256-signed
  tokens. Register a client with the callback
  `https://<console-host>/auth/callback`.

**Access**

- A cluster-administrator identity for the one-time bootstrap, and a narrower
  deploy identity afterwards.
- `kubectl`, Helm and Python 3 on the machine you deploy from, and a checkout
  of the `deploy` repository. Run commands from the folder that holds `deploy/`.
- A GitHub token with only the `read:packages` scope for the private
  `ghcr.io/kiongahq` images, and the image digests of the release you deploy.

**Secrets**

Store these in your secret manager, never in Helm values or command arguments:

| Kubernetes Secret | Keys |
| --- | --- |
| `kionga-gateway` | `DATABASE_URL`, `OIDC_CLIENT_SECRET`, `MLAIOPS_INTERNAL_TOKEN`, `KIONGA_CREDENTIAL_KEY` |
| `kionga-features` | `REDIS_URL`, `MLAIOPS_INTERNAL_TOKEN` |
| `kionga-storage` | `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `MLAIOPS_INTERNAL_TOKEN` |

`DATABASE_URL` must use `sslmode=verify-full`. `OIDC_CLIENT_SECRET` and
`MLAIOPS_INTERNAL_TOKEN` need at least 24 characters. `KIONGA_CREDENTIAL_KEY`
is the base64 encoding of exactly 32 bytes (`openssl rand -base64 32`); keep it
stable across replicas and restarts, because it encrypts users' stored personal
credentials.

## Steps

1. **Bootstrap the namespace and custom resources.** With the
   cluster-administrator identity:

    ```bash
    kubectl --context CONTEXT create namespace kionga-system
    kubectl --context CONTEXT label namespace kionga-system pod-security.kubernetes.io/enforce=restricted
    kubectl --context CONTEXT apply -f deploy/config/crd/
    ```

    The chart creates the workload namespace (`kionga-workloads` by default)
    with restricted pod security and a resource quota. Do not create it
    yourself, and do not share it between releases. Helm keeps it when you
    uninstall, so user workloads are never deleted silently; keeping it is not a
    backup.

2. **Create the registry pull Secret** in the release namespace (platform pods)
   and in the workload namespace (workspace and agent pods):

    ```bash
    for ns in kionga-system kionga-workloads; do
      kubectl --context CONTEXT -n "$ns" create secret docker-registry ghcr-pull \
        --docker-server=ghcr.io --docker-username=<github-user> --docker-password="$GHCR_TOKEN"
    done
    ```

    If the workload namespace does not exist yet, create this Secret there right
    after the first install. If you manage secrets with External Secrets, create
    the same `kubernetes.io/dockerconfigjson` Secret in both namespaces that way
    instead.

3. **Connect the secret manager.** Edit the store example for your provider
   (`deploy/helm/secretstore-aws.example.yaml`,
   `deploy/helm/secretstore-gcp.example.yaml` or
   `deploy/helm/secretstore-azure.example.yaml`): replace the account,
   project, region and identity placeholders, then apply it. Each example
   creates the `kionga-secret-reader` service account and a
   `SecretStore` named `kionga-store`. Grant that identity read access to the
   Kionga secret only; the examples do not create cloud IAM bindings. Your
   provider guide lists the identity setup.

    Without External Secrets, create the three Secrets in the table above
    yourself, with one key per value.

4. **Write the values overlay.** Copy `deploy/helm/production.example.yaml` to
   a protected location such as `/secure/production.yaml` and replace every
   placeholder:

    - `images`: every image as `repository@sha256:<digest>`, including
      `jupyter` and `ide`.
    - `imagePullSecrets: [{name: ghcr-pull}]`. The chart adds it to every
      platform pod and passes the name to the operator in
      `KIONGA_IMAGE_PULL_SECRETS`, which adds it to every workspace and agent
      pod.
    - `storageClass`, `ingress.className`, `ingress.host`,
      `ingress.tlsSecretName` and `ingress.controllerNamespace`.
    - `workspaceIngress.baseDomain` and `config.KIONGA_WORKSPACE_BASE_DOMAIN`:
      the same wildcard base, for example `workspaces.example.com`.
    - `config`: your OIDC endpoints, `MLAIOPS_ALLOWED_ORIGIN`
      (`https://<console-host>`), `OIDC_REDIRECT_URL`
      (`https://<console-host>/auth/callback`) and the engine and storage
      addresses. The example's internal URLs assume release `kionga` in
      namespace `kionga-system`.
    - `externalSecrets.targets`: map each Secret key to the property in your
      secret manager.
    - `networkPolicy.externalEgress`: explicit destinations and ports for the
      Kubernetes API server, PostgreSQL, Redis, the identity provider, Kafka
      REST, object storage and engines. Replace the example CIDR. With an empty
      list, all external traffic except DNS is denied.
    - Resource requests, limits and `workspaceQuota`, sized from measured
      workloads.

    Optional settings:

    - **Authenticated Kafka REST:** add `KAFKA_REST_TOKEN` to the `secrets`
      list of both `components.gateway` and `components.integration-worker`,
      and add the key to their Secrets. Lists in an overlay replace the
      defaults, so repeat the default keys.
    - **Break-glass administrator:** set `config.KIONGA_LOCAL_LOGIN: "true"`,
      add `MLAIOPS_LOCAL_PASSWORD` to the gateway's `secrets` list and Secret.
      The gateway refuses to start unless that password has at least 16
      characters and contains none of `local`, `change-me` or `password`.
    - **Workspace storage classes:** set
      `config.WORKSPACE_ALLOWED_STORAGE_CLASSES` to a comma-separated
      allowlist. See [Tenant storage](external-storage.md#tenant-storage-on-kubernetes).
    - **Monitoring:** `monitoring.enabled: true` creates ServiceMonitors for the
      gateway (port 9090), operator (port 8080) and integration worker
      (`/metrics` on port 8086), and alerts for fewer than two available
      gateway replicas and stale Kafka polling. Scraping is allowed only from
      `monitoring.namespace`. Make `monitoring.selectorLabels` match your
      Prometheus selectors.

    Create the Kafka topics your installation needs through your Kafka
    administration process; `deploy/scripts/local-topics.sh` lists them.

5. **Check the release without installing it.**

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml
    ```

    The script lints and renders the chart, then checks that the namespace,
    the Kionga custom resource definitions and, when your values need them,
    the External Secrets and Prometheus Operator definitions exist. It prints
    `Inputs rendered and cluster prerequisites checked.` To layer a provider
    overlay, add it after the base file; later files take precedence.

6. **Install.**

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml --apply
    ```

    The script runs `helm upgrade --install` with `--atomic --wait` and a
    15-minute timeout, then waits for the gateway rollout. If the install
    fails, Helm rolls it back.

## Verify

1. Check the resources:

    ```bash
    kubectl --context CONTEXT -n kionga-system get pods,services,ingress,hpa,pdb
    kubectl --context CONTEXT -n kionga-system get externalsecrets
    ```

    Every pod is `Running` and ready, and every ExternalSecret reports
    `SecretSynced`. The gateway is ready only when it can reach PostgreSQL; the
    integration worker is ready only after a recent successful poll.

2. Run the production verifier. It needs an ID token for an administrator and
   for a provisioned normal user (bearer tokens from your identity provider,
   not Kionga API keys) in protected files, a project the user cannot access,
   and the hostname of a provisioned workspace:

    ```bash
    python3 deploy/scripts/verify-production.py \
      --context CONTEXT --namespace kionga-system \
      --origin https://console.example.com \
      --workspace-host https://workbench-0123456789abcdef0123456789abcdef.workspaces.example.com \
      --admin-token-file /secure/admin-id-token \
      --user-token-file /secure/user-id-token \
      --forbidden-project PROJECT_ID --expect-monitoring
    ```

    It checks replicas, image digests, probes, autoscaling, ingress TLS,
    namespace policies, multi-zone nodes, HTTPS, anonymous denial,
    administrator and user access, cross-project denial and workspace host
    isolation. By default it changes nothing. Add `--test-workspace-handoff` to
    create a short-lived workspace session, check its cookie and API access,
    and revoke it.

3. Complete the [production readiness checklist](production-operations.md#acceptance-checklist)
   with real identities and data. Replica counts alone do not prove failover
   works.

## How workspace access works

Each workspace gets its own hostname under the wildcard domain. The name
contains an opaque 32-character hash, so OIDC subjects never appear in DNS or
certificate logs. When a user opens a workspace, the console submits a
single-use ticket (valid for 45 seconds) in a form POST body, and the gateway
exchanges it for a 30-minute, host-only, HttpOnly cookie for that workspace.
Every request checks the user's current grant and the workspace owner.
Suspending a grant denies access, and signing out of the console revokes the
user's workspace sessions. Do not log POST bodies at the ingress. Test Host
header forwarding, the wildcard certificate and browser cookies in staging.

## Upgrade and roll back

**Upgrade.** Update the image digests in your overlay and run step 5 and step 6
again. Promote the same digests through staging first. Gateway replicas apply
database migrations one at a time under a PostgreSQL lock; check migration
compatibility before you upgrade.

**Rotate secrets.** Kionga reads secret files at startup. After the secret
manager syncs a new value, restart the components that use it:

```bash
kubectl --context CONTEXT -n kionga-system rollout restart deployment/kionga-gateway
```

**Roll back.**

```bash
helm history kionga --kube-context CONTEXT -n kionga-system
helm rollback kionga REVISION --kube-context CONTEXT -n kionga-system --wait --timeout 15m
```

Rollback restores Kubernetes manifests only. It does not restore databases,
custom resource definitions, external secrets or user data. Never delete
PersistentVolumeClaims as a recovery step.

In CI, deploy with short-lived cloud credentials (OIDC federation) or a GitOps
controller rather than long-lived `kubeconfig` files or cloud keys. Never pass
secret values with `helm --set`: Helm stores release values.

## Next steps

- [Production readiness](production-operations.md): monitoring, backups,
  release controls and the acceptance checklist.
- [Single sign-on](single-sign-on.md) and [Permissions](../reference/rbac.md):
  map identity provider groups to roles and provision users by OIDC subject.
- [External object storage](external-storage.md) and
  [Log export](log-export.md).
- [Troubleshooting](troubleshooting.md#kubernetes).

Related: [Kubernetes Secret good practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/),
[Network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/),
[Pod security standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/),
[Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/).
