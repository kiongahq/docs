---
description: The Kionga engineering handbook, how Kionga is designed and built, for contributors, maintainers and reviewers.
---

# Kionga engineering handbook

This handbook explains how Kionga is designed and built. It is written for people who
change Kionga's code: contributors, maintainers and reviewers. To install, use or
operate Kionga, read the [product documentation](https://kiongahq.github.io/docs/).

| Section | What it covers | Standard |
| --- | --- | --- |
| [Architecture](architecture/index.md) | Goals, constraints, context, building blocks, runtime and deployment views, crosscutting concepts, quality, risks | [arc42](https://arc42.org/overview) |
| [Components](components/index.md) | Each repository and service: responsibility, interfaces, configuration, code map, tests | One shape per page |
| [Contracts](contracts/backend.md) | Interfaces between the control plane, its clients and its workers | |
| [Decisions](decisions/index.md) | Why major technical choices were made | [MADR 4](https://adr.github.io/madr/) |
| [Contributing](contributing/index.md) | Workspace setup, tests, CI gates, commits, and the [documentation standard](contributing/documentation.md) | |
| [Status and plans](status/implementation-status.md) | What is implemented, verified, or planned | |

Start with [architecture](architecture/index.md) for the big picture, or with
[contributing](contributing/index.md) to make your first change.

Every component repository also carries a `README.md`, a `CONTRIBUTING.md`
(development setup, tests, release) and an `ARCHITECTURE.md` (a map of its code).
