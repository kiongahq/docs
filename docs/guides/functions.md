---
icon: material/function-variant
description: Run functions on Kubernetes as Kionga-native workloads that scale to zero on requests and wake on the next call, with no OpenFaaS, and see how Compose installs keep faasd.
---

# Run functions on Kubernetes

Deploy a function on Kubernetes, call it through the gateway, and let it scale to
zero when nobody calls it. A function is a container image that serves HTTP,
which Kionga runs for you. On Kubernetes, functions are Kionga-native: Kionga
runs each one as a self-healing, autoscaling pod, and by default it starts the
pod again on the next call. There is no OpenFaaS on a Kubernetes install.

Compose and single-server installs keep faasd (OpenFaaS's single-node engine).
For those, follow [Git, functions and distributed workspaces](distributed-workspaces.md#deploy-a-function).
The API and the commands are the same in both cases, so a client doesn't change.

| | Kubernetes | Compose and single server |
| --- | --- | --- |
| Engine | Kionga, with KEDA for scaling | faasd or an OpenFaaS gateway you provide |
| Scale to zero | Built in, on by default | Depends on your OpenFaaS setup |
| Setup | The [cluster prerequisites](../operations/kubernetes-prerequisites.md) | `OPENFAAS_URL`, `OPENFAAS_USER` and `OPENFAAS_PASSWORD` |
| Cron and Kafka triggers | Not available. The settings are recorded, and nothing acts on them. | OpenFaaS connectors |
| Asynchronous calls | Run in the gateway, with no queue | OpenFaaS queue |

!!! info "Available in a later release"
    Functions run on Kubernetes with platform v0.2.1, but the chart in deploy
    v0.2.0 doesn't install the resource definitions or set the variables they
    need. Calls to a function also need a gateway and operator alignment, which
    sends each call to the address the operator reports for the function.
    Until a later release, treat this page as the behavior to expect after
    those changes.

## Before you begin

- You need the `functions` service for a normal user, or the `engineer`,
  `operator` or `admin` role, and access to the project.
- The install runs on Kubernetes with KEDA and its HTTP add-on. Without the
  add-on, a function falls back to CPU scaling and keeps one pod running.
- Your image serves HTTP on port 8080 and accepts `POST /` with a JSON body. It
  runs as a non-root user with a numeric user ID, or you set one with
  `run_as_user`.

## Deploy a function

1. Deploy the function with the SDK, the CLI or the API:

    === "SDK"

        ```python
        client.deploy_function(
            "prj-123", "score-events", "ghcr.io/acme/score-events:1.4.0",
            cpu="500m", memory="512Mi",
            min_replicas=0, max_replicas=5,
            scaling={"metric": "requests", "target": 100},
        )
        ```

    === "CLI"

        ```bash
        kionga-cli function deploy prj-123 score-events ghcr.io/acme/score-events:1.4.0
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/functions" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"project_id": "prj-123", "name": "score-events",
               "image": "ghcr.io/acme/score-events:1.4.0",
               "cpu": "500m", "memory": "512Mi",
               "replicas": {"min": 0, "max": 5},
               "scaling": {"metric": "requests", "target": 100}}'
        ```

2. Read the response. The request returns at once with the function in the
   `pending` state. Kionga creates the function only after Kubernetes accepts
   it. A function name is global across projects: if the name belongs to another
   project, the request returns `409 conflict`.
3. Set the fields that your function needs:

    | Field | Default | Notes |
    | --- | --- | --- |
    | `name` | none | A lowercase DNS label, up to 45 characters. |
    | `image` | none | Required. An OCI image reference. |
    | `env_vars` | none | Environment variables, as a map. |
    | `cpu`, `memory` | `100m`, `256Mi` | Per pod, as Kubernetes quantities. Request and limit are equal. The SDK's own defaults are `500m` and `512Mi`. |
    | `replicas` | `min` 0, `max` 5 | `max` is 1 to 100. |
    | `scaling` | `requests`, target 100 | `requests` counts concurrent calls per pod. `cpu` scales on utilization and needs `min` of 1 or more. |
    | `visibility` | `internal` | `internal`, `sso` or `public`. `internal` gives the function no host. |
    | `run_as_user` | The image's own user | Optional. A numeric user ID from 1 to 2147483647 for an image that runs as root or names its user. `0` is refused with `400 invalid_request`. |
    | `labels` | none | Labels recorded on the function, as a map. |

    A deploy replaces the whole function. A field that you leave out goes back
    to its default, so send `visibility`, `labels` and `run_as_user` on every
    deploy that should keep them. The SDK's `deploy_function` takes all three
    as keyword arguments.

    !!! info "Available in a later release"
        `visibility` and `run_as_user` on functions are not in platform v0.2.1
        or earlier, and the SDK's `visibility`, `labels` and `run_as_user`
        arguments are not in SDK v0.3.2 or earlier.

Function pods never run as root. When Kubernetes refuses to start an image
because it runs as root or names its user, the function's status becomes
`failed` with a message that names the image and the fix. The rules are the same
as for an application's [container user](applications.md#container-user).

A function has no public host by default. Callers reach it through the gateway,
which also checks who may call it. The same health, restart and rolling-update
rules as for [applications](applications.md) apply. See
[Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).

## Invoke a function

1. Call the function and wait for its response:

    ```bash
    export KIONGA_FUNCTION_PAYLOAD='{"customer_id":"c-42"}'
    kionga-cli function invoke score-events
    ```

    ```python
    result = client.invoke_function("score-events", {"customer_id": "c-42"})
    ```

    A synchronous call returns the function's JSON response. The request body
    can be up to 1 MiB, and the gateway waits up to 2 minutes, which covers a
    cold start. A non-2xx response from the function comes back as `502
    invoke_failed` with its message.

2. To start a call without waiting, use an asynchronous call:

    ```bash
    kionga-cli function invoke-async score-events
    ```

    ```python
    call = client.invoke_function_async("score-events", {"customer_id": "c-42"})
    ```

    An asynchronous call returns `202` with a `call_id` at once and runs in the
    background of the gateway replica that took the request. There is no queue:
    if that replica stops before the call finishes, the call is lost. The
    gateway logs the outcome with the call ID. Use a synchronous call, or a
    pipeline, when you must not lose work.

## Scale to zero and wake

With the `requests` trigger and a minimum of 0, Kionga removes the last pod after
five minutes without calls. The next call reaches the KEDA HTTP interceptor,
which holds it while a pod starts, and forwards it when the pod is ready. The
interceptor holds a call for its wait limit, 20 seconds by default, so keep
images small and startup quick. A new function starts with one pod and scales to
zero after the idle period.

To keep a function warm, set `min_replicas` (`replicas.min` in the API) to 1.
A function that must answer instantly needs a minimum of 1.

## What isn't available on Kubernetes

- **Cron and Kafka triggers.** These came from OpenFaaS connectors, which the
  Kubernetes runtime doesn't use. Nothing on Kubernetes runs a function on a
  schedule or calls it for each message on a topic. Schedule a call from a
  [pipeline](pipelines.md#schedule-a-flow), or run a [real-time consumer](realtime.md).
- **OpenFaaS settings.** `OPENFAAS_URL` and the OpenFaaS connection don't affect
  functions on Kubernetes.

The console's **Deploy function** form shows the same **Trigger** list on every
install: `http`, `async`, `cron` and `kafka`. The choice is saved with the
function as the annotations `io.kionga.invocation`, `schedule` and `topic`, and
the **Trigger** column shows it. This table says what each choice does:

| **Trigger** | Kubernetes | Compose and single server |
| --- | --- | --- |
| `http` | Calls go through the gateway. | Calls go through the gateway. |
| `async` | The function runs like any other. The console's invoke dialog sends an asynchronous call, and its button reads **Queue invocation**. | The same, and the call goes to the OpenFaaS queue. |
| `cron` | Recorded only. The function never runs on the schedule. | The OpenFaaS cron connector runs it, when you have installed the connector. |
| `kafka` | Recorded only. No message on the topic calls the function. | The OpenFaaS Kafka connector calls it, when you have installed the connector. |

On Kubernetes, a function with the `cron` or `kafka` trigger still deploys and
reads `ready`, so check the install mode before you rely on a trigger.

## Verify

1. List the functions:

    ```bash
    curl -s "$KIONGA_URL/api/v1/functions" \
      -H "Authorization: Bearer $KIONGA_TOKEN"
    ```

    The response has `"runtime": "kubernetes"` and an `items` array. The
    function appears with the status `ready` (at least one pod is running) or
    `scaled-to-zero` (the function is ready with no pods running). Right after a
    deploy, the status is `pending` until the operator reports the function.
    `kionga-cli function list` prints the same list.

2. Invoke the function. A synchronous call returns the function's JSON
   response, and an asynchronous call returns `{"accepted": true, "call_id":
   "call-..."}`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `409 conflict`, `a function named <name> belongs to another project` | A function name is global, and another project already uses it. | Choose a different name. |
| `400 invalid_request`, `cpu scaling keeps at least one replica: set replicas.min to 1 or more` | You set `cpu` scaling with a minimum of 0. | Set `min_replicas` to 1 or more, or use `requests` scaling. |
| `400 invalid_request`, `function names on Kubernetes are at most 45 characters` | The name is longer than 45 characters. | Shorten the name. |
| `502 invoke_failed` with `function <name> is not deployed` | No function resource has that name in the cluster. | Deploy the function, or check the name with `kionga-cli function list`. |
| `502 invoke_failed` with `function <name> failed: <reason>` | The operator reports the function as failed. | Read the reason, fix the image or its settings, and deploy again. |
| `502 invoke_failed` after a long wait | The function didn't become ready in time, or its image can't start. | Check `kionga-cli function list` and the pod events. |
| Status `failed` | The operator reported a failure for the function. | Read the status `message` in the function list and fix the cause it names. |
| Status `failed`, and the message says that the image runs as root or names its user | Function pods never run as root, and Kubernetes can't verify a named user. | Deploy again with `run_as_user` set to a numeric non-root user ID, or rebuild the image with a numeric non-root `USER`. |
| `400 invalid_request`, `run_as_user cannot be 0: workloads never run as root; use a non-root user id such as 1000` | You sent `run_as_user` as `0`. | Send a user ID from 1 to 2147483647, or leave the field out. |
| A function with a `cron` or `kafka` trigger never runs by itself | On Kubernetes, nothing acts on the trigger settings. | Schedule the call from a [pipeline](pipelines.md#schedule-a-flow), or run a [real-time consumer](realtime.md). |
| `503 kubernetes_unavailable` | The gateway cannot reach the Kubernetes API with its in-cluster service account. | Check the gateway's service account and the cluster's API access; see the [cluster prerequisites](../operations/kubernetes-prerequisites.md). |

## Related pages

- [Deploy applications](applications.md).
- [Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).
- [Git, functions and distributed workspaces](distributed-workspaces.md#deploy-a-function) for Compose installs.
- [Define and run pipelines](pipelines.md#schedule-a-flow) to schedule calls.
