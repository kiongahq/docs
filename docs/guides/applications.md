---
icon: material/application-braces-outline
description: Deploy your own software on Kubernetes at a name under your Kionga domain, from an image or a public Git repository, with environment, secrets, health checks, visibility, scaling, logs and redeploys.
---

# Deploy applications

An application is software you wrote, run by Kionga on Kubernetes and served at
`<name>.<your Kionga domain>`. For example, with the application domain
`kionga.company-x.net`, an application named `billing` is served at
`https://billing.kionga.company-x.net`. Kionga builds it if you give a Git
repository, keeps it running, restarts it when it fails and scales it with load.

Applications need a Kubernetes install. A Compose or single-server install
answers every applications request with `409 not_configured` and the steps to
enable it; see [Turn applications on](#enable).

!!! info "Available in a later release"
    The operator and the gateway that run applications ship in platform v0.2.1.
    These parts are not in a released version yet:

    - **Chart wiring.** The Helm chart in deploy v0.2.0 does not install the
      application resources or set the operator and gateway variables. Until a
      later chart release, an administrator applies the resource definitions
      and sets the variables listed in [Turn applications on](#enable).
    - **Gateway and operator alignment.** Redeploy, the `internal` visibility,
      sign-in for `sso` applications on their own host and the secret label
      check are being aligned between the gateway and the operator. This guide
      describes the aligned behavior. Where a step needs the fix, it says so.
    - **Live log following in the CLI.** `kionga apps logs --follow` arrives in a
      later SDK release. The API already streams logs; see
      [Read logs and events](#logs).

## Before you begin

- You need the `applications` service for a normal user, or the `engineer`,
  `operator` or `admin` role, and access to the project. Viewers can list and
  read applications but cannot change them.
- The install runs on Kubernetes with applications turned on and a wildcard DNS
  record for the application domain. An administrator sets this up; see
  [Turn applications on](#enable) and
  [Kubernetes prerequisites](../operations/kubernetes-prerequisites.md).
- Your container image serves HTTP on one port, runs as a non-root user with a
  numeric user ID, and answers its [health check](#health-check).
- For the CLI and Python client, install the SDK (`pip install kionga`, version
  0.3.2 or later), then set `KIONGA_URL` to your gateway address and
  `KIONGA_TOKEN` to a personal API key.

## Deploy an application

Pick a name, a project, and either an image or a Git repository.

=== "CLI"

    ```bash
    kionga apps deploy billing --project prj-123 \
      --image ghcr.io/acme/billing:1.4 --port 8080 \
      --health-path /healthz --wait
    ```

    `--wait` blocks until the application is ready or fails, then prints its
    status and URL. Without it, the command returns as soon as Kionga accepts the
    request.

=== "Python"

    ```python
    from kionga import KiongaClient

    client = KiongaClient()
    app = client.create_application(
        "prj-123", "billing",
        image="ghcr.io/acme/billing:1.4",
        port=8080,
        health_path="/healthz",
    )
    app = client.wait_until_ready("billing", generation=app.generation)
    print(app.status.url)
    ```

=== "API"

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/applications" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"project_id": "prj-123", "name": "billing",
           "image": "ghcr.io/acme/billing:1.4", "port": 8080,
           "health_path": "/healthz"}'
    ```

**Verify:** `kionga apps get billing` shows the phase `ready` and the URL
`https://billing.<your domain>`. The first deploy can take a few minutes while the
cluster pulls the image or builds the source.

Kionga records the application only after Kubernetes accepts it, so a refused
deploy returns an error and leaves no record.

### Deploy from a Git repository

Give a public HTTPS Git URL instead of an image, and Kionga builds it with a
rootless BuildKit job from your Dockerfile, pushes the image to the installation's
registry, and runs it.

=== "CLI"

    ```bash
    kionga apps deploy billing --project prj-123 \
      --git https://github.com/acme/billing --ref main \
      --context-dir services/billing --dockerfile Dockerfile --wait
    ```

=== "Python"

    ```python
    app = client.create_application(
        "prj-123", "billing",
        source={"git": "https://github.com/acme/billing", "ref": "main",
                "context_dir": "services/billing"},
    )
    ```

=== "API"

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/applications" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"project_id": "prj-123", "name": "billing",
           "source": {"git": "https://github.com/acme/billing", "ref": "main",
                      "context_dir": "services/billing"}}'
    ```

Rules for sources:

- The repository must be public and the URL must use `https://` with no
  credentials. Builds carry no Git credentials, so a private repository can't be
  cloned. Build and push the image yourself and deploy it by image instead.
- `ref` is a branch, tag or commit, and defaults to `main`. `dockerfile`
  defaults to `Dockerfile`, and `context_dir` to the repository root.
- Set an image or a source, not both.
- The install needs a build registry. Without one, an application with a source
  fails with the reason `BuildNotConfigured`. Image deployments still work.
- A build has a one hour limit and 2 CPUs and 4 GiB of memory at most.
- The phase is `Building` until the first build succeeds. If a later build fails,
  Kionga keeps serving the previous image and shows the failure in the
  application's last build.
- A build runs once for each combination of repository, ref, directory,
  Dockerfile and redeploy request. A branch that moves does not rebuild by
  itself. [Redeploy](#redeploy) to build the new commit.

## Settings

| Setting | Default | Notes |
| --- | --- | --- |
| `name` | none | Required. A lowercase DNS label that starts with a letter, up to 45 characters. It becomes the first part of the host name and can't change. Names the platform uses (such as `api`, `auth`, `console`, `www`) and names starting with `workbench-`, `ide-`, `langflow-` or `kionga-` are reserved. |
| `project_id` | none | Required for a normal user. The application belongs to the project and can't move. |
| `image` or `source` | none | Exactly one. |
| `port` | `8080` | The container port that serves HTTP. Kionga also sets the `PORT` variable to this value unless you set `PORT` yourself. |
| `env` | none | Up to 100 plain variables. Names can't start with `KIONGA_`. |
| `secret_refs` | none | Names of [Kubernetes Secrets](#secrets) to load as environment variables. |
| `resources` | `250m` CPU, `256Mi` memory | Per replica. Kionga sets the request and the limit to the same value. |
| `replicas` | `min` 1, `max` 3 | `min` can be 0 for scale to zero. `max` is 1 to 100. |
| `scaling` | `requests`, target 100 | See [Scale an application](#scale). |
| `health_path` | `/` | The path of the health check. See [Health check](#health-check). |
| `visibility` | `sso` | `public`, `sso` or `internal`. See [Visibility](#visibility). |

An unset field takes the default. When you send a configuration with `PUT`, send
all of it: the gateway replaces the whole configuration. The Python client's
`update_application` and the CLI's `kionga apps update` read the current
configuration, apply your changes and send the result, so you pass only what
changes.

```bash
kionga apps update billing --max-replicas 6 --env LOG_LEVEL=debug --wait
```

A user with a compute grant can't deploy an application whose CPU or memory
at the maximum replica count exceeds the grant. The request returns `403
resource_not_provisioned` with the numbers.

## Environment and secrets {#secrets}

Put non-secret settings in `env`. Put credentials in a Kubernetes Secret.

An application can load a Secret only if an administrator has labeled it
`kionga.dev/workload-secret=true` in the installation's workload namespace. The label
keeps platform Secrets in the same namespace, such as agent tokens and provider
keys, out of reach of user software. A Secret without the label makes the
application fail with the reason `SecretNotAllowed`, and a missing Secret with
`SecretNotFound`.

```bash
kubectl -n kionga-workloads create secret generic billing-db \
  --from-literal=DATABASE_URL='postgres://billing:...@db.internal/billing'
kubectl -n kionga-workloads label secret billing-db kionga.dev/workload-secret=true
```

Then reference it by name:

```bash
kionga apps update billing --secret billing-db --wait
```

Every key in the Secret becomes an environment variable, so a key name should be
a valid variable name. Changing the Secret's data rolls the pods, so they pick
up the new value. If someone removes the label or deletes the Secret, Kionga
removes it from the running pods and the application shows `Failed`.

Replace `kionga-workloads` with your installation's workload namespace.

## Health check {#health-check}

Kionga sends an HTTP GET to `health_path` on your port to decide whether a pod
is started, ready for traffic and alive. A response from 200 to 399 passes. The
default path is `/`, so if `/` needs sign-in or returns 404, set a path that
returns 200, such as `/healthz`. A wrong path leaves the application in
`Progressing` and then `Failed`, because no pod ever becomes ready.

See [Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md#self-healing)
for the timings and what happens when a check fails.

## Visibility

| Value | Who can reach it |
| --- | --- |
| `sso` (default) | People who sign in to Kionga. The gateway signs them in on the application's own host and then forwards the request. |
| `public` | Anyone on the internet who can reach the host. Kionga adds no sign-in. |
| `internal` | Nothing outside the cluster. There is no public host and no URL. Other workloads reach it at its internal address. |

!!! info "Available in a later release"
    Sign-in on the application's host for `sso` and the `internal` value need the
    gateway and operator alignment. Until then, an application with `sso` is not
    published unless the operator has a sign-in upstream, and the API accepts
    only `public` and `sso`. Use `public` only for software that handles its own
    access.

A `public` application is open to the internet. Treat its image, its
configuration and its secrets accordingly.

## Scale an application {#scale}

An application runs between `replicas.min` and `replicas.max` pods. The default
trigger is requests: Kionga adds pods when the average number of concurrent
requests per pod goes above the target, which defaults to 100.

=== "CLI"

    ```bash
    # Scale on concurrent requests, and go to zero when idle
    kionga apps update billing --min-replicas 0 --max-replicas 10 \
      --scale-on requests --target 50

    # Scale on CPU instead (at least one pod always runs)
    kionga apps update billing --min-replicas 2 --max-replicas 10 \
      --scale-on cpu --target 70
    ```

=== "Python"

    ```python
    client.update_application(
        "billing", min_replicas=0, max_replicas=10,
        scaling={"metric": "requests", "target": 50},
    )
    ```

- `--scale-on` and `--target` go together. A request target is 1 to 10000
  concurrent requests per replica. A CPU target is 1 to 100 percent of the CPU
  request.
- **Scale to zero** needs the `requests` trigger and `min_replicas` of 0. After
  five minutes with no requests, the last pod stops. The next request starts one,
  so that request waits for the pod to start. A CPU-scaled application keeps at
  least one pod, and the API refuses a minimum of 0 with it.
- With a minimum of 2 or more, Kionga also protects the application during node
  drains.

[Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md)
explains the triggers, the cold start and when to choose each.

## Check status

```bash
kionga apps list
kionga apps get billing
```

The status has one of these values:

| Status | Meaning |
| --- | --- |
| `pending` | Kionga accepted a change and the operator has not finished rolling it out. |
| `ready` | The current version has the pods it needs. |
| `scaled-to-zero` | Ready, with no pods running because it is idle. The next request starts one. |
| `failed` | The spec is invalid, a Secret or build failed, or the rollout missed its deadline. The message gives the reason. |
| `missing` | The Kubernetes resource is gone. |

`kionga apps get` also shows the URL, ready replicas against the maximum, the
scaling trigger, the last build for a Git source, and the conditions `Ready`,
`IngressReady`, `ScalingReady` and `BuildSucceeded`. The `generation` and
`observed_generation` fields tell a client whether the status describes the
latest change.

## Read logs and events {#logs}

```bash
kionga apps logs billing --tail 100
kionga apps events billing
```

`logs` prints the last lines of each pod, 200 by default and up to 2000 per
pod, for up to 20 pods. Use `--container` to pick a container. `events` lists
Kubernetes events for the application, its Deployment and its pods, newest first.
Read the events when an application won't start: they show image pull errors,
failed scheduling and probe failures.

To follow logs live, call the API with `follow=true`. The reply is a stream of
Server-Sent Events that ends after `max_seconds` (600 by default, 3600 at most):

```bash
curl -N "$KIONGA_URL/api/v1/applications/billing/logs?follow=true&tail=50" \
  -H "Authorization: Bearer $KIONGA_TOKEN"
```

Each event has an `id` that is a timestamp. To resume after a break, reconnect
with the last `id` in the `Last-Event-ID` header or the `since` parameter.
Streaming covers the pods that exist when you connect, so reconnect to pick up
new pods.

## Redeploy {#redeploy}

Redeploy restarts the pods, and rebuilds a Git source from its current ref.

```bash
kionga apps redeploy billing --wait
```

!!! info "Available in a later release"
    The restart and rebuild on redeploy need the gateway and operator
    alignment. Until then, change a setting, such as an environment variable, to
    roll the pods.

## Delete an application

```bash
kionga apps delete billing
```

Deleting removes the application, its pods, its host name and its autoscaler. The
CLI asks you to confirm. Pass `-y` to skip the question in scripts. Images that
a source build pushed stay in the registry.

## Turn applications on {#enable}

This section is for administrators.

Applications run only on Kubernetes. On a Compose or single-server install, every
`/api/v1/applications` request returns `409` with `not_configured`, a message and
the steps to enable them. On Kubernetes without a base domain, the same error
says that `KIONGA_APPLICATIONS_BASE_DOMAIN` is not set.

To enable applications:

1. Install Kionga on Kubernetes with the Helm chart, and install the
   [cluster prerequisites](../operations/kubernetes-prerequisites.md): cert-manager,
   KEDA with its HTTP add-on, and an ingress controller.
2. Choose a base domain that differs from the console host, such as
   `kionga.company-x.net`, and point a wildcard DNS record `*.kionga.company-x.net`
   at the ingress controller.
3. Provide a wildcard TLS certificate for `*.kionga.company-x.net`, issued by
   cert-manager through a DNS-01 issuer, or an existing certificate Secret.
4. Set the base domain on the gateway and the operator, and restart both.

The operator reads these variables:

| Variable | Purpose |
| --- | --- |
| `KIONGA_APPLICATIONS_BASE_DOMAIN` | The base domain. Without it the operator serves no host. |
| `KIONGA_APPLICATIONS_TLS_SECRET` | The wildcard certificate Secret in the workload namespace. Without it, URLs use `http://`. |
| `KIONGA_INGRESS_CLASS` | The `ingressClassName` for application Ingresses. |
| `KIONGA_SSO_UPSTREAM` | The gateway's `host:port`, for `sso` applications. Without it, `sso` applications are not published. |
| `KIONGA_KEDA_INTERCEPTOR_URL` | Gateway only. The KEDA HTTP interceptor address that functions use. |
| `KIONGA_KEDA_HTTP_INTERCEPTOR` | Operator only. The interceptor `host:port`. Defaults to `keda-add-ons-http-interceptor-proxy.keda.svc.cluster.local:8080`. |
| `KIONGA_BUILD_REGISTRY` | The registry prefix source builds push to, such as `registry.example.com/kionga`. Empty turns source builds off. |
| `KIONGA_BUILD_PUSH_SECRET` | A `kubernetes.io/dockerconfigjson` Secret with push access, in the workload namespace. |
| `KIONGA_BUILD_REGISTRY_INSECURE` | `true` pushes over plain HTTP, for a registry inside the cluster. |
| `KIONGA_BUILDKIT_IMAGE` | The rootless BuildKit image. Defaults to a pinned release. |

The gateway also reads `KIONGA_APPLICATIONS_BASE_DOMAIN` and
`KIONGA_TARGET_NAMESPACE`. Applications are Kubernetes resources, so the
Kionga resource definitions for applications, functions and model deployments
must be installed too. They come with each platform release in `config/crd`.

Source builds run rootless BuildKit, which needs an unconfined seccomp and
AppArmor profile. A namespace that enforces the Pod Security `baseline` or
`restricted` level refuses those pods, so builds need a namespace that doesn't.
See [Kubernetes prerequisites](../operations/kubernetes-prerequisites.md#pod-security-for-builds).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `409 not_configured` | The install runs on Compose, or the base domain is not set. The reply lists the steps. |
| `422 validation_error` | The reply lists each invalid field. For example, `image` and `source` together, a reserved name, or a CPU scale with `min` 0. |
| `409 conflict` | An application with that name exists, or a Kubernetes resource of that name belongs to another project. |
| Phase `Failed`, `InvalidName` | The name is longer than 45 characters. |
| Phase `Failed`, `SecretNotAllowed` or `SecretNotFound` | The Secret is missing, or lacks the `kionga.dev/workload-secret=true` label. |
| Phase `Failed`, `BuildNotConfigured` | The operator has no `KIONGA_BUILD_REGISTRY`. |
| Phase `Failed`, `UnsupportedSource` | The Git URL isn't a public `https://` URL without credentials. |
| Stuck in `Progressing`, events show `CreateContainerConfigError` | The image runs as root, or has a non-numeric user. Set `USER 10001` in the Dockerfile. |
| Stuck in `Progressing`, events show probe failures | The health path doesn't return 200 on your port. |
| `ScalingReady` is `False` with `KEDAHTTPAddonMissing` | The KEDA HTTP add-on wasn't installed when the operator started. Install it and restart the operator. |
| The URL doesn't resolve | The wildcard DNS record is missing, or the application is `internal`. |
| Browser certificate warning | The wildcard certificate doesn't cover the host, or isn't issued yet. |

## Next steps

- [Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).
- [Deploy on Kubernetes](../operations/managed-kubernetes.md).
- [REST API: applications](../reference/api.md).
