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

## Configure and start the exporter

1. **Store the credential as a file.** Compose mounts `deploy/config/secrets/`
   read-only at `/run/kionga-secrets` in the exporter. Everything in that
   folder except its README is ignored by Git. For example:

    ```bash
    mkdir -p deploy/config/secrets
    printf '%s' "$ES_API_KEY" > deploy/config/secrets/es-api-key
    chmod 600 deploy/config/secrets/es-api-key
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
    | `KIONGA_TENANT` | Tenant to export (default `default`); run one exporter per tenant |
    | `KIONGA_LOG_EXPORT_BATCH` | Documents per bulk request (default 500). Set in `deploy/.env` |
    | `KIONGA_LOG_EXPORT_INSECURE_TLS` | `true` turns off certificate checks, for testing only. Set in `deploy/.env` |

    The exporter sends credentials only over HTTPS to remote hosts and never
    includes them in errors, logs or its status.

3. **Start the exporter.**

    ```bash
    docker compose -f deploy/compose.yaml --profile log-export up -d log-exporter
    ```

## Verify

1. Check the exporter's status, which is published on `127.0.0.1` only:

    ```bash
    curl -s http://localhost:8086/status
    ```

    The response is a JSON object. Its `state` field holds one of the values
    below, and `cursor`, `exported`, `dead_lettered` and `last_error` show the
    progress. When the settings are incomplete, the object has only `state` and
    `detail`.

2. Confirm that `state` is `healthy`. The same state appears on the console's
   **Platform** page:

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

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `not_deployed` on the **Platform** page | The exporter container is not running | Start it with the command in step 3 |
| `not_configured` with `KIONGA_LOG_EXPORT_TARGET must be elasticsearch or opensearch` | The target is empty or misspelled | Set `KIONGA_LOG_EXPORT_TARGET` to `elasticsearch` or `opensearch` |
| `not_configured` with `KIONGA_LOG_EXPORT_URL must be an http(s) URL` | The address is empty or has no scheme | Set a full URL such as `https://search.example.com:9200` |
| `not_configured` with `put credentials in KIONGA_LOG_EXPORT_USERNAME / *_FILE variables, not in the URL` | The URL embeds a user name or password | Remove them from the URL and use the credential variables |
| `not_configured` with `set KIONGA_LOG_EXPORT_API_KEY_FILE, or a username and KIONGA_LOG_EXPORT_PASSWORD_FILE, or KIONGA_LOG_EXPORT_ANONYMOUS=true for an unauthenticated test cluster` | No credential is set | Set an API key file, or a user name and a password file. Use anonymous access only for a test cluster |
| `not_configured` with `refusing to send credentials over plain http to a remote host; use https` | The URL uses `http` for a host other than `localhost` or `127.0.0.1` | Use an `https` address |
| `not_configured` with `read KIONGA_LOG_EXPORT_API_KEY_FILE: ...` or `read KIONGA_LOG_EXPORT_PASSWORD_FILE: ...` | The file does not exist inside the container | Put the file in `deploy/config/secrets/` and reference it as `/run/kionga-secrets/<name>` |
| `degraded` with `last_error` `<host> rejected the credentials (HTTP 401)` or `(HTTP 403)` | The cluster refused the API key or password | Issue a new key, update the file and restart the exporter |
| `degraded` with `last_error` `<host> unreachable: ...` | The exporter cannot reach the cluster, or TLS verification failed | Check the address and network. For a private CA, set `KIONGA_LOG_EXPORT_CA_FILE` |
| `degraded` with `last_error` `<host> returned HTTP <status>` | The cluster answered with an error | Read the cluster's own logs. The exporter retries with a backoff |
| `unavailable` | Five or more consecutive failures | Fix the cause shown in `last_error`. The state returns to `healthy` after the next accepted batch |
| `last_error` is `<n> document(s) rejected by the target and dead-lettered`, and `dead_lettered` grows | The cluster rejected single documents with a `4xx` mapping or validation error | Check the index template or mapping for the destination in [Where the logs go](#where-the-logs-go) |

## Related pages

- [Logs and events](../guides/logs.md)
- [Run locally](local.md)
- [Production readiness](production-operations.md)
- Audit events are not exported by this service. They are published to the
  Kafka topic `kionga.audit.operations`, which the Kafka integrations of
  Elastic and OpenSearch can consume.
