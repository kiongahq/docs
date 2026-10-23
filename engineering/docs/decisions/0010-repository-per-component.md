---
description: Split the platform single repository into one repository per component, joined by versioned contracts, HTTP APIs, container images and shared CI workflows.
status: "accepted"
date: 2026-10-09
---

# 0010 One repository per component

## Context and problem statement

Kionga started as one repository holding the Go control plane, the Python SDK, the
agent runtime, the pipeline runner, the serving manager, the trace proxy, the
workspace images, the deployment assets and the documentation. Every change ran every
test, every image was built from one tree, and parallel work on unrelated components
collided. How should the code be organized so components build, test and release
independently?

## Decision drivers

- Each component builds, tests and releases on its own.
- Components never import each other's code; they meet at contracts, APIs and images.
- One place still runs everything together and catches cross-component breakage.
- History is preserved.
- CI and security gates stay consistent across components.

## Considered options

- One repository per component, with shared CI workflows and versioned contracts
- Keep the single repository

## Decision outcome

Chosen option: **One repository per component, with shared CI workflows and versioned
contracts**.

The `platform` repository keeps the control plane (gateway, console, store, auth and
IAM, scheduler, pipeline validation and execution, logs, editorial, operator, feature
gateway, storage proxy, integration worker, log exporter, CLI). `sdk-python`,
`agent-runtime`, `pipeline-runner`, `serving`, `trace-proxy`, `workspace`, `deploy` and
`docs` moved out with their history. `contracts` is a Git submodule of `platform`.
`kiongahq/.github` holds the reusable workflows and the repository list.

### Consequences

- Good, because each repository runs only its own gate tests and publishes only its
  own images.
- Good, because the reusable workflows give every repository the same lint, test and
  security gates.
- Bad, because a cross-repository change needs ordering: land the provider side first,
  keeping old behavior working; release it; then update the consumer and bump the pins
  (`SDK_VERSION`, image digests). See
  [working across repositories](../components/index.md#working-across-repositories).
- Bad, because a local checkout needs every repository side by side;
  `deploy/scripts/workspace.sh` (`make -C deploy workspace`) clones them.
- Neutral, because the `deploy` CI clones every component's `main` branch and runs the
  cross-repository checks, so integration breakage still fails a build.

### Confirmation

`deploy`'s CI workflow and its nightly Pressure workflow clone all components through
`deploy/scripts/workspace.sh` before testing. `repos.txt` in the
`kiongahq/.github` repository lists every repository in dependency order.

## Pros and cons of the options

### Repository per component

- Good, because ownership, release cadence and CI cost follow the component.
- Bad, because contract changes span pull requests in several repositories.

### Single repository

- Good, because a change across components is one commit.
- Bad, because every change builds and tests everything, and components are tempted to
  import each other's internals.

## More information

Written after the fact. Evidence: `platform` commit `77bef67` (2026-10-09, "split
components into their own kiongahq repositories"); the per-repository manifests and
the split procedure under `migration/` in `kiongahq/.github`; the `deploy` commit
`492952d` that made Compose build from sibling checkouts.
