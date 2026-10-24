---
icon: material/text-box-search-outline
description: Read, filter, search and stream the logs and events of pipeline runs in the console or through the API.
---

# Search and stream pipeline logs

Kionga stores structured logs and events for every pipeline run, tagged with the
tenant, project, flow, run, node, attempt and workload. Use this guide to read a
node's logs, search across runs, and stream new lines from a script.

## Before you begin

- You need the `pipelines` service for a normal user, or any of the `viewer`,
  `engineer`, `operator` or `admin` roles, plus the `logs:Read` permission, which
  these roles include. When a policy denies `logs:Read`, runs are still visible
  but without their logs.
- You see only projects you can read. A run in another project returns a 404
  response.
- For the API, export `MLAIOPS_URL` and a credential (see
  [Authentication](../reference/api.md#authentication)).

## Read the logs of one node

1. Open **Pipelines** and click a run.
2. Select a node in the execution graph.
3. Filter by severity and source, search the text, load earlier lines, or turn on
   the live tail.

**Verify:** the node's lines appear, newest first, with their severity and
source.

## Search logs across runs

1. Open **Logs**.
2. Choose a project with the page's **Project** selector, and optionally enter a
   **Run ID**, a **Node** and a **Time range**. Click **Apply**.
3. Filter by source, severity and text. Results are newest first; click **Load
   earlier lines** for older ones, or **Live tail** to follow new lines.

From the API:

```bash
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/logs?run_id=<run>&node=train&severity=warn,error&q=timeout"
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/logs?project_id=<project>&order=desc&limit=100&before=<sequence>"
```

**Verify:** the results contain only entries that match your filters.

## Stream logs from a script

```bash
curl -N -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/logs/stream?run_id=<run>"
```

The stream uses Server-Sent Events. Each `event: logs` message carries a JSON
array of at most 200 entries and an `id: <sequence>`, and the stream continues
from the last entry, so a slow client never loses lines. To resume after a
disconnect, reconnect with the `Last-Event-ID` header.

**Verify:** new lines arrive while the run is active.

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
- **Streamed output per node is capped** at `MLAIOPS_PIPELINE_LOG_STREAM_LIMIT_BYTES`
  (default 5 MiB), with a truncation notice. The final output tail is still kept
  on the node.
- **Retention:** entries older than `KIONGA_LOG_RETENTION_DAYS` (default 30) are
  deleted every hour.

## Next steps

- [Export logs to Elasticsearch or OpenSearch](../operations/log-export.md).
  Kionga keeps working whether or not the exporter runs; **Platform** shows its
  state.
- [Define and run pipelines](pipelines.md).
