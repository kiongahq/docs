---
description: Install Kionga on your machine and run your first project, pipeline, model and agent.
---

# Get started

Run Kionga on your own machine, then use it end to end: create a project, train
and serve a model, and chat with an agent. The local stack is the fastest way to
learn Kionga before you deploy it for a team.

| Step | Page | What you get |
| --- | --- | --- |
| 1 | [Install Kionga](installation.md) | The full platform running locally, with the console at `http://localhost:8080` |
| 2 | [Quickstart](quickstart.md) | A project, a trained and deployed model, a live prediction, and an agent conversation |
| 3 | [Service endpoints](../reference/service-endpoints.md) | Connections to MLflow, Prefect, PostgreSQL, Kafka and the other bundled services |

## Before you begin

You need a computer with Docker Engine and Docker Compose v2, at least 8 GB of
memory available to Docker, and 25 to 35 GB of free disk space for the first
build. The [installation guide](installation.md#before-you-begin) lists every
requirement.

## Local stack versus a team deployment

The local stack uses development credentials and binds every port to your own
machine. Those defaults are for learning and development only. To run Kionga for
a team, choose a deployment from [Deploy and operate](../operations/index.md)
and complete the [production readiness checklist](../operations/production-operations.md).

If installation or startup fails, see [Troubleshooting](../operations/troubleshooting.md).
