---
description: Write the control plane and its long-running services in Go, and the ML-facing SDK, runtimes and flows in Python.
status: "accepted"
date: 2026-06-27
---

# 0004 Go for the control plane, Python for ML-facing code

## Context and problem statement

Kionga has two kinds of code. The control plane is a set of long-running network
services: an API gateway, Kubernetes controllers, Kafka workers, a storage proxy, a
feature gateway, a serving manager and an LLM egress proxy. The ML-facing code is what
data scientists and agent developers import and extend: an SDK, LangGraph agents,
Prefect flows, MLflow training, feature definitions. Which language should each part
use?

## Decision drivers

- The control plane must be small to ship, quick to start, and safe to run as non-root
  in minimal images.
- The Kubernetes operator needs mature controller libraries.
- ML users work in Python, and the engines Kionga integrates (LangGraph, LangChain,
  Prefect flows, MLflow, scikit-learn, PyTorch, Langfuse's SDK) are Python libraries.
- The two sides must not import each other's code, so they can release independently.

## Considered options

- Go for the control plane and Python for ML-facing code
- Python for everything
- Go for everything

## Decision outcome

Chosen option: **Go for the control plane and Python for ML-facing code**, because it
is the only option that gives the control plane static binaries and controller-runtime
while keeping users in the Python ML ecosystem.

### Consequences

- Good, because Go services build to static binaries on
  `gcr.io/distroless/static-debian12:nonroot` and the Helm chart can run them with a
  read-only root file system and no capabilities.
- Good, because the operator uses `controller-runtime` and `client-go` directly.
- Good, because the SDK, agent runtime and pipeline runner use the libraries their
  users already know.
- Bad, because contributors need two toolchains, and CI runs two reusable workflows
  (`go.yml`, `python.yml`) with different security scanners.
- Neutral, because the two sides meet only over HTTP (the REST API with a service
  token), Kafka through its REST proxy, and container images. Choosing the Karapace
  REST proxy follows from this: Python services need only an HTTP client to use Kafka.

### Confirmation

Each repository's language is fixed by its build: `go.mod` in `platform`, `serving` and
`trace-proxy`; `pyproject.toml` or `requirements.txt` in `sdk-python`,
`agent-runtime`, `pipeline-runner`, `workspace` and `contracts`. No Python repository
imports Go code and no Go repository embeds Python.

## Pros and cons of the options

### Go control plane, Python ML-facing code

- Good, because each side uses the ecosystem built for it.
- Bad, because shared logic (for example pipeline validation) must be expressed as a
  contract, not a shared library. The `contracts` repository holds the JSON Schema
  for `kionga.dev/v1 Pipeline`.

### Python for everything

- Good, because there is one toolchain.
- Bad, because long-running proxies and controllers would ship a Python runtime in
  every image and lose `controller-runtime`.

### Go for everything

- Bad, because the agent graphs, flows and training code depend on Python-only
  libraries.

## More information

Written after the fact. Evidence: the first platform commit (`610529d`, 2026-06-27)
already contained `go/cmd`, `go/internal` and a Python `mlaiops_sdk`; the split into
repositories ([decision 0010](0010-repository-per-component.md)) kept the language
boundary; `platform/go/go.mod`; `sdk-python/pyproject.toml`. See
[technology](../architecture/technology.md#languages-and-runtimes).
