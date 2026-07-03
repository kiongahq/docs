# Models & serving

The classical-ML lifecycle, made real: register a model, gate it, promote it, deploy
it to a **live REST endpoint**, split traffic with a canary, and roll back.

## Registry

Models are registered against a project — usually automatically by the training
pipeline's `register` step, or manually:

```bash
curl -s -X POST http://localhost:8080/api/v1/models \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"<id>","name":"churn-classifier","version":"1",
       "artifact_uri":"models:/m-...","metrics":{"accuracy":0.968}}'
```

Each model carries `metrics`, a **quality gate** status, a **stage**, and (once
deployed) an `endpoint_url` and `deployment_status`. The console's Models tab shows
a per-version quality bar chart and cards with the gate, stage, and metrics.

## Promotion

Move a model between stages (e.g. `candidate` → `production`):

```bash
curl -s -X POST http://localhost:8080/api/v1/models/<id>/promote \
  -d '{"stage":"production"}'
```

## Deploying to a live endpoint

Deployment is **real** — the serving-manager launches an `mlflow models serve`
container for the model version and records the endpoint URL:

```bash
curl -s -X POST http://localhost:8080/api/v1/models/<id>/deploy \
  -d '{"canary_weight":0}'
```

1. The gateway calls the serving-manager (`POST /deployments`).
2. The manager starts the container on the platform network and returns the URL
   (e.g. `http://mlaiops-serve-churn-classifier:5001`).
3. The gateway records it and marks the model `serving` — or, if the manager
   rejects it, marks it `failed` (fail-closed, `502`).

The model card then shows a green **● live** tag and a **Test** button.

## Predicting

Hit the live endpoint through the gateway (it proxies to `/invocations`):

=== "Console"

    Click **Test** on a live model, edit the payload, **Send prediction request**:

    ```json
    {"predictions": [1]}
    ```

=== "API"

    ```bash
    curl -s -X POST http://localhost:8080/api/v1/models/<id>/predict \
      -H 'Content-Type: application/json' \
      -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
    ```

## Canary & rollback

- **Canary weight** (on deploy, or via agent traffic for agents) splits traffic
  between versions behind the edge router.
- **Rollback** removes the serving container and reverts:

    ```bash
    curl -s -X POST http://localhost:8080/api/v1/models/<id>/rollback -d '{}'
    ```

## Avoiding training-serving skew

A model trained under one library version can fail to load under another. Nexus
prevents this by **pinning the trainer, the serving image, and the workbench to the
same versions** (`mlflow==3.1.1`, `scikit-learn==1.7.0`). If you change a pin, change
it in all of: `python/pipelines/Dockerfile`, `deploy/mlflow/Dockerfile`, and
`deploy/jupyter/Dockerfile`.

## Kubernetes fidelity path

On the scale path, serving is KServe/Knative and the operator reconciles a
`NexusModelPromotion`. Locally and on a single VM, mlflow-serve containers provide
the identical capability without Kubernetes.
