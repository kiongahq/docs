---
description: Bundle RustFS as the S3-compatible object store in the local stack, replacing MinIO.
status: "accepted"
date: 2026-10-09
---

# 0003 Bundle RustFS as the object store

## Context and problem statement

The local stack bundles an S3-compatible object store for models, artifacts, feature
snapshots, traces, agent state, pipeline logs and blog media. It was MinIO. MinIO
stopped publishing free images in October 2025 and archived its open-source
repository in February 2026. On 2026-09-11 `minio/minio` and `minio/mc` were deleted
from Docker Hub, and since 2026-09-24 quay.io refuses anonymous pulls. A fresh Kionga
install or CI run could no longer start, and the last free release carries
CVE-2026-40344 (CVSS 8.8, authentication bypass), so pinning it was not an option.
Which object store should the stack bundle instead?

## Decision drivers

- S3 API with SigV4, including presigned URLs for the storage proxy.
- Path-style addressing, bucket create and list, object metadata and content type.
- A health endpoint and a web console for local use.
- Multi-architecture images.
- A permissive license that fits a self-hosted product.
- One container with one volume.

## Considered options

- RustFS
- SeaweedFS
- Garage
- `Chainguard` MinIO

## Decision outcome

Chosen option: **RustFS**, because it is the only option that meets the local S3
contract with one Apache-2.0 service, one volume, a console and a health endpoint.
[RustFS](https://github.com/rustfs/rustfs) 1.0.1, image `rustfs/rustfs:1.0.1` pinned by
digest, runs as the `objectstore` Compose service.

### Consequences

- Good, because fresh installs and CI start again with a maintained, pinned image.
- Neutral, because the Compose service and DNS name are both `objectstore`, with
  credentials `mlaiops` and `mlaiops-local-secret` locally (`OBJECTSTORE_*` to
  override).
- Neutral, because RustFS runs as UID 10001 with its own `objectstore-data` volume.
  The local stack has no automatic migration and no MinIO DNS alias; older Docker
  volumes are left untouched and not mounted into RustFS.
- Neutral, because the platform accepts `rustfs` and `s3` connection types for storage
  readiness.
- Good, because production installations keep using any external S3-compatible store
  ([external object storage](https://kiongahq.github.io/docs/operations/external-storage/)).

### Confirmation

`deploy` tests assert that the image is pinned RustFS, that no service uses a `minio/`
image, and that every S3 client points at `objectstore`
(`test_object_store_is_pinned_rustfs_and_every_client_uses_it` in
`deploy/tests/test_local_bootstrap.py`).

## Pros and cons of the options

### RustFS

S3-compatible, Apache-2.0, 1.0 generally available in September 2026, about 35,000
GitHub stars at the time, active.

- Good, because it runs as a single container with a console on port 9001 and
  `/health`.
- Good, because the license is permissive.

### SeaweedFS

Mature, Apache-2.0, broad S3 coverage.

- Bad, because it has more moving parts (master, volume, filer, S3 gateway) for a
  single-node stack.
- Bad, because S3 credentials need a separate configuration file.

### Garage

Small and built for self-hosting.

- Bad, because it is AGPL-3.0.
- Bad, because it has no web console, and buckets and keys need its admin CLI.

### `Chainguard` MinIO

The same software in a maintained build.

- Bad, because the free tier serves only `:latest`, so builds cannot pin a version.

## More information

The switch landed in `deploy` commit `4052a12` (2026-10-09); a later commit
(`f1aac7b`, 2026-10-10) removed the temporary `minio` network alias and finished the
RustFS-only startup.
