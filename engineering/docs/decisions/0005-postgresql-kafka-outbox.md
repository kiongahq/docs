---
description: Keep control-plane state in PostgreSQL and publish audit and lifecycle events to Kafka through a transactional outbox.
status: "accepted"
date: 2026-06-28
---

# 0005 PostgreSQL as the system of record, Kafka through a transactional outbox

## Context and problem statement

Every control-plane mutation (create a project, submit a run, promote a model, deploy
an agent, change a grant) must be stored, audited and, on Kubernetes, turned into a
command that workers reconcile. If the stored change and the event can diverge, the
system either reconciles something that was never stored or silently skips something
that was. How should the gateway persist state and emit events?

## Decision drivers

- Truthful state: no event without a stored change, no change without its audit
  record.
- Survive a Kafka outage without losing events or blocking reads.
- Several gateway replicas behind one database.
- Tenant isolation in the database itself.
- A lightweight mode for development and tests.

## Considered options

- PostgreSQL with a transactional outbox published to Kafka
- Write to PostgreSQL, then publish to Kafka in the request (dual write)
- A local JSON file store

## Decision outcome

Chosen option: **PostgreSQL with a transactional outbox published to Kafka**, because
it is the only option where the change, its audit event and its outbound events commit
or roll back together.

In one transaction, `writeTx` in `platform/go/internal/store/postgres.go` upserts the
resource in `platform_resources`, inserts the audit event, inserts an outbox row for
`mlaiops.audit.operations`, and for lifecycle actions inserts a command row for the
matching `mlaiops.<kind>.commands` topic. The outbox worker
(`platform/go/internal/store/outbox.go`) publishes pending rows through the Kafka REST
proxy every second and marks them published.

### Consequences

- Good, because a crash between the change and the publish cannot lose the event; the
  row stays pending until it is published.
- Good, because a Kafka outage delays events but does not fail writes.
- Good, because row-level security on `tenant_id` applies to resources, audit events
  and the outbox alike.
- Bad, because delivery is at least once, so every consumer must be idempotent. The
  integration worker is: it commits Kafka offsets only after a whole batch reconciles,
  and dispatch is an ID-keyed create-or-update.
- Bad, because the outbox needs its own operational care: failed rows are retried
  without a limit, and several replicas can publish the same row
  ([risk R6](../architecture/11-risks-and-technical-debt.md#risks)).
- Neutral, because the local JSON file store remains for development and tests. It has
  no outbox and no row-level security.

### Confirmation

`TestPostgresPersistsResourceAuditAndOutboxAtomically` in
`platform/go/integration/postgres_integration_test.go` runs against a real PostgreSQL
in CI (`go test -tags=integration ./integration`) and locally with
`make -C platform test-integration`. `TestLifecycleActionsRouteToDedicatedTopics`
checks the topic routing.

## Pros and cons of the options

### Transactional outbox

- Good, because atomicity comes from one database transaction.
- Good, because the publisher can retry independently of the request.
- Bad, because events are delayed by up to the polling interval.

### Dual write

- Good, because events leave immediately.
- Bad, because a crash or a Kafka error after the commit loses the event, and a
  publish before the commit can announce a change that then rolls back.

### Local JSON file store

- Good, because it needs no database.
- Bad, because it has no transactions across concurrent writers, no outbox and no
  tenant isolation.

## More information

Written after the fact. The PostgreSQL repository, the first migration (with the
`outbox_events` table and row-level security) and the outbox worker were added together
in `platform` commit `19f9b61` (2026-06-28). The file store predates it and is kept for
development. The dual-write option is not recorded in the history; it is listed as the
usual alternative. Details are in
[persistence and the Kafka outbox](../architecture/08-crosscutting-concepts.md#persistence-and-the-kafka-outbox).
