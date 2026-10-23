---
description: Define a versioned pipeline in the console or YAML, keep it in Git, schedule it, run it with checked overrides, watch each node, and roll back to an earlier revision.
---

# Define and run pipelines

A pipeline (a **flow**) is a versioned directed acyclic graph (DAG) of container
jobs or deployed functions. A **run** is one execution of a flow. Every run
records exactly what it executed: the flow revision and its SHA-256, the image
digests, the parameters and overrides, the policy decision, and the workload that
ran each node.

This guide covers defining a flow, keeping it in Git, scheduling it, running it,
watching a run, and rolling back.

## Before you begin

- **To create, edit, schedule or run flows:** the `pipelines` service for a normal
  user, or the `engineer`, `operator` or `admin` role, with access to the
  project. Viewers can read flows, runs and logs but cannot change or run them.
- **To override parameters, resources or images in a run:** the
  `pipeline:OverrideParameters`, `pipeline:OverrideResources` or
  `pipeline:OverrideImage` permission. The built-in roles that can run pipelines
  include them, and an administrator can remove them with a
  [policy](access-control.md).
- **An engine:** container flows run on Prefect through the bundled pipeline
  runner; function flows need OpenFaaS (see
  [Deploy a function](distributed-workspaces.md#deploy-a-function)). If no engine
  is configured, Kionga refuses the run and tells you why.
- **For the API and CLI:** export `MLAIOPS_URL`, and either sign in with a
  session cookie or export a personal API key with the `pipelines` scope as
  `MLAIOPS_TOKEN`. See [Authentication](../reference/api.md#authentication).

## Define a flow

1. Open **Pipelines** and click **＋ Define flow**.
2. On the **Form** tab, set the **Project**, the **Execution** mode
   (**Containers · pipeline runner** or **Functions · OpenFaaS**), a **Name** and
   a **Version**.
3. Click **＋ Add node** for each step. A node is a container image or a deployed
   function. Set what it runs after, its resources, retries and timeout.
   Dependencies decide what runs in parallel.
4. Optional: under **Schedule and parameters**, set a schedule, default
   parameters, and what a manual run may override.
5. Enter a **Change note** and click **Save flow**.

The **YAML** tab edits the same definition as a `kionga.dev/v1 Pipeline`
document. Kionga validates every change as you type and shows each problem
next to its field, node and YAML line. Switching tabs never loses changes. Kionga
stores YAML in canonical form, so your comments and key order are not kept.

```yaml
apiVersion: kionga.dev/v1
kind: Pipeline
metadata: {name: churn-training, project: prj-123, version: "3"}
spec:
  executionMode: prefect            # containers; use "functions" for OpenFaaS nodes
  parameters: {window: daily}
  overridable: {parameters: [window], resources: true, nodes: true}
  triggers:
    - {type: schedule, cron: "30 2 * * *", timezone: Africa/Nairobi}
  nodes:
    - {id: extract, type: container, image: ghcr.io/acme/churn@sha256:<digest>}
    - {id: features, type: container, image: ghcr.io/acme/churn@sha256:<digest>,
       dependsOn: [extract]}
    - {id: report, type: container, image: ghcr.io/acme/churn@sha256:<digest>,
       dependsOn: [extract], when: {param: window, equals: daily}}
    - {id: train, type: container, image: ghcr.io/acme/churn@sha256:<digest>,
       dependsOn: [features, report],
       resources: {cpu: "4", memory: 8Gi, gpu: 1},
       retry: {max: 2, backoffSeconds: 60}, timeoutSeconds: 7200}
```

Kionga rejects duplicate node IDs, dependencies on missing nodes, cycles (shown
as a path such as `a → b → c → a`), an invalid cron expression or timezone,
timeouts over 24 hours, more than 10 retries, and overridable parameters that are
not declared. For a normal user, it also rejects a flow whose widest set of
parallel nodes needs more CPU, memory or GPUs than the user's grant.

The JSON Schema for editor tooling is `pipeline/v1.schema.json` in the
[contracts repository](https://github.com/kiongahq/contracts), with examples in
`pipeline/examples/`.

**Verify:** the flow appears under **Flows**, and its **Dependency graph** shows
the nodes in the stages you expect.

## Keep a flow in Git

Review flows like code: keep them as `pipelines/<name>.kionga.yaml` in the project
repository, validate them in CI, and apply them after merge. Kionga never commits
to your repository.

1. Export the current definition:

    ```bash
    mlaiops pipeline export <definition-id> > pipelines/churn.kionga.yaml
    ```

2. In CI, validate the file. The command prints each issue with its line number
   and exits with status 1 when the file is invalid:

    ```bash
    mlaiops pipeline validate pipelines/churn.kionga.yaml
    ```

3. After the change merges, apply it with a change note:

    ```bash
    mlaiops pipeline apply pipelines/churn.kionga.yaml <definition-id> "PR #42"
    ```

    Omit the definition ID to create a new flow. Applying unchanged YAML creates
    no revision.

**Verify:** `apply` prints `<definition-id> revision <n> (sha256 <hash>)`.

## Review revisions, compare and roll back {#revisions-diff-and-rollback}

Each saved change creates an immutable revision with its author, message and
hash. Saving identical content does not.

1. Open the flow and click **Revisions**.
2. Click **Compare with current** on a revision to see a line diff.
3. Click **Roll back** to save that revision's content as a new revision.

History is never rewritten, and every run still points at the revision it
executed. The same operations are available through the API:

```bash
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/pipelines/definitions/<id>/revisions"
curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/pipelines/definitions/<id>/yaml"
curl -s -X POST -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "$MLAIOPS_URL/api/v1/pipelines/definitions/<id>/revisions/<revision>/rollback"
```

**Verify:** the revision list shows a new revision at the top with the old
content.

## Schedule a flow

1. In the flow editor, select **Run on a schedule**.
2. Enter a five-field **Cron** expression and an IANA **Timezone**, such as
   `Africa/Nairobi`. The default timezone is `UTC`.
3. Save the flow.

The flow list and detail show whether the schedule is active or paused and when
it runs next and last ran. Use **Pause** and **Resume** to stop and restart it.

Scheduled runs behave predictably:

- Each schedule slot runs at most once, even when the gateway restarts or runs
  as several replicas.
- After downtime, a schedule runs once for the most recent missed slot, not once
  for every missed slot.
- A scheduled run executes as the flow's owner, with the owner's project access
  and run quota at the moment the slot fires. If the owner lost access or is
  suspended, the slot is recorded as failed with the reason and the schedule
  moves on.

**Verify:** the flow shows the schedule as active with the next run time.

## Run a flow

1. Open **Pipelines** and click **▶ Run pipeline**, or click **▶ Run** on a flow.
2. Choose the **Project** and the **Flow**. Defaults come from the flow's
   current revision.
3. Under **Parameters**, change values for this run. Parameters the flow does not
   mark as overridable show a lock and the reason.
4. Under **Nodes**, if the flow allows it:
    - Run a subset of nodes. Kionga adds every node they depend on.
    - Replace a node's image. The image must be pinned by digest, and must come
      from an approved registry when the operator sets
      `KIONGA_IMAGE_REGISTRIES`.
    - Change CPU and memory within your grant, or change retries and timeouts.
    - Set **Maximum parallel nodes** (default 8, at most 64).
5. Click **Check run**. The preflight checks project access, your concurrent-run
   quota, the capacity of the widest parallel stage, image rules and engine
   availability, and lists exactly what this run changes.
6. Click **Start run**. It is enabled only after the checks pass.

To run a flow from a script, use the CLI or the SDK:

```bash
mlaiops pipeline submit <project-id> <definition-id>
```

```python
run = client.submit_pipeline("prj-123", definition_id="<definition-id>",
                             parameters={"window": "daily"})
```

The gateway runs the same preflight on every submission, so a hand-written
request cannot apply overrides that the flow, a policy or your quota does not
allow. The run's trigger is `manual` from the console and `api` from a
personal API key; the request cannot set it. A flow that declares no parameters
passes run parameters through unchecked, with a preflight warning.

**Verify:** the run appears under **Runs** with status `queued` or `running`.

### Rerun from a failure

On a failed run, click **Rerun from failure**. The new run reuses the recorded
outputs of the nodes that succeeded, and runs the failed node and everything
after it again. Reused nodes show as skipped, with the run they came from.

To stop a run, click **Cancel run**.

## Watch a run

1. Click a run under **Runs**. The page shows its status, trigger, owner, flow
   revision and hash, policy decision and overrides, and the execution graph.
2. Select a node to see its timing, attempt, exit code, workload, image digest,
   dependencies, and its logs and events. You can filter by severity and source,
   search, load earlier lines, and follow the live tail. See
   [Search and stream logs](logs.md).

The graph supports zoom, fit to view and dragging. With the keyboard, the arrow
keys move between nodes and **Enter** opens one. Status is shown by color, symbol
and text.

How nodes run:

- A node starts as soon as its own dependencies succeed, so independent branches
  run in parallel.
- A node whose `when` condition is false is skipped, and its dependents still run.
- Nodes after a failure are skipped with the reason, while unrelated branches
  finish.
- Each attempt honors the node's timeout and retry backoff.
- A run uses the revision that was current when you submitted it, so editing the
  flow does not change a queued run.

Each node reports its workload: `docker-container` with the container ID for
local container nodes, `openfaas-call` for function nodes, and `k8s-job` on
Kubernetes.

**Verify:** the run reaches `succeeded`, and every node shows an exit code and
the image digest it ran.

## Run container nodes as Kubernetes Jobs {#kubernetes}

On Kubernetes, the gateway can run container nodes as Kubernetes Jobs instead of
sending them to the Compose pipeline runner.

1. Create a dedicated namespace for pipeline jobs, with your NetworkPolicy and
   ResourceQuota.
2. In the Helm values, set `pipelineExecutor.kubernetes: true` and
   `pipelineExecutor.namespace` to that namespace (default `kionga-pipelines`).
   The chart sets `KIONGA_EXECUTOR=kubernetes` and `KIONGA_K8S_NAMESPACE` on the
   gateway and grants it only Jobs (create and delete) and Pods and Events (read)
   in that namespace.
3. Upgrade the release.

Each node attempt becomes one `batch/v1` Job, labeled
`kionga.dev/{tenant,project,run,node,attempt}`. The node timeout becomes
`activeDeadlineSeconds`, and Kionga drives retries itself (`backoffLimit: 0`).
Pods run as non-root with all capabilities dropped, no privilege escalation and
no service account token. Exit codes and reasons such as `OOMKilled` are recorded,
and Pod and Job events appear in the node's logs with the source `k8s`.

Limits to plan for:

- Container output is not streamed from Kubernetes pods into the Kionga log store
  yet. Read it with `kubectl logs` and the Job name shown on the node.
- Function nodes are not supported by this executor.
- The executor is tested against the Kubernetes API, not yet on a live cluster.
  Validate it in a staging cluster first.

**Verify:** `kubectl get jobs -n kionga-pipelines -l kionga.dev/run=<run-id>`
lists one Job per node attempt.

## Plan heavy and distributed training

Start with the [`distributed-training`](project-templates.md#create-a-gpu-training-project)
template for PyTorch DDP, and express the steps around the trainer as ordinary
nodes:

- Pin images by digest and record the Git commit.
- Write checkpoints to object storage at regular intervals.
- Make retries and resumes idempotent.
- Let only rank zero publish shared MLflow and registry results.
- Keep evaluation and registration in separate nodes so quality gates stay
  easy to audit.

## Security note for Compose

On Compose, the pipeline runner starts each container node through the host's
Docker socket. That suits a trusted laptop or a single-operator server, not
untrusted tenants. Child containers never receive the socket, and they run with
all capabilities dropped, `no-new-privileges` and a process limit. For
multi-tenant isolation, use the [Kubernetes executor](#kubernetes).

## Next steps

- [Search and stream logs](logs.md) for a run.
- [Register and serve the model](models-serving.md) a pipeline trains.
- To write a native Prefect flow, see the pipeline runner in the
  [engineering handbook](https://kiongahq.github.io/docs/engineering/components/execution/).
