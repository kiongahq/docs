# Decision: bundled object store

**Chosen:** [RustFS](https://github.com/rustfs/rustfs) 1.0.1 (Apache-2.0), image
`rustfs/rustfs:1.0.1` pinned by digest, as the `objectstore` Compose service.
**Replaces:** MinIO.

## Why MinIO had to go

MinIO stopped publishing free images in October 2025 and archived its open source
repository in February 2026. On 2026-09-11 `minio/minio` and `minio/mc` were deleted
from Docker Hub, and since 2026-09-24 quay.io refuses anonymous pulls. A fresh
Kionga install or CI run could no longer start, and the last free release carries
CVE-2026-40344 (CVSS 8.8, authentication bypass), so pinning it was not an option.

## Requirements

S3 API with SigV4 (including presigned URLs for the storage proxy), path-style
addressing, bucket create/list, object metadata and content type, a health
endpoint, a web console for local use, multi-arch images, and a permissive licence
that fits a self-hosted product. It must run as one container with one volume.

## Options compared

| Option | Fit | Why not / why |
| --- | --- | --- |
| **RustFS** | S3-compatible, Apache-2.0, 1.0 GA (2026-09), ~35k stars, active; console on 9001, `/health`; MinIO-style deployment | Chosen. Closest to what Kionga already used (same ports, same single-volume model), permissive licence, documented migration path from MinIO. |
| SeaweedFS | Mature, Apache-2.0, broad S3 coverage | More moving parts (master, volume, filer, S3 gateway) for a single-node stack; S3 credentials need a separate config file. |
| Garage | Small, built for self-hosting | AGPL-3.0; no web console; buckets and keys need its admin CLI. |
| Chainguard MinIO | Same software, maintained build | Free tier serves only `:latest`, so builds cannot pin a version. |

## Consequences

- The Compose service is `objectstore`; it keeps `minio` as a network alias so
  existing `http://minio:9000` settings resolve. Credentials stay
  `mlaiops` / `mlaiops-local-secret` locally (`OBJECTSTORE_*` to override).
- RustFS runs as uid 10001 and has its own data volume (`objectstore-data`). Data
  from an existing MinIO volume is copied across with `make -C deploy migrate-minio`,
  which verifies every object and never writes to the source, rather than pointing
  RustFS at MinIO's files in place.
- `deploy` tests assert the image is pinned RustFS, that no service uses a
  `minio/` image, and that every S3 client points at `objectstore`. The platform
  accepts `rustfs`, `s3` and `minio` connection types for storage readiness.
- Production deployments keep using any external S3-compatible store (see
  [External object storage](../../operations/external-storage.md)).
