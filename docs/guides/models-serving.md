---
icon: material/rocket-launch-outline
description: Register a model version, pass its quality gate, promote it, deploy it to a live REST endpoint, send predictions, and roll it back.
---

# Register, deploy and serve models

Take a trained model from registration to a live REST endpoint. You register a
version, check its quality gate, promote it, deploy it, send predictions, and
roll back when you need to.

## Before you begin

- You need the `models` service for a normal user, or the `engineer`,
  `operator` or `admin` role, and access to the model's project. Viewers can
  see models but cannot change them.
- The model is logged to MLflow, or stored at an artifact URI that the serving
  image can load.
- Deployment needs the serving manager, which the Compose stack runs for you. On
  Kubernetes, deployment uses KServe instead; see
  [Deploy and canary models on Kubernetes](models-kubernetes.md).
- For the API examples, export `KIONGA_URL` and a personal API key with the
  `models` scope as `KIONGA_TOKEN`. See
  [Authentication](../reference/api.md#authentication).

## Register a model version

A training pipeline usually registers its model. To register one yourself:

1. Register the version:

    === "SDK"

        ```python
        model = client.register_model(
            "prj-123", "churn-classifier", "1", "models:/m-1234",
            metrics={"accuracy": 0.968},
            serving_image="ghcr.io/acme/churn-sklearn@sha256:<digest>",
        )
        print(model.id, model.gate_status)
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"project_id": "prj-123", "name": "churn-classifier", "version": "1",
               "artifact_uri": "models:/m-1234",
               "serving_image": "ghcr.io/acme/churn-sklearn@sha256:<digest>",
               "metrics": {"accuracy": 0.968}}'
        ```

2. Read `gate_status` in the response. A new version starts in the `candidate`
   stage with a quality gate:

    | Gate status | When |
    | --- | --- |
    | `passed` | The default for a registered artifact |
    | `failed` | The metrics include `accuracy` below `0.8` |
    | `needs_evaluation` | The artifact is an imported Hugging Face reference (`hf://`) |

`serving_image` is optional. Set it when the model needs libraries that the
default serving image does not have; see
[Avoid training-serving skew](#avoid-training-serving-skew). The image must match
`SERVE_IMAGE_ALLOWED_PREFIXES`, and in production it must be pinned by digest.
A project cannot hold two versions with the same name and version number.

## Promote a model

Promotion moves a version to `staging`, `production` or `archived`. Promoting to
`production` requires a `passed` quality gate.

1. Promote the version:

    === "Console"

        Open **Models** and click **Promote** in the version's row. The console
        promotes the version to `production`.

    === "SDK"

        ```python
        client.promote_model(model.id, "staging")
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/promote" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"stage": "production"}'
        ```

## Deploy a model to a live endpoint

Deploying starts an `mlflow models serve` container for the version and records
its endpoint. Deployment also requires a `passed` quality gate.

1. Deploy the version:

    === "Console"

        Open **Models**, click **Deploy** in the version's row, leave **Canary
        weight (%)** at `0`, and click **Deploy**.

    === "SDK"

        ```python
        client.deploy_model(model.id)
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/deploy" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"canary_weight": 0}'
        ```

2. Wait for the container to start. The model's `deployment_status` becomes
   `serving` and its `endpoint_url` is recorded, for example
   `http://kionga-serve-churn-classifier:5001`. If the serving manager rejects
   the deployment, the status becomes `failed` and the request returns `502`
   with the reason.

`canary_weight` (0 to 100) is recorded on the model. The bundled serving path
runs one container per model name and does not split traffic between versions.
On Kubernetes, a canary does split traffic; see
[Deploy and canary models on Kubernetes](models-kubernetes.md#send-a-share-of-traffic-to-a-canary).
Agents have their own [canary traffic control](agents.md#shift-canary-traffic).

## Send a prediction

The gateway forwards your request to the model's MLflow `/invocations` route.

1. Send a request:

    === "Console"

        1. In the live version's row, click **Test**.
        2. Edit the **Request payload** and click **Predict**.

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/predict" \
          -H "Authorization: Bearer $KIONGA_TOKEN" \
          -H 'Content-Type: application/json' \
          -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
        ```

A model without a live endpoint returns `409 not_serving`.

## Roll back a model

Rollback returns the version to its previous stage, sets its deployment status to
`rolled_back` and removes its serving container.

1. Roll the version back:

    === "Console"

        Open **Models** and click **Rollback** in the version's row.

    === "SDK"

        ```python
        client.rollback_model(model.id)
        ```

    === "API"

        ```bash
        curl -s -X POST "$KIONGA_URL/api/v1/models/<model-id>/rollback" \
          -H "Authorization: Bearer $KIONGA_TOKEN" -d '{}'
        ```

A version that was never promoted has no previous stage, and rollback returns
`422` with `no previous stage is available`.

## Avoid training-serving skew


A model trained with one library version can fail to load under another. The
default serving image matches the [Jupyter workbench](workbench.md) pins
(`scikit-learn==1.7.0`, `mlflow==3.16.1`), so scikit-learn models trained there
serve as they are.

For `xgboost`, PyTorch and other frameworks, register a `serving_image` with each
version:

- Use an OCI image with the same dependencies you trained with, pinned by digest.
- Include the `mlflow` command-line tool and support for your artifact store,
  because Kionga runs `mlflow models serve` inside the image.

A model server holds no platform credentials. A short-lived fetch container,
which runs the operator's image rather than yours, downloads the artifact into a
volume. The server starts with an empty environment and mounts that volume
read-only. Still treat the images you allow as part of your trust boundary: the
server runs on the platform network, and dropped capabilities,
`no-new-privileges` and a process limit do not make an untrusted image safe.
Administrators list trusted images in `SERVE_IMAGE_ALLOWED_PREFIXES`; see
[Serving manager](../reference/configuration.md#serving-manager).

## Verify

Check each step against the model record. `GET /api/v1/models` returns the
registered versions in an `items` array.

1. **Register:** the version appears under **Models** with its **Stage**,
   **Quality gate** and **Metrics**, and the API record has `"stage":
   "candidate"` and the `gate_status` you expect.
2. **Promote:** the **Stage** column shows the new stage, and the API record has
   the matching `stage`.
3. **Deploy:** the **Deployment** column shows `serving`, a **Test** button
   appears in the row, and the API record has a `deployment_status` of `serving`
   and an `endpoint_url` that starts with `http`.
4. **Predict:** the response contains predictions, for example
   `{"predictions": [1]}`.
5. **Roll back:** the **Stage** column shows the previous stage, and the
   **Deployment** column shows `rolled_back`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `422`, `model evaluation gates have not passed` | You promoted to `production` or deployed a version whose gate is `failed` or `needs_evaluation`. | Register an evaluated version with passing metrics. |
| `409`, `resource already exists` | The project already holds a version with that name and version number. | Register the model under a new version number. |
| `409 not_configured`, `Model serving is not configured: SERVING_MANAGER_URL is not set, so Deploy cannot start a model server.` | The gateway has no serving manager address. | Set `SERVING_MANAGER_URL` on the gateway. The Compose stack sets it for you. |
| `502 serving_failed`, `... is outside SERVE_IMAGE_ALLOWED_PREFIXES ...` or `only the default serving image is allowed until the operator sets SERVE_IMAGE_ALLOWED_PREFIXES` | The version's `serving_image` is outside the images the operator allows. | Use an allowed image, or ask an administrator to add its prefix to `SERVE_IMAGE_ALLOWED_PREFIXES`. |
| `502 serving_failed`, `... must be pinned by digest (name@sha256:...)` | The operator requires digests and the `serving_image` has none. | Register the version with an image pinned as `name@sha256:<digest>`. |
| `502 serving_failed` with another reason | The serving manager could not start the container. The message gives its reason. | Fix the cause it names. See [Troubleshooting](../operations/troubleshooting.md). |
| `409 not_serving`, `model has no live serving endpoint` | The version has no live endpoint. | Deploy the model first, and wait for `deployment_status` to become `serving`. |
| `422`, `no previous stage is available` | The version was never promoted, so rollback has no stage to return to. | Promote the version before you roll it back, or deploy a different version. |

## Related pages

- [Import a Hugging Face model](huggingface.md).
- [Deploy and canary models on Kubernetes](models-kubernetes.md).
- [Use a deployed model in real-time scoring](realtime.md).
- [Train models in a pipeline](pipelines.md).
