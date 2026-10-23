---
description: Publish every port of the local Compose stack on 127.0.0.1 by default, widened only through KIONGA_BIND_ADDRESS.
status: "accepted"
date: 2026-10-21
---

# 0008 Bind local published ports to loopback by default

## Context and problem statement

The local stack publishes PostgreSQL, Redis, Kafka, the object store, MLflow, Langfuse,
the gateway and other services, all with development credentials that are visible in
`deploy/compose.yaml`. Every port was bound to `0.0.0.0`, so anyone on the same network
as a developer machine could reach them. Which address should local ports bind to?

## Decision drivers

- Development credentials must not be reachable from the network by default.
- Some setups need access from another machine (a VM, a remote browser), so widening
  must remain possible.
- Services that must never be shared stay private even when widened.
- The server deployment is not affected; it exposes only Caddy.

## Considered options

- Bind to `KIONGA_BIND_ADDRESS`, default `127.0.0.1`
- Bind every port to `0.0.0.0` (the previous behavior)
- Publish no ports and reach services only through the gateway

## Decision outcome

Chosen option: **Bind to `KIONGA_BIND_ADDRESS`, default `127.0.0.1`**, because it closes
the exposure by default and keeps direct tool access (database clients, the MLflow and
RustFS consoles) on the developer's own machine.

### Consequences

- Good, because a default local stack is unreachable from the network.
- Good, because Jupyter, the log exporter and the log-export test targets stay pinned to
  loopback even when the bind address is widened.
- Neutral, because a developer who needs remote access sets `KIONGA_BIND_ADDRESS` in
  `deploy/.env` and accepts the exposure of development credentials.
- Neutral, because `local-up` probes the bind address, not `0.0.0.0`, when it checks
  for busy ports, so a native PostgreSQL or Redis on `127.0.0.1` is detected.

### Confirmation

`deploy/tests/test_network_exposure.py` fails if a published port has no bind address,
if the default is not loopback, or if widening the address would expose a pinned
service. It fails against the earlier `compose.yaml`.

## Pros and cons of the options

### `KIONGA_BIND_ADDRESS`, default loopback

- Good, because it is safe by default and still configurable.

### All interfaces

- Bad, because every development credential is reachable from the local network.

### No published ports

- Good, because it removes the exposure entirely.
- Bad, because developers lose direct access to databases and engine consoles that the
  local workflow relies on.

## More information

Written after the fact from `deploy` commit `4231cbd` (2026-10-21), whose message
records the problem, the change and the test. The port-probe change is `deploy`
commit `9207db2` (2026-10-21). The no-published-ports option is not recorded in the
history; it is listed as the strict alternative.
