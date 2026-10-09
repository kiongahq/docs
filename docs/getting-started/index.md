# Getting started

Kionga is an open-source platform you can deploy for a team. The local Compose
stack is the fastest way to learn the workflows before configuring a hosted
environment. Commands here assume the repositories are sibling directories in
one workspace folder.

## Recommended path

1. [Install the local stack](installation.md) and confirm the gateway is healthy.
2. [Follow the quickstart](quickstart.md) to create a project, run a pipeline,
   serve a model, and inspect an agent session.
3. [Connect to the bundled services](../connecting-services.md) from a notebook,
   a local client, or another container.

The local profile uses development credentials and shared workspaces; those
defaults do not carry over to a multi-tenant deployment. For a team installation,
start with
[public hosting options](../hosting.md) and complete the
[production acceptance checklist](../operations/production-operations.md).

## Before you start

You need Docker Engine with Compose v2, enough free memory and disk for the
multi-service stack, and the component repositories. The
[installation guide](installation.md#prerequisites) gives current sizing and
bootstrap instructions. If startup fails, use the
[troubleshooting guide](../operations/troubleshooting.md).
