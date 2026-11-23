---
icon: material/function-variant
description: Run functions on Kubernetes as Kionga-native workloads that scale to zero on requests and wake on the next call, with no OpenFaaS, and see how Compose installs keep faasd.
---

# Run functions on Kubernetes

A function is a container image that serves HTTP, which Kionga runs for you and
calls through the gateway. On Kubernetes, functions are Kionga-native: Kionga
runs each one as a self-healing, autoscaling pod, and by default it scales to
zero when nobody calls it and starts again on the next call. There is no OpenFaaS
on a Kubernetes install.

Compose and single-server installs keep faasd (OpenFaaS's single-node engine).
For those, follow [Git, functions and distributed workspaces](distributed-workspaces.md#deploy-a-function).
The API and the commands are the same in both cases, so a client doesn't change.

| | Kubernetes | Compose and single server |
| --- | --- | --- |
| Engine | Kionga, with KEDA for scaling | faasd or an OpenFaaS gateway you provide |
| Scale to zero | Built in, on by default | Depends on your OpenFaaS setup |
| Setup | The [cluster prerequisites](../operations/managed-kubernetes.md) | `OPENFAAS_URL`, `OPENFAAS_USER` and `OPENFAAS_PASSWORD` |
| Cron and Kafka triggers | Not available | OpenFaaS connectors |
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
- Your image serves HTTP on port 8080, accepts `POST /` with a JSON body, and
  runs as a non-root user with a numeric user ID.

## Deploy a function

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

The request returns at once with the function in the `pending` state. Kionga
creates the function only after Kubernetes accepts it. A function name is global
across projects: if the name belongs to another project, the request returns `409
conflict`.

| Field | Default | Notes |
| --- | --- | --- |
| `name` | none | A lowercase DNS label, up to 45 characters. |
| `image` | none | Required. An OCI image reference. |
| `env_vars` | none | Environment variables, as a map. |
| `cpu`, `memory` | `100m`, `256Mi` | Per pod, as Kubernetes quantities. Request and limit are equal. The SDK's own defaults are `500m` and `512Mi`. |
| `replicas` | `min` 0, `max` 5 | `max` is 1 to 100. |
| `scaling` | `requests`, target 100 | `requests` counts concurrent calls per pod. `cpu` scales on utilization and needs `min` of 1 or more. |

A function has no public host by default. Callers reach it through the gateway,
which also checks who may call it. The same health, restart and rolling-update
rules as for [applications](applications.md) apply. See
[Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).

**Verify:** `GET /api/v1/functions` lists the function with the status `ready`
or `scaled-to-zero` and `"runtime": "kubernetes"`.

## Invoke a function

```bash
export KIONGA_FUNCTION_PAYLOAD='{"customer_id":"c-42"}'
kionga-cli function invoke score-events
kionga-cli function invoke-async score-events
```

```python
result = client.invoke_function("score-events", {"customer_id": "c-42"})
call = client.invoke_function_async("score-events", {"customer_id": "c-42"})
```

- **Synchronous** calls return the function's JSON response. The request body can
  be up to 1 MiB, and the gateway waits up to 2 minutes, which covers a cold
  start. A non-2xx response from the function comes back as `502 invoke_failed`
  with its message.
- **Asynchronous** calls return `202` with a `call_id` at once and run in the
  background of the gateway replica that took the request. There is no queue: if
  that replica stops before the call finishes, the call is lost. The gateway logs
  the outcome with the call ID. Use a synchronous call, or a pipeline, when you
  must not lose work.

## Scale to zero and wake

With the `requests` trigger and a minimum of 0, Kionga removes the last pod after
five minutes without calls. The next call reaches the KEDA HTTP interceptor,
which holds it while a pod starts, and forwards it when the pod is ready. The
interceptor holds a call for its wait limit, 20 seconds by default, so keep
images small and startup quick. A function that must answer instantly needs a
minimum of 1.

A new function starts with one pod and scales to zero after the idle period.

## What isn't available on Kubernetes

- **Cron and Kafka triggers.** These came from OpenFaaS connectors, which the
  Kubernetes runtime doesn't use. Schedule a call from a
  [pipeline](pipelines.md#schedule-a-flow), or run a [real-time consumer](realtime.md).
- **OpenFaaS settings.** `OPENFAAS_URL` and the OpenFaaS connection don't affect
  functions on Kubernetes.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `409 conflict` on deploy | The name belongs to another project. |
| `400 invalid_request`, `cpu scaling keeps at least one replica` | Set `min_replicas` to 1 or more, or use `requests` scaling. |
| `502 invoke_failed` after a long wait | The function didn't become ready in time, or its image can't start. Check `kionga-cli function list` and the pod events. |
| Status `failed` | The image can't be pulled or runs as root. Read the status message. |

## Next steps

- [Deploy applications](applications.md).
- [Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).
