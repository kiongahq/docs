# Local operations

Day-to-day commands for running, verifying, and inspecting the local stack.

## Lifecycle

```bash
make local-up       # build + start everything, create Kafka topics
make local-down     # stop (named volumes persist)
```

Restarting is idempotent — `make local-up` reconciles to the desired state and only
rebuilds changed images. Durable state survives in the `postgres-data`,
`minio-data`, `redis-data`, `prefect-data`, and `jupyter-data` volumes.

## Status & health

```bash
docker compose -f deploy/compose.yaml ps                    # per-service state
curl -s http://localhost:8080/api/v1/health                 # gateway
curl -s http://localhost:8080/api/v1/components | python -m json.tool   # component grid
```

## Logs

```bash
docker compose -f deploy/compose.yaml logs -f gateway
docker compose -f deploy/compose.yaml logs -f realtime-processor
docker compose -f deploy/compose.yaml logs --tail 100 serving-manager
```

## Rebuilding one service

After editing code for a single service:

```bash
docker compose -f deploy/compose.yaml up -d --build gateway
```

The console (HTML/JS/CSS) is embedded in the gateway binary, so console changes need
a gateway rebuild.

## Re-running one-shot jobs

```bash
docker compose -f deploy/compose.yaml up feature-materializer   # re-materialize features
docker compose -f deploy/compose.yaml up minio-init             # ensure buckets
```

## Verifying the whole platform

```bash
./scripts/demo-smoke.sh          # 18-point end-to-end check against the running stack
make verify                      # gate suite (Go+Python tests, lint, build, banned-tech)
make test-integration            # Postgres outbox + pgvector round-trip
```

The demo smoke expects `18 passed, 0 failed, 1 skipped` (the skip is OpenFaaS).

## Changing ports

Every published port has a `*_PORT` override. Put them in `.env` (or export them),
then `make local-up`. Example — move the console off 8080:

```bash
echo "GATEWAY_PORT=8090" >> .env
make local-up
```

## Switching your local role

Preview the console as a non-admin without OIDC:

```bash
MLAIOPS_LOCAL_ROLE=viewer docker compose -f deploy/compose.yaml up -d gateway
# ... then restore:
docker compose -f deploy/compose.yaml up -d gateway
```

## Data & backups

All durable state is in Postgres (control plane, MLflow, Langfuse, checkpoints) and
MinIO (artifacts). To back up locally, snapshot those two volumes:

```bash
docker run --rm -v mlaiops_postgres-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres-data.tgz -C /data .
docker run --rm -v mlaiops_minio-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/minio-data.tgz -C /data .
```

## Resetting

To wipe all state and start clean (destructive):

```bash
docker compose -f deploy/compose.yaml down -v   # -v removes the named volumes
make local-up
```

## Building the docs site

```bash
make docs-install     # once
make docs-serve       # live preview at http://localhost:8000
make docs-build       # strict static build into site/
```
