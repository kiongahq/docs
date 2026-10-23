---
description: Register an existing S3-compatible bucket as a storage connection, test it, and control where tenant workloads may store data on Kubernetes.
---

# Connect external object storage

This guide shows you how to register an existing S3-compatible bucket with
Kionga as a **storage connection** and check that the platform can reach it.
The local stack ships the RustFS object store; team and production
deployments usually keep artifacts, feature snapshots and datasets in a store
you already run, such as Amazon S3, Google Cloud Storage through its S3
interoperability API, Ceph RGW, RustFS, Wasabi or Cloudflare R2.

## Before you begin

- An administrator account in Kionga.
- A bucket and an access key pair scoped to it: `s3:ListBucket` on the bucket,
  and `s3:GetObject` and `s3:PutObject` on the prefix Kionga uses. Never use
  root or account-wide keys.
- An environment variable on the gateway that holds the key pair as
  `ACCESS_KEY_ID:SECRET_ACCESS_KEY`. Kionga stores only a reference to the
  variable (`env:VARIABLE`), never the key itself.
    - **Local stack:** add the variable to the `gateway` service's
      `environment` in `deploy/compose.yaml`, then run
      `make -C deploy local-up`. Values in `deploy/.env` reach the gateway only
      when `deploy/compose.yaml` passes them through.
    - **Kubernetes:** add the variable to the gateway with the chart's
      `components.gateway.extraEnv`, read from a Secret with
      `valueFrom.secretKeyRef`.

## Register a bucket

1. In the console, open **Platform**. Under **Feature stores and object
   storage**, select **＋ Object storage**.

    Or call the API with an administrator session (see
    [Authentication](../reference/api.md#authentication) for how to get
    `kionga.cookies`):

    ```bash
    curl -b kionga.cookies -X POST "$GATEWAY/api/v1/admin/storage-connections" \
      -H 'Content-Type: application/json' -d '{
        "name": "team-lake",
        "endpoint": "https://s3.eu-west-1.amazonaws.com",
        "region": "eu-west-1",
        "bucket": "team-lake",
        "path_style": false,
        "secret_ref": "env:LAKE_CREDENTIALS",
        "allowed_projects": []
      }'
    ```

2. Fill in the fields:

    | Field | Rules |
    | --- | --- |
    | `name` | 2 to 63 lowercase letters, digits and hyphens; unique |
    | `endpoint` | `http(s)://host[:port]`, with no path, query or embedded credentials |
    | `region` | Lowercase letters, digits and hyphens. Requests are signed for `us-east-1` when empty |
    | `bucket` | A valid S3 bucket name. Buckets with dots need `path_style` over HTTPS, because wildcard certificates do not cover them |
    | `path_style` | `true` for RustFS, Ceph and dotted bucket names; `false` for virtual-hosted Amazon S3 |
    | `ca_bundle` | PEM CA certificates, added to the system roots, for a private CA. Private keys are rejected |
    | `secret_ref` | `env:VARIABLE`, naming the gateway variable that holds `ACCESS_KEY_ID:SECRET_ACCESS_KEY` |
    | `allowed_projects` | IDs of the projects that may use the connection. Each project must exist |

    A new connection starts as `configured`.

3. Select **Test**, or call the test endpoint with the connection's `id`:

    ```bash
    curl -b kionga.cookies -X POST "$GATEWAY/api/v1/admin/storage-connections/<id>/test"
    ```

## Verify

The test sends a SigV4-signed `HEAD` request for the bucket and records the
result with a reason:

| State | Meaning |
| --- | --- |
| `healthy` | The bucket answered `200` within 3 seconds |
| `degraded` | The bucket answered slowly (more than 3 seconds), returned `5xx`, or redirected to another region (the reason names the bucket's real region) |
| `unavailable` | The endpoint is unreachable, TLS verification failed (add `ca_bundle`), access was denied (`403`: wrong or expired credentials, or missing `s3:ListBucket`) or the bucket does not exist (`404`) |
| `configured` | Saved, but the `secret_ref` variable is not set on the gateway |

Credentials never appear in responses, stored records or check reasons.

## Secure the bucket

- Require TLS. For a private CA, set `ca_bundle`; certificate verification
  cannot be turned off.
- Enable bucket encryption (SSE-S3 or SSE-KMS) and block public access.
- Use one IAM principal per deployment (or per tenant), scoped to the bucket
  and prefix.
- `allowed_projects` records which projects may use a connection. Grant users
  access to buckets through Kionga's bucket grants.

## Plan for consistency and performance

- Amazon S3 offers strong read-after-write consistency. Most S3-compatible
  stores match it for single objects, but listings on some (older Ceph, some
  gateways) are eventually consistent. Kionga writes feature snapshots and
  model artifacts under immutable, versioned keys and records each URI in
  lineage, so readers never depend on a listing or an overwrite.
- Cross-region replication is asynchronous. Point training jobs at the primary
  region, or accept the replication lag.
- Keep compute and the bucket in the same region to avoid latency and egress
  cost.
- Online feature lookups are served from Redis and never read object storage.
- For large datasets in jobs, read with `pyarrow` or `fsspec` directly; mounted
  buckets are convenient for browsing but slow for random access.

## Recover from failures

| Failure | Effect | Recovery |
| --- | --- | --- |
| Endpoint down | Test reports `unavailable`; materialization runs fail and are recorded in lineage, and the feature view goes stale after its TTL | Online serving continues from Redis. Run materialization again when the store is back |
| Credentials rotated | Test reports `unavailable` with `403` | Update the gateway variable, restart the gateway and test again |
| Bucket deleted or emptied | Test reports `unavailable` with `404` | Restore from versioning or a replica; lineage records which `offline_uri` each feature view version used |
| Bucket moved to another region | Test reports `degraded` with the real region | Update `region` |

Enable bucket versioning so that you can roll back a bad materialization to the
`offline_uri` recorded for an earlier run.

## Tenant storage on Kubernetes

On Kubernetes, the operator checks the storage of every workspace before it creates
anything, so that tenants never choose where on a node their data lands:

- **No node paths.** Tenant workloads may mount only PersistentVolumeClaims,
  ConfigMaps, Secrets, `emptyDir`, projected and downward API volumes.
  `hostPath` and every other volume source are rejected.
- **Allowlisted storage classes.** Set `WORKSPACE_ALLOWED_STORAGE_CLASSES` to a
  comma-separated list (with the Helm chart, as
  `config.WORKSPACE_ALLOWED_STORAGE_CLASSES`, for example `gp3,s3-csi`). A
  workspace claim whose class (the chart's `storageClass`, or the cluster
  default when empty) is not on the list is refused.

A workspace that fails either check is marked `Failed` with reason
`StorageNotAllowed`, and no claim is created.

To give workspaces object storage as a volume, use an object storage CSI driver (for Amazon S3, Cloud Storage FUSE or
Azure Blob) exposed as an allowlisted
StorageClass. Access then follows the driver's identity binding, not node
paths. The allowlist applies to the whole operator; to give groups of tenants
different classes, run one installation per group.

## Related

- On Kubernetes, prefer short-lived cloud credentials (IRSA on EKS, Workload
  Identity on GKE and AKS) for buckets. The storage proxy currently uses the
  mounted `S3_ACCESS_KEY` and `S3_SECRET_KEY`,. Give the gateway a
  `secret_ref` variable through `components.gateway.extraEnv` with
  `valueFrom.secretKeyRef`, never as a plain value or from a ConfigMap.
- [Feature store integrations](../guides/feature-stores.md)
- [Deploy on Kubernetes](managed-kubernetes.md)
