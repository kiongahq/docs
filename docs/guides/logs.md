---
icon: material/text-box-search-outline
description: Read, filter, search and stream the logs and events of pipeline runs in the console or through the API.
---

# Search and stream pipeline logs

Read the logs of a pipeline node, search logs across runs, and stream new lines
from a script. Kionga stores structured logs and events for every pipeline run,
tagged with the tenant, project, flow, run, node, attempt and workload.

## Before you begin

- You need the `pipelines` service for a normal user, or any of the `viewer`,
  `engineer`, `operator` or `admin` roles, plus the `logs:Read` permission, which
  these roles include. When a policy denies `logs:Read`, runs are still visible
  but without their logs.
- You see only projects you can read. A run in another project returns a 404
  response.
- For the API, export `KIONGA_URL` and a credential (see
  [Authentication](../reference/api.md#authentication)).

## Read the logs of one node

1. Open **Pipelines** and select **Open run** in a run's row.
2. Select a node in the **Execution graph**.
3. In **Node logs**, set **Severity** and **Source**, enter text in **Search**,
   select **Load earlier lines** for older entries, or turn on **Live tail**.

## Search logs across runs

1. Open **Logs**.
2. Choose a project with the page's **Project** selector, and optionally enter a
   **Run** and a **Node**. The filters apply as you change them. Select
   **Refresh** to load again.
3. Set **Time window** (the default is **Last hour**; the other choices are
   **Last 15 minutes**, **Last day**, **Last week** and **All time**),
   **Severity** (**All**, **Errors**, **Warnings and errors** or **Info and
   above**), **Source**, and **Search** text. The table lists lines in time
   order, oldest first. Select **Load earlier lines** for older ones, or turn on
   **Live tail** to follow new lines.

From the API:

```bash
curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
  "$KIONGA_URL/api/v1/logs?run_id=<run>&node=train&severity=warn,error&q=timeout"
curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
  "$KIONGA_URL/api/v1/logs?project_id=<project>&order=desc&limit=100&before=<sequence>"
```

## Stream logs from a script

1. Open a stream for a run. The stream accepts the same filters as the search
   query:

    ```bash
    curl -N -H "Authorization: Bearer $KIONGA_TOKEN" \
      "$KIONGA_URL/api/v1/logs/stream?run_id=<run>"
    ```

2. Read the events. The stream uses Server-Sent Events. Each `event: logs` message carries a JSON
array of at most 200 entries and an `id: <sequence>`, and the stream continues
from the last entry, so a slow client never loses lines. To resume after a
disconnect, reconnect with the `Last-Event-ID` header.

## What Kionga records

| Source | Produced by | Examples |
| --- | --- | --- |
| `runner` | The pipeline runner, while a container runs | Container stdout and stderr, one entry per line |
| `platform` | The gateway | Every node transition (`train → failed: ValueError: ...`) with attempt, exit code and workload |
| `engine` | Reserved for orchestrator messages | |
| `k8s` | The [Kubernetes executor](pipelines.md#kubernetes) | Pod and Job events such as `FailedScheduling`, `OOMKilled` or a deadline |

Each entry has a timestamp, source, severity (`debug`, `info`, `warn`, `error`),
message and structured context. Lines from stderr are `warn` unless the runner
says otherwise.

- **Secrets are redacted before storage:** cloud and provider keys, bearer and
  JSON web tokens, private key blocks, credentials in URLs, `password=` style
  pairs, and the values of the gateway's own secret environment variables.
- **Streamed output per node is capped** at `KIONGA_PIPELINE_LOG_STREAM_LIMIT_BYTES`
  (default 5 MiB), with a truncation notice. The final output tail is still kept
  on the node.
- **Retention:** entries older than `KIONGA_LOG_RETENTION_DAYS` (default 30) are
  deleted every hour.

## Verify

1. **Node logs:** the node's lines appear under **Node logs** in the run page, each
   with its severity and source.
2. **Search:** the results contain only entries that match your filters. The API
   returns them in an `items` array, and adds `next_before` (descending order) or
   `next_after` (ascending order) when a full page came back, so you can request
   the next page.
3. **Stream:** while the run is active, `event: logs` messages arrive, each with
   an `id:` line holding the sequence of its last entry. When there are no new
   lines, the stream sends a `: keep-alive` comment about every 15 seconds.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `404` with `run not found` or `project not found` | The run or project does not exist, or you cannot read its project. | Check the ID, and ask a project owner or an administrator for access. |
| `400` with `since must be an RFC 3339 timestamp` (or `until must be ...`) | The `since` or `until` value is not an RFC 3339 timestamp. | Use a form such as `2026-01-31T09:30:00Z`. |
| A run is visible but its logs are empty | A policy denies `logs:Read` on the pipeline. | Ask an administrator to change the [policy](access-control.md). |
| Older lines are missing | Kionga deletes entries older than `KIONGA_LOG_RETENTION_DAYS` (default 30) every hour. | Export logs to your own store before they expire; see [Export logs](../operations/log-export.md). |
| The log ends with `[log output truncated after <n> bytes; the full tail is in the step message]` | Streamed output per node is capped at `KIONGA_PIPELINE_LOG_STREAM_LIMIT_BYTES` (default 5 MiB, at most 100 MiB). | Read the output tail in the node's message, or raise the limit. |
| A message ends with `…[truncated]` | The gateway cuts a message longer than 8 KiB. | Log long values across several lines. |

## Related pages

- [Export logs to Elasticsearch or OpenSearch](../operations/log-export.md).
  Kionga keeps working whether or not the exporter runs; **Platform** shows its
  state.
- [Define and run pipelines](pipelines.md).
- [Access control](access-control.md).
