---
title: Engineering handbook
---

# Kionga engineering handbook

This handbook explains how Kionga is designed and built. It is written for people
who change Kionga's code: contributors, maintainers and reviewers. To install,
use or operate Kionga, read the [product documentation](https://kiongahq.github.io/docs/).

| Section | What it covers | Standard |
| --- | --- | --- |
| [Architecture](architecture/index.md) | System context, building blocks, runtime and deployment views, quality goals | [arc42](https://arc42.org/overview) |
| [Components](components/index.md) | Each repository and service: responsibilities, interfaces, code map | `ARCHITECTURE.md` per repository |
| [Contracts](contracts/backend.md) | Versioned interfaces between services | |
| [Decisions](decisions/index.md) | Why major technical choices were made | [MADR](https://adr.github.io/madr/) |
| [Status and plans](status/implementation-status.md) | What is implemented, validated, or planned | |

Each repository also carries a `CONTRIBUTING.md` (development setup, tests,
release) and an `ARCHITECTURE.md` (a map of its code).
