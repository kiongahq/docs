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
  variable (`env:VARIABLE`), never the key itself. The variable must be
  `LAKE_CREDENTIALS`, start with `KIONGA_STORAGE_SECRET_`, or be listed in
  `KIONGA_STORAGE_SECRET_REFS`. See
  [Secret references](../reference/configuration.md#secret-references).
    - **Single server:** put the value in a file named after the variable in
      `secrets_directory`, and list the name in `secret_references.files` in
      `deployment.json`.
    - **Kubernetes:** add the key to the Secret `secretReferences.secretName`, and
      list the name in the chart's `secretReferences.names`.
    - **Local stack:** add `NAME=value` to `deploy/config/secrets/gateway.env`, then
      run `make -C deploy local-up`.

## Register a bucket

1. In the console, open **Platform** (in the **Operate** group). Under
   **Object storage connections**, select **Add object storage**. The
   **Connect object storage** dialog opens, and **Save and test** creates the
   connection and tests it in one step.

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

2. Fill in the fields. The console labels the API fields as the second column
    shows:

    | Field | Console label | Rules |
    | --- | --- | --- |
    | `name` | **Name** | 2 to 63 lowercase letters, digits and hyphens; unique |
    | `endpoint` | **S3 endpoint** | `http(s)://host[:port]`, with no path, query or embedded credentials |
    | `region` | **Region** | Lowercase letters, digits and hyphens. Requests are signed for `us-east-1` when empty |
    | `bucket` | **Bucket** | A valid S3 bucket name. Buckets with dots need `path_style` over HTTPS, because wildcard certificates do not cover them |
    | `path_style` | **Path-style addressing** | `true` for RustFS, Ceph and dotted bucket names; `false` for virtual-hosted Amazon S3. The console selects it by default |
    | `ca_bundle` | **Custom CA bundle** | PEM CA certificates, added to the system roots, for a private CA. Private keys are rejected |
    | `secret_ref` | **Secret reference** | `env:VARIABLE`, naming a permitted gateway variable that holds `ACCESS_KEY_ID:SECRET_ACCESS_KEY` |
    | `allowed_projects` | **Allowed project IDs** | IDs of the projects that may use the connection, separated by commas. Each project must exist |

    A new connection starts as `configured`.

3. In the console, **Save and test** already ran the test. To test again later,
   select **Test** on the connection. With the API, call the test endpoint with
   the connection's `id`:

    ```bash
    curl -b kionga.cookies -X POST "$GATEWAY/api/v1/admin/storage-connections/<id>/test"
    ```

## Verify

1. Read the result of the test from step 3. The response holds `health.state`
   and `health.detail`, and the **Health** column of the connection shows the same. The
   test sends a SigV4-signed `HEAD` request for the bucket and records one of
   these states with a reason:

    | State | Meaning |
    | --- | --- |
    | `healthy` | The bucket answered `200` within 3 seconds |
    | `degraded` | The bucket answered slowly (more than 3 seconds), returned `5xx`, or redirected to another region (the reason names the bucket's real region) |
    | `unavailable` | The endpoint is unreachable, TLS verification failed (add `ca_bundle`), access was denied (`403`: wrong or expired credentials, or missing `s3:ListBucket`) or the bucket does not exist (`404`) |
    | `configured` | Saved, but the `secret_ref` variable is not set on the gateway |

2. Confirm that the state is `healthy`. For any other state, follow the
   matching entry in [Troubleshooting](#troubleshooting).

Credentials never appear in responses, stored records or check reasons.

## Secure the bucket

- Require TLS. For a private CA, set `ca_bundle`; certificate verification
  cannot be turned off.
- Enable bucket encryption (SSE-S3 or SSE-KMS) and block public access.
- Use one IAM principal per deployment (or per tenant), scoped to the bucket
  and prefix.
- `allowed_projects` records which projects may use a connection. Grant users
  access to buckets through Kionga's bucket grants.
- On Kubernetes, prefer short-lived cloud credentials (IRSA on EKS, Workload
  Identity on GKE and AKS) for buckets. The storage proxy currently uses the
  mounted `S3_ACCESS_KEY` and `S3_SECRET_KEY`. Give the gateway a `secret_ref`
  variable through `components.gateway.extraEnv` with `valueFrom.secretKeyRef`,
  never as a plain value or from a ConfigMap.

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

## Troubleshooting

Each entry starts with what the test or the API reports. Enable bucket
versioning so that you can roll back a bad materialization to the
`offline_uri` recorded for an earlier run.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `configured` with `Credentials are not available: set the secret_ref environment variable on the gateway to ACCESS_KEY_ID:SECRET_ACCESS_KEY` | The variable named in `secret_ref` is not set on the gateway, or is empty | Set the variable as described in [Before you begin](#before-you-begin), restart the gateway and test again |
| `unavailable` with `Endpoint unreachable: ...` | The endpoint is down, or the gateway cannot reach it. Materialization runs fail and are recorded in lineage, and the feature view goes stale after its TTL | Restore the network path or the store. Online serving continues from Redis. Run materialization again when the store is back |
| `unavailable` with `TLS verification failed: ... Provide the endpoint's CA in ca_bundle.` | The endpoint uses a certificate from a private CA | Set `ca_bundle` to the PEM CA certificates. Certificate verification cannot be turned off |
| `unavailable` with `Access denied to bucket <name>: the credentials are wrong, expired, or lack s3:ListBucket` | The store answered `403`, for example after the credentials rotated | Update the gateway variable, restart the gateway and test again. Check that the key pair has `s3:ListBucket` on the bucket |
| `unavailable` with `Bucket <name> does not exist at this endpoint` | The store answered `404`: the bucket was deleted, or `endpoint` or `bucket` is wrong | Correct the connection, or restore the bucket from versioning or a replica. Lineage records which `offline_uri` each feature view version used |
| `degraded` with `Bucket <name> lives in region <region>, not "<region>"; update the region` | The bucket moved to another region, or `region` was set wrong | Update `region` |
| `degraded` with `Bucket check returned ...; check region and path_style` | The store redirected or rejected the request | Check `region` and `path_style` |
| `degraded` with `Object store returned ...` | The store answered `5xx` | Wait for the store to recover, then test again |
| `unavailable` with `buckets containing dots need path_style over https ...` or another validation message | A field fails the rules in the table in step 2 | Correct the field with `PUT` on the connection |
| `503` with `connection_unavailable`, and `secret_present` is `false` | The `secret_ref` variable is outside the permitted names, so the connection stops authenticating | Use a permitted variable and update the connection with `PUT`. See [Migrate a stored reference](production-operations.md#migrate-a-stored-reference) |
| A workspace is `Failed` with reason `StorageNotAllowed` (Kubernetes) | The storage class is not on `WORKSPACE_ALLOWED_STORAGE_CLASSES`, or a volume uses a source that tenants may not mount | Add the class to the allowlist, or remove the allowlist. See [Tenant storage on Kubernetes](#tenant-storage-on-kubernetes) |

## Related pages

- [Feature store integrations](../guides/feature-stores.md)
- [Deploy on Kubernetes](managed-kubernetes.md)
- [Secret references](../reference/configuration.md#secret-references)
- [Migrate a stored reference](production-operations.md#migrate-a-stored-reference)
