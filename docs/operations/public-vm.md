---
icon: material/server-outline
description: Deploy the Kionga gateway behind Caddy on one Linux server from digest-pinned images, with configuration in JSON and secrets delivered as files.
---

# Deploy on a single server

This guide shows you how to run the Kionga gateway (console and API) on one
Linux server with the single-server installer, `deploy/vm/up.py`. The installer
runs two containers from images pinned by digest: the gateway, and Caddy as the
TLS edge. Your identity provider, PostgreSQL and ML engines run elsewhere.

Use this deployment for a pilot or as a control plane in front of
infrastructure you already operate. It has no workload plane: it cannot
provision notebooks, IDE workspaces or agents, and it has no gateway failover. For those,
see [Deploy on Kubernetes](managed-kubernetes.md).

## Before you begin

**Server**

- A maintained Linux host with Docker Engine, the Docker Compose plugin,
  Python 3 and Git. Make is optional.
- Inbound TCP 80 and 443 open to your users and to Let's Encrypt. Restrict SSH
  to administrators. Expose no other ports.
- Outbound HTTPS to `ghcr.io`, Let's Encrypt and your identity provider, and
  private network access to PostgreSQL and any engines you connect.
- An owner for patching, disk monitoring, backups and recovery.

**DNS**

- A public DNS name (for example `kionga.example.org`) that resolves to the
  server. Caddy requests the certificate for this name on first start.

**Identity provider and database**

- An OIDC identity provider with an HTTPS issuer. Register a client for Kionga
  with the callback `https://<your-domain>/auth/callback`.
- A PostgreSQL database the gateway can reach over TLS with certificate
  verification (`sslmode=verify-full`).

**Access**

- A GitHub account with access to the `ghcr.io/kiongahq` packages and a token
  with only the `read:packages` scope. Use a dedicated machine account.
- `sudo` on the server to create `/etc/kionga` and the secret directory.
- The image digests of the release you are deploying, for the gateway
  (`ghcr.io/kiongahq/gateway@sha256:...`) and for Caddy (`caddy@sha256:...`).

**Secrets**

Four values, delivered as files by your secret manager or configuration
management (never in Git, cloud-init user data, shell history or command
arguments):

| File | Value | Requirement in production |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection URI | `postgres://` or `postgresql://` with `sslmode=verify-full` |
| `OIDC_CLIENT_SECRET` | The identity provider's client secret | At least 24 characters, not a development value |
| `MLAIOPS_INTERNAL_TOKEN` | Shared token for platform services | At least 24 characters, not a development value; generate with `openssl rand -hex 24` |
| `KIONGA_CREDENTIAL_KEY` | Key that encrypts users' stored personal credentials | Base64 encoding of exactly 32 bytes; generate with `openssl rand -base64 32` |

Back up `KIONGA_CREDENTIAL_KEY` with your recovery plan. Replacing it makes
previously stored personal credentials unreadable.

## Steps

1. **Get the deployment files.** The installer needs only the `deploy`
   repository; it never builds from source.

    ```bash
    mkdir ~/kionga && cd ~/kionga
    git clone https://github.com/kiongahq/deploy.git
    ```

    Run the remaining commands from `~/kionga`.

2. **Sign in to the registry.** The `ghcr.io/kiongahq` images are private. As
   the user that runs the installer, sign in once:

    ```bash
    echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
    ```

    Docker stores the credential in `~/.docker/config.json` (or
    `$DOCKER_CONFIG`, which the installer passes through). Rotate the token
    like any other secret.

3. **Write the deployment file.** Copy `deploy/vm/deployment.example.json` to
   `/etc/kionga/deployment.json` and replace every value:

    | Field | Value |
    | --- | --- |
    | `domain` | Your DNS name, without a scheme or port. Example domains are rejected. |
    | `acme_email` | Contact address for Let's Encrypt |
    | `gateway_image` | `ghcr.io/kiongahq/gateway@sha256:<digest>` |
    | `caddy_image` | `caddy@sha256:<digest>` |
    | `config_file` | Path of the application configuration, for example `/etc/kionga/config.json` |
    | `secrets_directory` | Directory that holds the four secret files, for example `/run/kionga/secrets` |

    The installer rejects image references that are not pinned by a SHA-256
    digest.

4. **Write the application configuration.** Copy
   `deploy/vm/config.example.json` to the `config_file` path and set your
   values. Every value must be a JSON string.

    - `MLAIOPS_ALLOWED_ORIGIN`: `https://<your-domain>`. It must match
      `domain`.
    - `OIDC_ISSUER`, `OIDC_JWKS_URL`, `OIDC_AUTH_URL`, `OIDC_TOKEN_URL`: your
      identity provider's HTTPS endpoints.
    - `OIDC_CLIENT_ID` and `OIDC_AUDIENCE`: the client you registered.
    - `OIDC_REDIRECT_URL`: `https://<your-domain>/auth/callback`.
    - Optional engine addresses, such as `MLFLOW_URL`, `PREFECT_API_URL` and
      `KAFKA_REST_URL`.

    Do not put secrets in this file. The gateway refuses to start if a key is
    a secret name, ends in `_FILE`, or contains `PASSWORD`, `SECRET`, `TOKEN`
    (other than `OIDC_TOKEN_URL`) or `API_KEY`.

