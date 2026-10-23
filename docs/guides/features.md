---
description: Use Kionga's built-in feature store to browse feature views, read online features, define and materialize views, build leakage-free training sets, and expire stale online rows.
---

# Use the built-in feature store

Kionga includes a feature store for both real-time and batch use:

- **Online:** feature values in Redis, served through the feature gateway for
  low-latency reads by models, agents and stream processors.
- **Offline:** Parquet snapshots in object storage (`s3://mlaiops-features` by
  default) for training and analysis.

Every feature view has a versioned definition, a materialization history, and a
freshness status. This guide covers browsing views, reading features, defining
and materializing views, building training sets, and expiring stale rows. To use
a feature store you already run, such as Feast, see
[Connect an external feature store](feature-stores.md).

## Before you begin

- **To browse and read features:** the `features` service for a normal user, or
  any of the `viewer`, `engineer`, `operator` or `admin` roles.
- **To apply feature views:** the `features` service for a normal user, or the
  `engineer`, `operator` or `admin` role. Viewers are read-only.
- **To report materialization runs:** the `engineer`, `operator` or `admin` role,
  or the materializer's service identity. Normal users cannot.
- **To run the materializer and the retention sweep:** shell access to the
  deployment, or a Kionga workspace terminal for the Python modules.
- For the API examples, export `MLAIOPS_URL` and a personal API key with the
  `features` scope as `MLAIOPS_TOKEN`.

## Browse feature views

=== "Console"

    Open **Features**. Each feature view card shows its schema, TTL, online
    entity count, version, store location, freshness and recent failures. Use
    **Search feature views** to filter by name or tag.

=== "API"

    ```bash
    curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      "$MLAIOPS_URL/api/v1/features/views" | python -m json.tool
    ```

The bundled demo views are:

| View | Entity | Example fields |
| --- | --- | --- |
| `customer_profile` | `entity_id` | `plan`, `region`, `open_tickets`, `csat_90d` |
| `transaction_stats_5m` | `entity_id` | `txn_count_5m`, `txn_amount_5m`, `distinct_merchants_5m`, `home_region` |

Freshness compares the last successful materialization with the view's TTL:

| Freshness | Meaning |
| --- | --- |
| `fresh` | Materialized within the TTL |
| `stale` | The last successful materialization is older than the TTL |
| `never` | Never materialized successfully |

A view with a TTL of `0` never goes stale.

**Verify:** the views you expect are listed with a freshness of `fresh`.

## Read online features

The feature gateway answers lookups in a Feast-compatible shape. From a Kionga
workspace, its address is in `MLAIOPS_FEATURE_GATEWAY_URL`; on a Compose host it
listens on `http://localhost:8083`.

```bash
curl -s -X POST "$MLAIOPS_FEATURE_GATEWAY_URL/get-online-features" \
  -H 'Content-Type: application/json' \
  -d '{"feature_service": "customer_profile", "entities": [{"entity_id": "u123"}]}'
```

```json
{"results": [{"values": {"plan": "pro", "region": "eu-west", "open_tickets": 1, "csat_90d": 4.6},
              "statuses": {"plan": "PRESENT", "...": "PRESENT"}}]}
```

A missing entity returns `NOT_FOUND` statuses. Agents read the same data through
the `feature_store_lookup` tool and `AgentMemoryClient.get_entity_features`, and
the [real-time processor](realtime.md) uses it to enrich events.

**Verify:** the response has `PRESENT` statuses for an entity you materialized.

## Define and materialize a feature view

A feature view names an entity, a typed schema, a TTL and its source. The
materializer applies each definition to Kionga, writes online values through the
feature gateway, writes an offline snapshot, and reports the run.

1. Define the view. The bundled materializer reads the view list in
   `agent-runtime/features/definitions.py`: each entry has a `name`, an `entity`,
   `fields` with a `name` and `type`, `tags`, a `source` and `ttl_seconds`, and
   `source_rows` supplies its rows. To apply a definition without the
   materializer, post the same fields to the API:

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/features" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"name": "customer_profile", "entity": "entity_id",
           "fields": [{"name": "plan", "type": "string"}],
           "tags": ["customer"], "source": "s3://mlaiops-features/customer_profile",
           "ttl_seconds": 3600}'
    ```

2. Run the materializer. On Compose:

    ```bash
    docker compose -f deploy/compose.yaml up feature-materializer
    ```

    It applies each view, writes its online values, writes a Parquet snapshot
    under `s3://mlaiops-features/`, reports the run, and exits. You can also run
    it as `python -m features.materialize`.

Applying a definition that changed (entity, fields, tags, source or TTL) creates
a new immutable version, `<name>@<n>`. Applying the same definition again
creates nothing.

**Verify:** the view's card shows a new materialization with its entity count,
and the history lists the run:

```bash
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/features/customer_profile/versions"
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/features/customer_profile/lineage"
```

The lineage lists each run's `run_id`, `source_dataset`, `offline_uri`,
`entity_count`, `status` and `error`, linked to the view version it materialized.

## Build a training set without leakage

`point_in_time_join` builds a training set from labels and historical feature
rows. For each label, it takes the latest feature row for the entity at or before
the label's `event_timestamp` (ties go to the later `created_timestamp`), and
treats rows older than `ttl_seconds` as missing, as online serving does.

```python
from features.point_in_time import point_in_time_join

training = point_in_time_join(
    labels, feature_rows,
    entity_key="user_id", features=["plan", "spend"], ttl_seconds=3600,
)
```

The `features` module is installed in the Jupyter workbench.

**Verify:** no row in `training` uses a feature value timestamped after its
label.

## Expire stale online rows

The feature gateway writes online rows without an expiry. Run the retention
sweep after each materialization so that rows that stop being refreshed disappear
within one TTL.

1. Preview the changes:

    ```bash
    REDIS_URL=redis://redis:6379 python -m features.retention --dry-run
    ```

2. Apply them:

    ```bash
    REDIS_URL=redis://redis:6379 python -m features.retention
    ```

The sweep sets an expiry of `ttl_seconds` on every key of a view that has a TTL,
deletes keys of views that no longer exist, and leaves views without a TTL alone.

**Verify:** the command prints `feature retention sweep: scanned=... expiry_set=...
deleted=... untouched=...` with a line per view.

## Monitor the feature gateway

The feature gateway exposes `/healthz`, which returns `503` when Redis (or Feast,
when it serves from Feast) is unreachable, and Prometheus metrics at `/metrics`:

| Metric | Labels |
| --- | --- |
| `kionga_feature_gateway_lookups_total` | `mode`, `outcome` (`ok`, `invalid_request`, `failed`) |
| `kionga_feature_gateway_lookup_entities_total` | `mode` |
| `kionga_feature_gateway_lookup_entities_missing_total` | `mode` |
| `kionga_feature_gateway_lookup_duration_seconds` | `mode` |
| `kionga_feature_gateway_writes_total` | `mode`, `outcome` (`ok`, `unauthorized`, `invalid_request`, `unsupported`) |
| `kionga_feature_gateway_health_checks_total` | `mode`, `outcome` |

An administrator can check the built-in store from the console: open
**Platform**, find `kionga-internal` under **Feature stores and object
storage**, and click **Test**. The result appears as a health message, such as
`Healthy: ...`.

## Next steps

- [Connect an external feature store](feature-stores.md).
- [Process real-time events](realtime.md) with online features.
- [Build an agent](agents.md) that looks up features.
