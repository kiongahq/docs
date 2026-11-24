---
icon: material/source-branch-sync
description: Deploy a model to a KServe endpoint on Kubernetes, check its status, send a share of traffic to a canary version with a weight split and a routing key header, and roll it back.
---

# Deploy and canary models on Kubernetes

On Kubernetes, **Deploy** on a model card starts a real model server with
[KServe](https://kserve.github.io/website/) and shows the endpoint only after the
server is ready. A deploy never reports success for a server that did not start.
You can also send a share of traffic to a new version first, as a canary.

On Compose, Deploy starts one container per model with the serving manager; see
[Register, deploy and serve models](models-serving.md). The console, SDK and
API are the same on both.

!!! info "Available in a later release"
    The operator and gateway for model deploys ship in platform v0.2.1. These
    parts are not in a released version yet:

    - **Chart wiring.** The chart in deploy v0.2.0 does not install the model
      deployment resource definition or set the operator's object store
      variables. See [Kubernetes prerequisites](../operations/kubernetes-prerequisites.md).
    - **Canary.** The gateway and the operator are being aligned on the shape of
      the canary fields. A plain deploy is unaffected by the canary part. Treat
      the canary sections as the behavior to expect after the change.

## Before you begin

- The model is registered in MLflow with the quality gate `passed`, and its
  artifacts are in an S3-compatible object store. Kionga loads `s3://` locations
  only.
- You need the `models` service for a normal user, or the `engineer`,
  `operator` or `admin` role, and access to the project.
- An administrator has installed KServe in RawDeployment mode (plain Deployments
  and Services, with no Knative or Istio), and has told the operator how to read
  your object store. See [Set up model serving](#set-up).

## Deploy a model

1. Deploy the version:

    === "Console"

        Open **Models**, click **Deploy** in the version's row, leave **Canary
        weight (%)** at `0`, and click **Deploy**.

    === "SDK"

        ```python
        client.deploy_model(model.id)
        deployment = client.wait_for_model_deployment(model.id)
        print(deployment.endpoint_url)
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/deploy" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"canary_weight": 0}'
        ```

    The request returns `202` with `deployment_status` set to `pending`.

2. Read the live status at any time:

    ```bash
    curl -s "$KIONGA_URL/api/v1/models/<model-id>/deployment" \
      -H "Authorization: Bearer $KIONGA_TOKEN"
    ```

3. Send predictions as in [Send a prediction](models-serving.md#send-a-prediction).
   The gateway forwards the request to the server's `/invocations` route.

Behind the request:

1. The gateway creates one deployment resource for the model name in its
   project.
2. The operator asks MLflow where the version's files live and turns the answer
   into an `s3://` address.
3. The operator creates a KServe InferenceService, and KServe starts the model
   server. The server downloads the model with the object store credentials the administrator configured.
4. When the server is ready, the status becomes `serving` and `endpoint_url` is
   set. If KServe reports a failure, the status becomes `failed` and
   `deployment_message` says why.

Promotion in the registry changes the MLflow stage only. It does not start or stop
a server. Deploy does that.

## Send a share of traffic to a canary

A canary serves a new version next to the stable version, and the gateway sends
the share of requests you choose to the new one. KServe's plain Deployment mode
has no traffic splitting, so Kionga runs the canary as a second InferenceService
and splits the traffic itself.

1. Deploy the stable version with a weight of 0, and wait for `serving`.
2. Deploy the new version with a weight from 1 to 99:

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/models/<new-version-id>/deploy" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"canary_weight": 10}'
    ```

    ```python
    client.deploy_model(new_version.id, canary_weight=10)
    ```

3. Send predictions to either version's ID. The gateway splits them between the two
   servers by the weight, and tells you which version answered in the
   `X-Kionga-Model-Version` response header.

A canary needs a stable version that is `serving`. Without one, the request
returns `422` and says to deploy a stable version first. Until the canary server is
ready, all requests go to the stable version. A weight of `100` makes the new
version the only one, the same as a weight of 0 for that version.

### How requests are split

| Request | Where it goes |
| --- | --- |
| No routing key | Exactly the weight percent of each 100 consecutive requests go to the canary, spread evenly. Each gateway replica counts its own requests. |
| `X-Kionga-Routing-Key: <key>` | Sticky. The same key always reaches the same version for a given weight. A key goes to the canary when a hash of the key, modulo 100, is below the weight. |

Use a routing key when one caller must see one version, for example a customer ID
or a session ID, so that a user doesn't see answers change between requests:

```bash
curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/predict" \
  -H "Authorization: Bearer $KIONGA_TOKEN" \
  -H "X-Kionga-Routing-Key: customer-42" \
  -H 'Content-Type: application/json' \
  -d '{"inputs": [[0.1, -1.2, 0.5]]}' -i
```

Raising the weight moves more keys to the canary and never moves a key back,
because a key goes to the canary when its hash is below the weight. Lowering
the weight returns those keys to the stable version.

### Promote or roll back a canary

- **Promote:** deploy the new version with a weight of 0 or 100. The new version
  becomes the stable version.
- **Roll back the canary:** roll back the canary version
  (`POST /api/v1/models/<id>/rollback`). The deployment drops the canary and all traffic
  returns to the stable version.
- Rolling back the stable version while a canary exists returns `409`. Roll back
  the canary first. Rolling back a stable version with no canary removes the
  deployment.

## Set up model serving {#set-up}

This section is for administrators. Model deploys need these on the cluster:

- KServe, installed in RawDeployment mode. KServe 0.21 calls this mode
  `Standard` and still accepts `RawDeployment`.
- The Kionga operator able to reach MLflow (`MLFLOW_URL`) and read model
  artifacts from the object store.

Set these variables on the operator, and restart it. The operator checks for
KServe at startup.

| Variable | Purpose |
| --- | --- |
| `KIONGA_MODEL_STORAGE_SECRET` | A Secret in the workload namespace with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` that model servers read artifacts with. Use a read-only identity. Empty leaves credentials to the cluster, for example workload identity. |
| `KIONGA_MODEL_S3_ENDPOINT` | The object store address as `host:port`, without a scheme. |
| `KIONGA_MODEL_S3_USE_HTTPS` | `1` or `0`. The default is `0`. |
| `KIONGA_MODEL_S3_REGION` | The region. The default is `us-east-1`. |
| `KIONGA_MLFLOW_ARTIFACTS_DESTINATION` | The bucket behind MLflow's artifact proxy, such as `s3://kionga-models`, when MLflow serves artifacts itself. |
| `KIONGA_KSERVE_DEPLOYMENT_MODE` | The KServe mode. The default is `RawDeployment`. |

Without KServe, a deployment fails with a message that the cluster does not serve
InferenceService and that KServe must be installed. Without a way to reach the
artifacts, it fails with the location it could not read. Allow the model servers
to reach the object store in your network policies.

## Verify

1. **Deploy:** the status call returns `"status": "serving"` and an
   `endpoint_url` that starts with `http`. The response also carries `model_id`,
   `name`, `version`, `message` and `canary_weight`. In the console, the
   **Deployment** column of **Models** shows `serving` for the version, and a
   **Test** button appears in its row.
2. **Canary:** over about 100 requests without a routing key, the
   `X-Kionga-Model-Version` response header shows the canary version for about
   the weight percent of them. With a routing key, the same key always shows the
   same version.
3. **Canary status:** the canary version's **Deployment** column shows `serving`
   with the note `canary <weight>%`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `422`, `model evaluation gates have not passed` | The model's gate is `failed` or `needs_evaluation`. | Register an evaluated version with passing metrics. |
| `422`, `a canary needs a serving stable version of <name>; deploy one with canary_weight 0 first` | No stable version of the model is serving. | Deploy the stable version with weight 0, and wait for `serving`. |
| `422`, `canary_weight must be between 0 and 100` | The weight is outside the range. | Send a weight from 0 to 100. |
| `503 kubernetes_unavailable`, `the gateway cannot reach the Kubernetes API with its in-cluster service account` | The gateway cannot call the Kubernetes API. | Check the gateway's service account; see [Kubernetes prerequisites](../operations/kubernetes-prerequisites.md). |
| Status stays `pending`, and `message` says `waiting for the model server to become ready` or names an InferenceService | KServe is still starting the server, or the server cannot start. | Wait. If it stays pending, check for a missing KServe, a server that cannot download the artifact, or an image pull error in the pod events. |
| Status `failed`, `this cluster does not serve serving.kserve.io/v1beta1 InferenceService; install KServe in RawDeployment mode` | KServe is not installed. | Install KServe in RawDeployment mode. See [Set up model serving](#set-up). |
| Status `failed`, `MLflow is not configured on the operator (MLFLOW_URL)` | The operator cannot reach MLflow. | Set `MLFLOW_URL` on the operator and restart it. |
| Status `failed`, `artifact location "<uri>" is proxied by MLflow; set KIONGA_MLFLOW_ARTIFACTS_DESTINATION to the bucket behind it` | MLflow serves the artifacts itself, and the operator does not know the bucket. | Set `KIONGA_MLFLOW_ARTIFACTS_DESTINATION` on the operator, for example `s3://kionga-models`. |
| Status `failed`, `artifact location "<uri>" uses scheme "<scheme>"; KServe here reads s3:// only` | The model's artifacts are not in an S3-compatible store. | Store the artifacts in an S3-compatible bucket. |
| `409 not_serving` on predict | The stable version is not serving yet. | Wait for `serving`, then retry. |
| Rollback returns `409`, `version <v> is a canary on this version; roll the canary back first` | You rolled back the stable version while a canary exists. | Roll the canary back first. |

## Related pages

- [Register, deploy and serve models](models-serving.md).
- [Kubernetes prerequisites](../operations/kubernetes-prerequisites.md).
- [Shift canary traffic for agents](agents.md#shift-canary-traffic).