5. **Deliver the secret files.** Have your secret agent write the four files
   from [Before you begin](#before-you-begin) into `secrets_directory`, one
   value per file, named exactly as in the table. The installer requires each
   file to be non-empty, readable by the deploying user and not
   world-accessible.

    On a standard Docker host that runs as root, make the files owned by root with
    group `65532` (the gateway's user and group), mode `0640`, in a directory
    with mode `0750`:

    ```bash
    sudo chown -R root:65532 /run/kionga/secrets
    sudo chmod 0750 /run/kionga/secrets
    sudo chmod 0640 /run/kionga/secrets/*
    ```

    Rootless Docker or user-namespace remapping needs the matching mapped
    ownership instead. `/run` is cleared at reboot, so configure your secret
    agent to write the files again before Docker starts the containers.

6. **Validate the inputs.**

    ```bash
    python3 deploy/vm/up.py /etc/kionga/deployment.json --validate-only
    ```

    Expected output:

    ```text
    VM deployment inputs and Compose configuration validated
    ```

    Validation checks the deployment file, the configuration origin, the secret
    files and the Compose configuration. It does not check credentials, the
    database or your identity provider.

7. **Start Kionga.**

    ```bash
    make -C deploy public-up DEPLOYMENT=/etc/kionga/deployment.json
    ```

    Without Make, run `bash deploy/public-up.sh /etc/kionga/deployment.json`.
    The installer pulls the pinned images, recreates both containers and polls
    `https://<your-domain>/api/v1/ready` (60 attempts, 3 seconds apart). When
    the gateway answers, it prints:

    ```text
    Kionga is ready at https://<your-domain>
    ```

## Verify

1. Check readiness from outside the server:

    ```bash
    curl -s https://<your-domain>/api/v1/ready   # {"status":"ready"}
    ```

    The gateway reports ready when it can reach PostgreSQL.

2. Open `https://<your-domain>`, sign in through your identity provider and
   sign out again.

3. Check that anonymous API access is denied:

    ```bash
    curl -s -o /dev/null -w '%{http_code}\n' https://<your-domain>/api/v1/projects   # 401
    ```

4. Inspect the containers if something fails:

    ```bash
    docker compose -p kionga-public ps
    docker compose -p kionga-public logs --tail 100 gateway
    ```

Readiness is not acceptance. Before you admit users, complete the
[production readiness checklist](production-operations.md#acceptance-checklist).

## Optional: add a break-glass administrator

By default the server accepts only single sign-on. To keep a local `admin`
account for when the identity provider is unavailable:

1. Add `"KIONGA_LOCAL_LOGIN": "true"` to the application configuration.
2. Deliver the password as a fifth secret file, `MLAIOPS_LOCAL_PASSWORD`. In
   production the gateway refuses to start unless the password has at least
   16 characters and contains none of `local`, `change-me` or `password`.
3. The installer mounts only the four standard secrets. Add the file to the
   gateway's `secrets` list in `deploy/vm/compose.yaml`, with a matching entry
   under the top-level `secrets` key, and set
   `MLAIOPS_LOCAL_PASSWORD_FILE: /run/secrets/MLAIOPS_LOCAL_PASSWORD` in the
   gateway's `environment`.
4. Run the start command again.

Connect optional engines that need credentials (for example `MLFLOW_TOKEN` or
`KAFKA_REST_TOKEN`) the same way: mount the secret file and set the matching
`NAME_FILE` variable.

## Upgrade and roll back

**Upgrade.** Replace the image digests in `deployment.json` with the reviewed
digests of the new release, then run the start command again. The installer
always recreates the containers, so it also picks up replaced secret files.
Expect a short outage: there is one gateway.

**Rotate secrets.** Have your secret agent write the new file contents, then
run the start command again. The gateway reads secret files only at startup.
When you rotate `MLAIOPS_INTERNAL_TOKEN`, update every service that uses it at
the same time.

**Roll back.** Restore the previous digests and configuration, then run the
start command again. Rollback does not undo database migrations or restore
earlier secret values. Back up PostgreSQL before every upgrade.

**Stop.** Stop the containers without deleting the certificate volumes:

```bash
make -C deploy public-down DEPLOYMENT=/etc/kionga/deployment.json
```

`python3 deploy/vm/up.py /etc/kionga/deployment.json --stop` does the same.
Never use `docker compose down -v` to upgrade or troubleshoot: it deletes
Caddy's certificate data.

## Next steps

- [Production readiness](production-operations.md): monitoring, backups and the
  acceptance checklist.
- [Single sign-on](single-sign-on.md): map identity provider groups to Kionga
  roles.
- [Troubleshooting](troubleshooting.md#single-server): installer and gateway
  startup errors.
- [Deploy on Kubernetes](managed-kubernetes.md) when you need notebooks, IDE
  workspaces or agents.

Related: [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
[Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
