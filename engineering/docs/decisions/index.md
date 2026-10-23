---
description: The log of Kionga architecture decision records in MADR 4 format, and how to propose a new one.
---

# Architecture decision records

Decisions that shape the system are recorded here in the
[MADR 4](https://adr.github.io/madr/) format: context and problem, decision drivers,
considered options, the outcome, its consequences, and how compliance is confirmed.
Records are numbered in the order they were made and are never deleted; a reversed
decision is marked `superseded by NNNN` and links to the record that replaces it.

| Record | Status | Date |
| --- | --- | --- |
| [0001 Lay out pipeline graphs with Dagre and a Kionga SVG renderer](0001-dag-layout-library.md) | Accepted | 2026-10-09 |
| [0002 Blog editor, canonical content and editorial identity](0002-blog-editor.md) | Accepted | 2026-10-09 |
| [0003 Bundle RustFS as the object store](0003-object-store.md) | Accepted | 2026-10-09 |
| [0004 Go for the control plane, Python for ML-facing code](0004-go-control-plane-python-ml.md) | Accepted | 2026-06-27 |
| [0005 PostgreSQL as the system of record, Kafka through a transactional outbox](0005-postgresql-kafka-outbox.md) | Accepted | 2026-06-28 |
| [0006 Single sign-on through OIDC, with Dex as the bundled broker](0006-oidc-single-sign-on-dex.md) | Accepted | 2026-10-10 |
| [0007 Per-user workspaces on Kubernetes, a shared workbench in Compose](0007-per-user-workspaces.md) | Accepted | 2026-07-20 |
| [0008 Bind local published ports to loopback by default](0008-loopback-local-ports.md) | Accepted | 2026-10-21 |
| [0009 Private GHCR images, pulled with registry credentials](0009-private-images-and-pull-secrets.md) | Accepted | 2026-10-23 |
| [0010 One repository per component](0010-repository-per-component.md) | Accepted | 2026-10-09 |

Numbers follow the order records were written, so dates are not monotonic: 0004 to
0010 were written after the fact from the code and commit history and carry the date
the decision took effect. Each cites its evidence.

## Propose a decision

1. Copy the [template](template.md) to the next free number, for example
   `0011-short-title.md`.
2. Fill in every required section; keep the evidence concrete (files, tests, commits).
3. Add the record to this table, to the `Decisions` navigation in
   `engineering/mkdocs.yml`, and to
   [architecture section 9](../architecture/09-architecture-decisions.md).
4. Open a pull request with status `proposed`; set `accepted` when it merges.
