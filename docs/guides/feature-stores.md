---
icon: material/database-sync-outline
description: Connect an external feature store such as Feast to Kionga, test its health, share it with projects, and serve online lookups from it through the feature gateway.
---

# Connect an external feature store

Register a feature store you already run, such as a Feast feature server, so
Kionga can check its health and show it to the projects that may use it. For the
store that ships with Kionga, see [Use the built-in feature store](features.md).

Kionga connects external stores through adapters. An adapter defines what Kionga
can drive in that store:

| Provider | Adapter | What Kionga can drive | Health check |
| --- | --- | --- | --- |
| `internal` (built in) | Yes | Online, offline, point-in-time joins, materialization, TTL, push | Redis, or the feature gateway's `/healthz` |
| `feast` | Yes | Online lookups and TTL | Feast `GET /health` |
| `tecton`, `hopsworks`, `vertex-ai`, `sagemaker`, `databricks` | Not yet | Nothing | Listed as a contract without an adapter; you cannot connect them |

## Before you begin

- **To connect, edit, test or remove a store:** the `admin` or `operator` role.
- **To see the stores shared with your projects:** the `features` service for a
  normal user, or the `viewer`, `engineer`, `operator` or `admin` role.
- A running Feast feature server that the Kionga gateway can reach over HTTP or
  HTTPS.
- If Feast needs a bearer token, an operator sets it as an environment variable
  on the gateway, for example `FEAST_TOKEN`. You never paste the secret into
  Kionga.

## Connect a Feast feature server

=== "Console"

    1. Open **Platform**. Under **Feature stores and object storage**, click
       **＋ Feature store**.
    2. Choose the **Provider** and enter a **Connection name** (2 to 63
       lowercase letters, digits and hyphens).
    3. Enter the **Feature server URL**, for example
       `http://feast-feature-server:6566`.
    4. Optional: enter **Feature services** as a comma-separated list. Feast's HTTP
       server cannot list them itself.
    5. Optional: enter a **Credential reference** such as `env:FEAST_TOKEN`.
    6. Enter the **Allowed projects** as comma-separated project IDs. Leave it
       empty to share the store with every project.
    7. Click **Save and test**.

=== "API"

    Use an administrator's session cookie (see
    [Authentication](../reference/api.md#authentication)):

    ```bash
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/admin/feature-stores" \
      -H 'Content-Type: application/json' \
      -d '{"provider": "feast", "name": "team-feast",
           "config": {"url": "http://feast-feature-server:6566",
                      "feature_services": "customer_profile"},
           "secret_ref": "env:FEAST_TOKEN",
           "allowed_projects": ["prj-123"]}'
    curl -s -b kionga.cookies -X POST \
      "$MLAIOPS_URL/api/v1/admin/feature-stores/<store-id>/test"
    ```

Kionga validates the connection before saving it:

- `config` accepts only the provider's keys (`url` and `feature_services` for
  Feast). Keys that look like secrets, and URLs with embedded credentials, are
  rejected.
- `secret_ref` is empty or `env:VARIABLE`. Kionga reads the value only to run a
  check, and never stores, logs or returns it. Responses report only whether the
  secret is present.
- Every project in `allowed_projects` must exist.

**Verify:** the health message reads `Healthy: Feast feature server is serving
at ...`. Other results mean:

| Health | Meaning |
| --- | --- |
| `configured` | Saved but not tested yet. Saving or editing a connection resets it to this state. |
| `degraded` | Feast answered, but took more than 2 seconds or returned an unexpected status |
| `unavailable` | Feast is unreachable, or it rejected the credential (`401` or `403`) |

## Share a store with projects

To change which projects can use a store after you connect it, send the full
connection with the new `allowed_projects` list. The console has no edit form;
there you remove the store and connect it again.

1. Update the connection:

    ```bash
    curl -s -b kionga.cookies -X PUT \
      "$MLAIOPS_URL/api/v1/admin/feature-stores/<store-id>" \
      -H 'Content-Type: application/json' \
      -d '{"provider": "feast", "name": "team-feast",
           "config": {"url": "http://feast-feature-server:6566"},
           "secret_ref": "env:FEAST_TOKEN",
           "allowed_projects": ["prj-123", "prj-456"]}'
    ```

2. Test it again, because saving resets its health to `configured`.

Project members see a store only when it is shared with one of their projects
(or with every project), and they see only their own project IDs on it.

**Verify:** a project member sees the store in **Features > Feature stores**,
or in the response of:

```bash
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/features/stores"
```

## Serve online lookups from Feast

Registering a store records and monitors it. To make Kionga's feature gateway
answer `/get-online-features` from Feast instead of Redis, an operator configures
the feature gateway itself:

1. Set `FEAST_URL` on the `feature-gateway` service to the Feast feature server
   address.
2. Restart the feature gateway.

With `FEAST_URL` set, the gateway forwards every lookup to Feast and its
`/healthz` returns `503` when Feast is unreachable. Its metrics carry the label
`mode="feast"`.

**Verify:** a lookup returns the values that Feast serves:

```bash
curl -s -X POST "$MLAIOPS_FEATURE_GATEWAY_URL/get-online-features" \
  -H 'Content-Type: application/json' \
  -d '{"feature_service": "customer_profile", "entities": [{"entity_id": "u123"}]}'
```

## Remove a store

Click **Remove** on the store under **Feature stores and object storage**, or
call `DELETE /api/v1/admin/feature-stores/<store-id>`. The built-in store, with
the ID `internal`, cannot be edited or removed; its addresses come from
`MLAIOPS_FEATURE_GATEWAY_URL` and `KIONGA_FEATURE_OFFLINE_URI` on the gateway.

## Next steps

- [Use the built-in feature store](features.md) for materialization, versions
  and point-in-time joins.
- [Process real-time events](realtime.md) with online features.
- For how adapters work and how to add one, see the
  [engineering handbook](https://kiongahq.github.io/docs/engineering/components/go-packages/).
