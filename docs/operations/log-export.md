---
description: Ship one tenant's Kionga log entries to Elasticsearch or OpenSearch with the optional log exporter, and check its delivery state.
---

# Export logs to Elasticsearch or OpenSearch

This guide shows you how to run the optional `log-exporter` service, which
ships one tenant's Kionga log entries (see [Logs and events](../guides/logs.md))
to Elasticsearch or OpenSearch. The gateway never waits on the exporter: if it
is not running, is configured incorrectly, or the cluster is down, pipelines and the
console keep working, and the **Platform** page shows the exporter's state.

The exporter is packaged as a Compose profile in `deploy/compose.yaml`. The
Helm chart does not include it.

## Before you begin

- A running local stack; see [Run locally](local.md).
- An Elasticsearch or OpenSearch cluster reachable over HTTPS, with an
  Elasticsearch API key or a username and password that can write to the
  destination below.
- For a private CA, its PEM bundle.

## Steps

1. **Store the credential as a file.** Compose mounts the `config/secrets/`
   folder of your workspace folder (the folder that holds `deploy/`, so
   `config/secrets/` sits beside `deploy/`) read-only at `/run/kionga-secrets`
   in the exporter. For example:

    ```bash
    mkdir -p config/secrets
    printf '%s' "$ES_API_KEY" > config/secrets/es-api-key
    chmod 600 config/secrets/es-api-key
    ```

    Keep this folder out of Git.

2. **Configure the exporter** in `deploy/.env`. For Elasticsearch with an API
   key:

    ```text
    KIONGA_LOG_EXPORT_TARGET=elasticsearch
    KIONGA_LOG_EXPORT_URL=https://search.example.com:9200
    KIONGA_LOG_EXPORT_API_KEY_FILE=/run/kionga-secrets/es-api-key
    ```

    All settings:

    | Variable | Purpose |
    | --- | --- |
    | `KIONGA_LOG_EXPORT_TARGET` | `elasticsearch` or `opensearch` |
    | `KIONGA_LOG_EXPORT_URL` | Cluster address, for example `https://cluster:9200`. Credentials in the URL are rejected |
    | `KIONGA_LOG_EXPORT_API_KEY_FILE` | File that holds an Elasticsearch API key |
    | `KIONGA_LOG_EXPORT_USERNAME`, `KIONGA_LOG_EXPORT_PASSWORD_FILE` | Basic authentication; the password is read from a file |
    | `KIONGA_LOG_EXPORT_CA_FILE` | PEM bundle for a private CA |
    | `KIONGA_LOG_EXPORT_ANONYMOUS` | `true` allows an unauthenticated test cluster |
    | `MLAIOPS_TENANT` | Tenant to export (default `default`); run one exporter per tenant |
    | `KIONGA_LOG_EXPORT_BATCH` | Documents per bulk request (default 500). Exporter environment only: Compose does not pass it from `deploy/.env` |
    | `KIONGA_LOG_EXPORT_INSECURE_TLS` | `true` turns off certificate checks, for testing only. Exporter environment only: Compose does not pass it from `deploy/.env` |

    The exporter sends credentials only over HTTPS to remote hosts and never
    includes them in errors, logs or its status.

3. **Start the exporter.**

    ```bash
    docker compose -f deploy/compose.yaml --profile log-export up -d log-exporter
    ```

## Verify

Check the exporter's status, which is published on `127.0.0.1` only:

```bash
curl -s http://localhost:8086/status
```

The same state appears on the console's **Platform** page:

| State | Meaning |
| --- | --- |
| `not_deployed` | The exporter is not running (the default). |
| `not_configured` | Running, but the `KIONGA_LOG_EXPORT_*` settings are incomplete; the detail says what is missing. |
| `configured` | Configured, nothing exported yet. |
| `healthy` | The last batch was accepted. |
| `degraded` | The last request failed; the exporter retries with a backoff from 1 second, doubling up to 60 seconds. |
| `unavailable` | Five or more consecutive failures. |

## Where the logs go

| | Elasticsearch | OpenSearch |
| --- | --- | --- |
| Destination | Data stream `logs-kionga.<tenant>-default` (matches the built-in `logs-*-*` index template) | Daily index `kionga-logs-<tenant>-YYYY.MM.DD` |
| Bulk action | `create` | `index` with a stable `_id` (`<tenant>-<sequence>`) |
| Authentication | API key (`Authorization: ApiKey ...`) or basic authentication | Basic authentication |

Documents use ECS-style fields: `@timestamp`, `message`, `log.level`,
`event.dataset` (`kionga.<source>`), `event.id`, and `kionga.tenant`,
`kionga.project_id`, `kionga.pipeline_id`, `kionga.run_id`, `kionga.node`,
`kionga.attempt`, `kionga.workload_kind`, `kionga.workload_id`,
`kionga.source`, `kionga.sequence` and `kionga.context`.

## Delivery guarantees

- **At least once.** The exporter's cursor (the log sequence number) is stored
  in the database and advances only after a batch is fully accepted or
  dead-lettered.
- **Partial failures.** Only rejected documents are sent again. `429` and `5xx`
  responses for single documents are retried with backoff up to five attempts;
  mapping and validation errors (`4xx`) are counted as dead-lettered and
  reported in the status.
- **Tenant separation.** Each exporter reads one tenant's rows (PostgreSQL
  row-level security) and writes to that tenant's data stream or indices.
- **Retention.** Retention in the target is your cluster's lifecycle policy
  (ILM or ISM). Kionga keeps log entries for `KIONGA_LOG_RETENTION_DAYS`; if
  the exporter falls further behind than that, the oldest entries are lost.

!!! note
    Both adapters are tested against servers that reproduce the bulk API,
    including partial failures, outages and authentication errors, but not
    against a live cluster. Use the test clusters below to try your setup.

## Try it with a local test cluster

The `log-export-es` profile starts a single-node Elasticsearch on
`localhost:9200`, and `log-export-os` starts OpenSearch on `localhost:9201`.
Both run without security. Set:

```text
KIONGA_LOG_EXPORT_ANONYMOUS=true
KIONGA_LOG_EXPORT_URL=http://elasticsearch:9200    # or http://opensearch:9200
```

Then start the cluster and the exporter:

```bash
docker compose -f deploy/compose.yaml --profile log-export-es --profile log-export up -d elasticsearch log-exporter
```

## Related

- Audit events are not exported by this service. They are published to the
  Kafka topic `mlaiops.audit.operations`, which the Kafka integrations of
  Elastic and OpenSearch can consume.
- [Logs and events](../guides/logs.md)
