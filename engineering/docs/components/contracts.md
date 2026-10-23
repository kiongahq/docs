---
description: The contracts repository, versioned JSON Schema shared by Kionga components, today the Pipeline definition.
---

# Contracts repository

## Responsibility

Holds the definitions that more than one component reads, so each has a single
versioned source. Today it publishes one contract: the `kionga.dev/v1 Pipeline`
definition, a JSON Schema for pipeline YAML files.

## Interfaces

The schema at `contracts/pipeline/v1.schema.json`, released as Git tags (`v1.0.0`) and
referenced by its tagged raw URL from editors that use the YAML language server.

## Dependencies and consumers

The `platform` repository pins this repository as a Git submodule at
`platform/contracts`; `pipelinespec` tests read it, and the gateway validates every
pipeline definition before it stores or runs it. A change is a new tag that consumers
adopt ([working across repositories](index.md#working-across-repositories)).

## Code map

| Path | Contents |
| --- | --- |
| `contracts/pipeline/v1.schema.json` | The Pipeline schema |
| `contracts/pipeline/examples/` | Valid example definitions |
| `contracts/tests/test_pipeline_schema.py` | Schema tests |

## Tests

Install `requirements-dev.txt` (`jsonschema`, `pyyaml`, `pytest`, `ruff`), then run
`python -m pytest -q` and `ruff check .`. The tests validate the example and reject a
set of structural mistakes.
