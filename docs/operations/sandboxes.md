---
icon: material/shield-lock-outline
description: Install and verify gVisor for agent team sandboxes on a Linux host or Kubernetes nodes, configure the image allowlist, and fix sandboxes that report as unavailable.
---

# Sandboxes and gVisor

Agent team sandboxes run under gVisor (`runsc`). If gVisor is not available, Kionga
refuses to create sandboxes and sandbox tools report `sandbox_unavailable`. It never
falls back to another runtime. Teams that do not use sandboxes are unaffected.

To learn what this protects, see
[What a sandbox protects](../guides/agent-teams.md#what-a-sandbox-protects).

| Deployment | Sandboxes |
| --- | --- |
| Single server | Off until you enable them in `deployment.json`. gVisor is required, and the installer starts nothing without it. |
| Kubernetes | Off until you set `sandbox.enabled`, and gVisor is required |
| Local, without gVisor (the default on macOS and Windows) | Reported as unavailable |
| Local, on Linux with gVisor | Available once you set the image allowlist |
| Compose public overlay (legacy) | gVisor is required, and `public-up.sh` stops without it |

## Install gVisor on a Linux host

This step is optional and changes the host. Kionga never runs it for you.

```bash
sudo make -C deploy sandbox-runtime-install
```

The target downloads gVisor's release archive, checks it against a SHA-512 pinned for
your architecture, installs `runsc`, its `containerd` shim and the `gvisor-bin/` directory
to `/usr/local/bin`, registers the runtime with Docker, and reloads Docker.

To use Podman, or to install another way, follow the
[gVisor installation guide](https://gvisor.dev/docs/user_guide/install/) and keep
`gvisor-bin/` next to `runsc`. For Podman, add `runsc` under `[engine.runtimes]` in
`containers.conf`.

## Verify the runtime

```bash
make -C deploy sandbox-runtime-verify
```

The target starts a container with no network under `runsc` and reads its kernel release,
which contains `gvisor`. Success prints `A container ran under gVisor.` Do not rely on the engine's list of runtimes:
Podman lists `runsc` even when it is not installed.

The probe image is pinned by digest. If the host has no network, the pull stops after 120
seconds with a message. Load the image from another machine with `docker save` and
`docker load`, then run the check again.

The sandbox manager makes the same kind of check. At startup and before each create, it
confirms the runtime and that a probe reports gVisor's kernel.

## Enable sandboxes on a single server

The single-server installer adds agent teams and sandboxes when your deployment file enables
them. With the settings off, it runs only the gateway and Caddy.

1. Install gVisor on the server, then verify it, as described in
   [Install gVisor on a Linux host](#install-gvisor-on-a-linux-host).
2. Add these secret files to `secrets_directory`, with the same ownership and mode as
   the other secret files. See [Deploy on a single server](public-vm.md).

    | File | Value |
    | --- | --- |
    | `KIONGA_DESIGNER_RUNNER_TOKEN` | At least 32 characters. Generate it with `openssl rand -hex 24`. |
    | `TRACE_PROXY_PROJECT_KEY` | At least 32 characters. Generate it with `openssl rand -hex 24`. |
    | `TRACE_PROXY_KEYS` | JSON list holding the SHA-256 hash of that project key. |
    | `LLM_UPSTREAM_API_KEY` | Your model provider's API key. |
    | `KIONGA_SANDBOX_TOKEN` | At least 32 characters. Generate it with `openssl rand -hex 24`. |

3. Add this block to `/etc/kionga/deployment.json`, with digests from your release:

    ```json
    "agent_teams": {
      "enabled": true,
      "agent_runtime_image": "ghcr.io/kiongahq/agent-runtime@sha256:<digest>",
      "trace_proxy_image": "ghcr.io/kiongahq/trace-proxy@sha256:<digest>",
      "llm_upstream_url": "https://api.openai.com",
      "llm_model": "<model>",
      "sandbox": {
        "enabled": true,
        "manager_image": "ghcr.io/kiongahq/sandbox-manager@sha256:<digest>",
        "images": ["ghcr.io/kiongahq/sandbox@sha256:<digest>"],
        "git_hosts": ["github.com"]
      }
    }
    ```

    To run teams without code sandboxes, leave `sandbox.enabled` false.

4. Run the installer again:

    ```bash
    make -C deploy public-up DEPLOYMENT=/etc/kionga/deployment.json
    ```

The installer checks these settings before it starts anything. It rejects images that are not
pinned by digest, short tokens, development values, and any setting it does not recognize. Before
it pulls images, it starts a probe container, and it stops unless that container runs under gVisor.

The runtime, production mode and the empty unsafe flag are fixed values in the installer's
Compose files, so no setting can change them. Caddy stays the only public listener. The runner,
trace proxy and sandbox manager share internal networks with the gateway and publish no ports.
The trace proxy has a route out, to your model provider. If you set `git_hosts`, the sandbox
manager also joins a network of its own, because it resolves those hosts itself and internal
networks have no external DNS.

To tune teams, add a `tuning` block to `agent_teams`. See the
[configuration reference](../reference/configuration.md#agent-teams). These settings cannot go
in `config.json`, which refuses names that contain `TOKEN` or `SECRET`.

On this path, model calls are not sent to a trace store, because the package has no Kafka or
Langfuse. The sandbox manager's engine access is equivalent to root on the server.

## Set the image allowlist

Sandboxes use only images listed in `KIONGA_SANDBOX_IMAGES`. While the list is empty, the
manager stays up and creates return 503. Entries are comma-separated, each as
`repository@sha256:digest`.

The base image has git, Python, Node and build tools. To build it locally:

```bash
docker build -t kionga-sandbox -f platform/deploy/sandbox/Dockerfile platform
docker image inspect --format '{{.Id}}' kionga-sandbox
```

On the local stack only, you can list the resulting `sha256:` image ID. Add it to
`deploy/.env` and run `make -C deploy local-up`:

```bash
KIONGA_SANDBOX_IMAGES=sha256:<image-id>
```

To let agents use git, also set `KIONGA_SANDBOX_GIT_HOSTS`, for example to `github.com`.
Git uses HTTPS only. With an empty list, git tools are refused.

The credential for a git grant comes from an API connection, so its reference must be
`env:KIONGA_CONNECTION_SECRET_<NAME>` or an allowlisted name. See
[Secret references](../reference/configuration.md#secret-references).

## Compose public overlay (legacy)

The [single-server installer](#enable-sandboxes-on-a-single-server) is the supported path. If
you still use the legacy overlay, set these values in `.env`:

| Variable | Rule |
| --- | --- |
| `KIONGA_SANDBOX_TOKEN` | Required, at least 32 characters. Generate it with `openssl rand -hex 24`. |
| `KIONGA_SANDBOX_IMAGES` | Required. Every entry must be pinned by digest. |
| `KIONGA_SANDBOX_GIT_HOSTS` | Optional. |

The overlay sets the runtime to `runsc` and production mode as fixed values. The preflight
refuses to start if `.env` sets `KIONGA_SANDBOX_ALLOW_UNSAFE_RUNTIME` or another
`KIONGA_SANDBOX_RUNTIME`. `public-up.sh` also starts a probe container and stops unless it
runs under gVisor. If you start the overlay directly with Compose, that probe does not run.
The manager still refuses to create sandboxes without gVisor.

## Kubernetes

1. Install gVisor on the nodes that run sandboxes and create its RuntimeClass, or set
   `sandbox.createRuntimeClass: true`. On GKE, use GKE Sandbox.
2. Create the Secret named by `sandbox.secretName` with key `KIONGA_SANDBOX_TOKEN`. The
   gateway and the manager both read it.
3. Set the chart values:

    ```yaml
    sandbox:
      enabled: true
      image: ghcr.io/kiongahq/sandbox-manager@sha256:<digest>
      runtimeClassName: gvisor
      images:
        - ghcr.io/kiongahq/sandbox@sha256:<digest>
      gitHosts: [github.com]
      kubernetesApiCidrs: [<api-server-address>/32]
    ```

4. List every API server address in `kubernetesApiCidrs`, including the `kubernetes` Service
   address and any public endpoint. The manager is allowed to reach them, and git helpers
   are denied them.
5. If your pod, Service or node ranges fall outside the private ranges, list them in
   `sandbox.internalCidrs`.

The chart runs sandboxes in their own namespace, `kionga-sandboxes` by default, with a
default-deny NetworkPolicy. Git helper pods can reach only HTTPS on public addresses. They need
no DNS, because the manager resolves each host and pins its addresses. The manager pod can reach
DNS only when `gitHosts` is set. The private ranges and the `169.254.0.0/16` metadata range are always excluded. These rules
depend on a network plugin that enforces NetworkPolicy, so confirm that yours does.

The manager's write access stops at the sandbox namespace. Outside it, the manager can read
only the one named RuntimeClass. The chart has no setting for the unsafe runtime.

## When sandboxes are unavailable

Look for the banner in the run view, then read the manager's state.

```bash
# Single server
docker compose -p kionga-public logs sandbox-manager

# Local stack
make -C deploy local-logs | grep sandbox-manager

# Kubernetes
kubectl -n kionga-system port-forward svc/kionga-sandbox-manager 8088:8088
curl http://localhost:8088/healthz
```

`/healthz` reports `runtime`, `runtime_verified` and `driver`. `runtime_verified: false`
means creates return 503.

| Symptom | Cause | What to do |
| --- | --- | --- |
| `runtime_verified` is false | gVisor is missing or not registered | Install it, run `make -C deploy sandbox-runtime-verify`, then restart `sandbox-manager`. |
| Verify says the kernel release does not mention gVisor | The name `runsc` points to another runtime | Fix the engine's runtime configuration. |
| Verify says the Podman client cannot choose a runtime | The Podman client on macOS and Windows has no runtime flag | Run the check on the Linux host. |
| Creates return 503 and the runtime is verified | `KIONGA_SANDBOX_IMAGES` is empty | Set the allowlist. |
| The manager exits at startup | The token is missing or short, or an image is not pinned | Read the log. Run `make -C deploy local-up` to generate the local token. |
| Git tools refuse a host | The host is not in `KIONGA_SANDBOX_GIT_HOSTS` | Add it. Only HTTPS is supported. |
| The installer or `public-up.sh` stops at the probe | The server has no working gVisor | Install gVisor on the server. |
| The probe says the pull took too long or failed | The server cannot reach the registry | Restore network access, or load the image with `docker load`. |

Workers that hit `sandbox_unavailable` report it to the coordinator. After you fix the cause,
resume the run from the run view.

!!! danger "Do not use the unsafe runtime to fix a production problem"
    Production refuses it, and it removes the isolation that sandboxes rely on.

## Develop without gVisor

On a development machine with no gVisor, you can opt in to a weaker runtime. Add both lines to
`deploy/.env`, then run `make -C deploy local-up`:

```bash
KIONGA_SANDBOX_RUNTIME=runc
KIONGA_SANDBOX_ALLOW_UNSAFE_RUNTIME=1
```

Sandbox code then shares the host kernel, so a kernel exploit escapes the sandbox. Use this only
with code and input you trust. The manager logs a warning on every create, the run view shows a
banner, and the manager refuses the flag when `KIONGA_ENVIRONMENT` is `production`.

## Limits

- **No egress allowlists for sandboxes.** A sandbox has no network at all, and you cannot grant it
  selected hosts.
- **No per-tenant node pools.** All sandboxes in a deployment share hosts or nodes.
- **Git helper egress is not limited to your git hosts.** While it runs, a git helper can reach any
  public IP address on port 443. Only the sandbox manager enforces `KIONGA_SANDBOX_GIT_HOSTS`, by
  refusing to start an operation for another host. The network does not enforce that list. Helpers
  run only your approved image and a fixed script, live for one operation, and hold one credential.
  Scope each git credential to the repositories the team needs. On Kubernetes, private ranges, the
  metadata range and your API server addresses are also denied. On a single server or the local
  stack, helpers use the engine's bridge network, so private addresses are reachable too.

## Check the result

Run `make -C deploy sandbox-runtime-verify`, then start a team run with an agent whose workspace is
**Sandbox**. Its first `exec` call should return output rather than `sandbox_unavailable`.
