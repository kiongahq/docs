---
description: The Compose public overlay is a legacy demo path that exposes the local development stack through Caddy; use the single-server or Kubernetes deployment instead.
---

# Compose public overlay (legacy)

!!! warning "Legacy path, not supported for production"
    The Compose public overlay runs the local development stack on a public
    server. It builds from source, keeps its secrets in `deploy/.env` and runs
    every data service with local defaults. To host Kionga for other people,
    use the [single-server deployment](operations/public-vm.md) or
    [Deploy on Kubernetes](operations/managed-kubernetes.md). See
    [Choose a deployment](operations/index.md) to compare them.

The overlay adds two things to the local stack in `deploy/compose.yaml`: a Caddy
TLS edge with automatic Let's Encrypt certificates, and Dex served at
`https://<domain>/dex` for single sign-on. Only Caddy publishes ports (80 and
443). Caddy routes `/dex/*` to Dex, `/langfuse/*` to the Langfuse UI and
everything else to the gateway.

`make -C deploy public-up` no longer starts this overlay: it runs the
single-server installer. The overlay starts only when you set
`KIONGA_LEGACY_PUBLIC_DEPLOY=1`, and the script prints a warning that it is not
the supported production path.

## If you already run the overlay

The overlay reads `deploy/.env`. The start script refuses to run until
`MLAIOPS_DOMAIN`, `MLAIOPS_ACME_EMAIL`, `DEX_CLIENT_SECRET`, `DEX_ADMIN_EMAIL`,
`DEX_ADMIN_PASSWORD_HASH` and `MLAIOPS_INTERNAL_TOKEN` are set, and Compose
also requires `MLAIOPS_LOCAL_PASSWORD` (the break-glass `admin` password).

| Task | Command |
| --- | --- |
| Start or update after `make -C deploy workspace-pull` | `KIONGA_LEGACY_PUBLIC_DEPLOY=1 bash deploy/public-up.sh` |
| Follow the gateway logs | `docker compose -f deploy/compose.yaml -f deploy/compose.public.yaml logs -f gateway` |
| Stop (volumes are kept) | `docker compose -f deploy/compose.yaml -f deploy/compose.public.yaml down` |

Durable state is in the `postgres-data` and `objectstore-data` volumes. Back
them up before you change anything, as described in
[Back up local data](operations/local.md#back-up-local-data).

## Move to a supported deployment

1. Choose the [single-server deployment](operations/public-vm.md) for one host,
   or [Kubernetes](operations/managed-kubernetes.md) for teams that need
   workspaces.
2. Provide the infrastructure the overlay bundled: an OIDC identity provider
   with an HTTPS issuer, PostgreSQL with TLS, and any ML engines your users
   need.
3. Plan how to move the data you want to keep. There is no automated
   migration from the overlay's PostgreSQL and object store volumes.
4. Follow the new deployment's guide, then stop the overlay.

## OpenFaaS functions on a VM (faasd)

Connecting faasd is described in
[Run locally: Connect OpenFaaS functions](operations/local.md#connect-openfaas-functions).
