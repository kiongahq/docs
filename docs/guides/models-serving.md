---
icon: material/rocket-launch-outline
description: Register a model version, pass its quality gate, promote it, deploy it to a live REST endpoint, send predictions, and roll it back.
---

# Register, deploy and serve models

Take a trained model from registration to a live REST endpoint: register a
version, check its quality gate, promote it, deploy it, send predictions, and
roll back when you need to.

## Before you begin

- You need the `models` service for a normal user, or the `engineer`,
  `operator` or `admin` role, and access to the model's project. Viewers can
  see models but cannot change them.
- The model is logged to MLflow, or stored at an artifact URI that the serving
  image can load.
- Deployment needs the serving manager, which the Compose stack runs for you.
- For the API examples, export `MLAIOPS_URL` and a personal API key with the
  `models` scope as `MLAIOPS_TOKEN`. See
  [Authentication](../reference/api.md#authentication).

## Register a model version

A training pipeline usually registers its model. To register one yourself:

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
    curl -s -X POST "$MLAIOPS_URL/api/v1/models" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"project_id": "prj-123", "name": "churn-classifier", "version": "1",
           "artifact_uri": "models:/m-1234",
           "serving_image": "ghcr.io/acme/churn-sklearn@sha256:<digest>",
           "metrics": {"accuracy": 0.968}}'
    ```

`serving_image` is optional. Set it when the model needs libraries that the
default serving image does not have; see
[Avoid training-serving skew](#avoid-training-serving-skew).

A new version starts in the `candidate` stage with a quality gate:

| Gate status | When |
| --- | --- |
| `passed` | The default for a registered artifact |
| `failed` | The metrics include `accuracy` below `0.8` |
| `needs_evaluation` | The artifact is an imported Hugging Face reference (`hf://`) |

A project cannot hold two versions with the same name and version number.

**Verify:** the model appears under **Models** with its stage, quality gate and
metrics, and the **Model quality by version** chart includes it.

## Promote a model

Promotion moves a version to `staging`, `production` or `archived`. Promoting to
`production` requires a `passed` quality gate.

=== "Console"

    On the model card, click **Promote**. The console promotes the version to
    `production`.

=== "SDK"

    ```python
    client.promote_model(model.id, "staging")
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/promote" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"stage": "production"}'
    ```

**Verify:** the model card shows the new stage, for example `production · v1`.

## Deploy a model to a live endpoint

Deploying starts an `mlflow models serve` container for the version and records
its endpoint. Deployment also requires a `passed` quality gate.

=== "Console"

    On the model card, click **Deploy**.

=== "SDK"

    ```python
    client.deploy_model(model.id)
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/deploy" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"canary_weight": 0}'
    ```

When the container starts, the model's `deployment_status` becomes `serving`
and its `endpoint_url` is recorded, for example
`http://mlaiops-serve-churn-classifier:5001`. If the serving manager rejects the
deployment, the status becomes `failed` and the request returns `502` with the
reason.

`canary_weight` (0 to 100) is recorded on the model. The bundled serving path
runs one container per model name and does not split traffic between versions.
Agents have their own [canary traffic control](agents.md#shift-canary-traffic).

**Verify:** the model card shows a **● live** tag and a **Test** button.

## Send a prediction

The gateway forwards your request to the model's MLflow `/invocations` route.

=== "Console"

    1. On a live model card, click **Test**.
    2. Edit the **Request payload** and click **Send prediction request**.

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/predict" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
    ```

A model without a live endpoint returns `409 not_serving`.

**Verify:** the response contains predictions, for example
`{"predictions": [1]}`.

## Roll back a model

Rollback returns the version to its previous stage, sets its deployment status to
`rolled_back` and removes its serving container.

=== "Console"

    On the model card, click **Rollback**.

=== "SDK"

    ```python
    client.rollback_model(model.id)
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/rollback" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" -d '{}'
    ```

A version that was never promoted has no previous stage, and rollback returns
`no previous stage is available`.

**Verify:** the model card shows the previous stage and the deployment status
`rolled_back`.

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

Serving containers run with the platform's model-store credentials, so treat the
images you allow as part of your trust boundary. Dropped capabilities,
`no-new-privileges` and a process limit reduce what a container can do, but they
do not make an untrusted image safe.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `model evaluation gates have not passed` | The gate is `failed` or `needs_evaluation`. Register an evaluated version with passing metrics. |
| Deploy returns `502 serving_failed` | The serving manager could not start the container; the message gives its reason. See [Troubleshooting](../operations/troubleshooting.md). |
| `409 not_serving` on predict | Deploy the model first, and wait for the **● live** tag. |

## Next steps

- [Import a Hugging Face model](huggingface.md).
- [Use a deployed model in real-time scoring](realtime.md).
- [Train models in a pipeline](pipelines.md).
