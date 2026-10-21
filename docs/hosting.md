# Public hosting

Kionga supports two deployment packages without using repository `.env` files
as the production secret source. Managed Kubernetes is the primary team deployment.

| Path | Intended use | Included |
| --- | --- | --- |
| [Managed Kubernetes](operations/managed-kubernetes.md) | Distributed teams and workload provisioning | Replicated control plane, operator, integration worker, service gateways, namespace isolation, External Secrets integration |
| [Public VM](operations/public-vm.md) | Pilot or gateway in front of existing infrastructure | Digest-pinned gateway and Caddy TLS edge; external identity and database |

Neither package creates your cloud account infrastructure, databases, identity
provider, ML engines, or secret manager. The VM package does not provision
Kubernetes workloads. Kubernetes packaging is locally tested, not a certification
that a particular cloud installation is secure or highly available.

Read the [production operations and acceptance checklist](operations/production-operations.md)
before exposing either path to users. Public same-origin notebook and IDE proxying
is disabled in production by default. Managed Kubernetes can route isolated
workspace subdomains with single-use handoff tickets and host-only sessions;
wildcard DNS, TLS and real cluster acceptance are required.

## Configuration model

Version non-secret JSON or Helm values in Git. Keep credentials in a cloud secret
manager and mount them as files. The Go services read `KIONGA_CONFIG_FILE` and
supported `NAME_FILE` inputs at startup. Explicit environment variables override
JSON, but supplying both a nonempty secret environment variable and its file fails.
Secrets are not accepted in the JSON config. Production gateway startup requires
HTTPS OIDC, a matching callback, PostgreSQL with `sslmode=verify-full`, a strong
internal token, and a 32-byte base64 credential encryption key.

## Development compatibility

`make -C deploy local-up` remains the development environment. New public deployment uses
`make -C deploy public-up DEPLOYMENT=/etc/kionga/deployment.json`. The old Compose overlay
is available only through `KIONGA_LEGACY_PUBLIC_DEPLOY=1 bash deploy/public-up.sh`;
it is a legacy demo path, not the recommended production deployment. Do not
expose its development credentials or services to the Internet.

## Legacy demo overlay

The overlay is the local Compose stack plus a Caddy TLS edge (automatic Let's
Encrypt) and Dex for OIDC login. Only Caddy publishes ports; every other service
stays on the internal network.

```text
Internet ──► Caddy (443, automatic TLS)
              ├── /dex/*       ──► Dex (OIDC login)
              ├── /langfuse/*  ──► Langfuse UI
              └── /*           ──► gateway (console + API, JWT enforced)
```

It needs a Linux VM with Docker Engine and the Compose plugin (4 vCPU / 8 GB RAM
minimum, 8 / 16 recommended, 35 GB free Docker storage for the cold build), a DNS
A record pointing at the VM, and ports 80 and 443 open.

1. Clone the workspace on the VM (it builds from source) and create the
   environment file:

    ```bash
    mkdir ~/kionga && cd ~/kionga
    git clone https://github.com/kiongahq/deploy.git
    KIONGA_GIT_BASE=https://github.com/kiongahq/ make -C deploy workspace
    cp deploy/.env.example deploy/.env
    ```

2. Fill in `deploy/.env` (the script refuses to start until the first seven are set):
    - `MLAIOPS_DOMAIN`, `MLAIOPS_ACME_EMAIL`: your DNS name and ACME contact.
    - `DEX_CLIENT_SECRET`, `MLAIOPS_INTERNAL_TOKEN`: `openssl rand -hex 24` each.
    - `MLAIOPS_LOCAL_PASSWORD`: a long random break-glass password for the local
      `admin` account.
    - `DEX_ADMIN_EMAIL` and `DEX_ADMIN_PASSWORD_HASH`, a bcrypt hash:

        ```bash
        docker run --rm httpd:2.4-alpine htpasswd -bnBC 10 "" 'your-password' | tr -d ':\n'
        ```

    - An LLM provider (`MLAIOPS_LLM_BACKEND=openai` or `anthropic` plus its key), or
      leave `mock`.
    - Fresh `LANGFUSE_*` keys and secrets; the defaults are for local development.

3. Start it: `KIONGA_LEGACY_PUBLIC_DEPLOY=1 bash deploy/public-up.sh`. It validates
   the configuration, builds the images, starts the stack, creates Kafka topics
   and waits for the gateway. Open `https://<your-domain>` and sign in through Dex
   with the admin user from `.env`.

Day two: update with `make -C deploy workspace-pull` and the same start command
(Compose recreates changed services); stop with
`docker compose -f deploy/compose.yaml -f deploy/compose.public.yaml down` (volumes
persist); follow logs with the same files and `logs -f gateway`. All durable state
is in the `postgres-data` and `objectstore-data` volumes, so snapshot those.

## OpenFaaS functions on a VM (faasd)

Functions are optional. On a single VM, install faasd on the host (its supported
single-node mode), not in Compose. These commands need sudo:

```bash
git clone https://github.com/openfaas/faasd --depth=1 && cd faasd
sudo ./hack/install.sh
sudo cat /var/lib/faasd/secrets/basic-auth-password
```

Then point the gateway at it and restart the gateway:

```text
OPENFAAS_URL=http://<vm-private-ip>:8080
OPENFAAS_USER=admin
OPENFAAS_PASSWORD=<the printed password>
```

The console's Functions view then lists project-owned functions, and
`POST /api/v1/functions` deploys OCI images with limits and trigger annotations.
Connector deployment and scale-to-zero stay in OpenFaaS's own configuration.
