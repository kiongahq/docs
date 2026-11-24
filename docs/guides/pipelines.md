---
icon: material/graph-outline
description: Define a versioned pipeline in the console or YAML, keep it in Git, schedule it, run it with checked overrides, watch each node, and roll back to an earlier revision.
---

# Define and run pipelines

Define a pipeline, keep it in Git, schedule it, run it, watch each node, and roll
back to an earlier revision. A pipeline (a **flow**) is a versioned directed
acyclic graph (DAG) of container jobs or deployed functions. A **run** is one
execution of a flow. Every run records exactly what it executed: the flow
revision and its SHA-256, the image digests, the parameters and overrides, the
policy decision, and the workload that ran each node.

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
- **For the API and CLI:** export `KIONGA_URL`, and either sign in with a
  session cookie or export a personal API key with the `pipelines` scope as
  `KIONGA_TOKEN`. See [Authentication](../reference/api.md#authentication).

## Define a flow

1. Open **Pipelines** and click **Define flow**.
2. On the **Form** tab, set the **Project**, the **Execution** mode
   (**Containers / pipeline runner** or **Functions / OpenFaaS**), a **Name** and
   a **Version**.
3. Click **Add node** for each step. A node is a container image or a deployed
   function. Set what it runs after, its resources, retries and timeout.
   Dependencies decide what runs in parallel.
4. Optional: set a schedule, default parameters, and what a manual run may
   override.
5. Click **Validate**. The editor also validates as you type and shows a status
   such as `4 nodes, 3 stages, valid`.
6. When you edit an existing flow, enter a **Revision message**. Click **Save
   flow**.

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

## Keep a flow in Git

Review flows like code: keep them as `pipelines/<name>.kionga.yaml` in the project
repository, validate them in CI, and apply them after merge. Kionga never commits
to your repository.

1. Export the current definition:

    ```bash
    kionga-cli pipeline export <definition-id> > pipelines/churn.kionga.yaml
    ```

2. In CI, validate the file. The command prints each issue with its line number
   and exits with status 1 when the file is invalid:

    ```bash
    kionga-cli pipeline validate pipelines/churn.kionga.yaml
    ```

3. After the change merges, apply it with a change note:

    ```bash
    kionga-cli pipeline apply pipelines/churn.kionga.yaml <definition-id> "PR #42"
    ```

    Omit the definition ID to create a new flow. Applying unchanged YAML creates
    no revision.

## Review revisions, compare and roll back {#revisions-diff-and-rollback}

Each saved change creates an immutable revision with its author, message and
hash. Saving identical content does not.

1. Open **Pipelines** and select **Edit** in the flow's row. The **Revisions** panel
   lists each revision with its message, author and save time.
2. Click **Compare with current** on a revision to see a line diff.
3. Click **Roll back** to save that revision's content as a new revision. The
   console asks you to confirm first. The current revision shows
   **Current revision** instead of these buttons.

The flow's **Details** dialog also lists the revisions, with **View revision** and
**Restore revision** buttons.

History is never rewritten, and every run still points at the revision it
executed. The same operations are available through the API:

```bash
curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
  "$KIONGA_URL/api/v1/pipelines/definitions/<id>/revisions"
curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
  "$KIONGA_URL/api/v1/pipelines/definitions/<id>/yaml"
curl -s -X POST -H "Authorization: Bearer $KIONGA_TOKEN" \
  "$KIONGA_URL/api/v1/pipelines/definitions/<id>/revisions/<revision>/rollback"
```

## Schedule a flow

1. In the flow editor, under **Schedule**, select **Enable scheduled
   execution**.
2. Enter a five-field **Cron expression** and an IANA **Timezone**, such as
   `Africa/Nairobi`. The default timezone is `UTC`.
3. Save the flow.

The **Schedule** column of the flow list shows whether the schedule is active or
paused and when it runs next. When you edit an existing flow, the **Active
schedules** panel also shows when it last ran. Use **Pause** and **Resume** in
that panel, or in the **Schedule** section of the flow's **Details** dialog, to
stop and restart it.

Scheduled runs behave predictably:

- Each schedule slot runs at most once, even when the gateway restarts or runs
  as several replicas.
- After downtime, a schedule runs once for the most recent missed slot, not once
  for every missed slot.
- A scheduled run executes as the flow's owner, with the owner's project access
  and run quota at the moment the slot fires. If the owner lost access or is
  suspended, the slot is recorded as failed with the reason and the schedule
  moves on.

## Run a flow

1. Open **Pipelines** and click **Run pipeline**.
2. Choose the **Project** and the **Flow definition**, and enter a **Run name**.
   Defaults come from the flow's current revision.
3. Under **Parameters**, change values for this run. Parameters the flow does not
   mark as overridable are disabled.
4. Under **Node overrides**, if the flow allows it:
    - Run a subset of nodes. Kionga adds every node they depend on.
    - Replace a node's image. The image must be pinned by digest, and must come
      from an approved registry when the operator sets
      `KIONGA_IMAGE_REGISTRIES`.
    - Change CPU and memory within your grant, or change retries and timeouts.
    - Set **Maximum parallelism** (default 8, at most 64).
5. Click **Check run**. The preflight checks project access, your concurrent-run
   quota, the capacity of the widest parallel stage, image rules and engine
   availability, and lists exactly what this run changes under **Effective run
   configuration**.
6. Click **Submit run**. It is enabled only after the checks pass.

To run a flow from a script, use the CLI or the SDK:

```bash
kionga-cli pipeline submit <project-id> <definition-id>
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

### Rerun from a failure

1. On a failed run, click **Rerun from failure**. The new run reuses the recorded
   outputs of the nodes that succeeded, and runs the failed node and everything
   after it again. Reused nodes show as skipped, with the run they came from.
2. To stop a run, click **Cancel run**.

## Watch a run

1. Under **Run history**, select **Open run** in a run's row. The row shows the
   run's trigger, status, progress and start time. The run dialog shows its
   status, run ID, project, engine run ID, execution mode, progress and
   provenance (the flow revision and hash, the overrides and the policy
   decision), and the **Execution graph**.
2. Select a node, or select **Inspect node** in its row, to see its timing,
   attempt, dependencies, and its logs and events under **Node logs**. You can
   filter by severity and source, search, load earlier lines, and follow the live
   tail. Select **Show all run logs** to return to the whole run. See
   [Search and stream logs](logs.md).

Drag the graph's background to pan, and use its controls to zoom or fit it to the
view. Each node is a button, so you can reach it with **Tab** and open it with
**Enter**. Status is shown by color, symbol and text.

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

## Run container nodes as Kubernetes Jobs {#kubernetes}

On Kubernetes, the gateway can run container nodes as Kubernetes Jobs instead of
sending them to the Compose pipeline runner. The Jobs executor is the one pipeline
engine on Kubernetes: Kionga does not run pipelines on Kubeflow there. Compose
keeps Prefect.

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

## Verify

1. **Define:** the flow appears under **Flow definitions**, and the **Dependency
   graph** in its editor shows the nodes in the stages you expect.
2. **Git:** `kionga-cli pipeline validate <file>` prints `valid: <n> stage(s),
   sha256 <hash>`, and `kionga-cli pipeline apply` prints `<definition-id>
   revision <n> (sha256 <hash>)`.
3. **Revisions:** the revision list shows a new revision with the content of the
   revision you rolled back to.
4. **Schedule:** the flow shows the schedule as `Active`, with the next run time
   under **Active schedules**.
5. **Run:** the run appears under **Run history** with the status `queued` or
   `running`.
6. **Watch:** the run reaches `succeeded`, and every node shows an exit code and
   the image digest it ran.
7. **Kubernetes Jobs:** `kubectl get jobs -n kionga-pipelines -l
   kionga.dev/run=<run-id>` lists one Job per node attempt.

## Troubleshooting

A submission that fails the preflight returns `403` or `422` with `"error":
"preflight_failed"`. The `message` field holds the first failed check, and
`details` lists every check.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `line <n> (node <id>): dependency cycle: a → b → a` from `validate` or **Validate** | The nodes depend on each other in a loop. | Remove one dependency. Other checks print the same way, for example `node "<id>" depends on "<dep>", which does not exist`. |
| `executionMode must be prefect (containers) or functions (OpenFaaS)` | The `spec.executionMode` value is not one of the two. | Use `prefect` for container nodes or `functions` for function nodes. |
| `Parameter "<name>" cannot be overridden for this flow.` | The parameter is not listed in `spec.overridable.parameters`. | Add it to `overridable.parameters` and save a new revision, or run with the default. |
| `Parameter "<name>" is not declared by this flow.` | The run sets a parameter that `spec.parameters` does not declare. | Declare the parameter in `spec.parameters`. |
| `This flow does not allow image overrides.` (or `resource`, `retry or timeout`, `parallelism`, or `running a subset of nodes`) | The flow does not set that field as overridable. | Set `overridable` for the field in the flow and save a new revision. |
| `Override images must be pinned by digest (name@sha256:…), so the run is reproducible.` | The override image has no digest. | Use an image reference with an `@sha256:` digest. |
| `Image registry is not approved. Approved: <list>` | The image is outside `KIONGA_IMAGE_REGISTRIES`. | Use an image from an approved registry, or ask an operator to add the registry. |
| `403`, `concurrent run quota reached (<n>)` or `no concurrent run capacity has been provisioned` | You reached your concurrent-run quota, or your grant has none. | Wait for a run to finish, or ask an administrator for more capacity. |
| `403`, `pipeline layer <n> requests <x> CPUs but the grant provides <y>` (or memory, or GPUs) | The widest parallel stage needs more than your grant. | Lower the resources, add dependencies to run fewer nodes at once, or ask for a larger grant. |
| `No pipeline engine is configured (set PREFECT_API_URL or activate a Prefect connection on the Platform page).` | Container flows have no engine. | Set `PREFECT_API_URL`, or activate a Prefect connection. On Kubernetes, enable the [Jobs executor](#kubernetes). |
| `OpenFaaS is not configured (set OPENFAAS_URL or activate an OpenFaaS connection on the Platform page).` | A function flow has no function runtime. | Configure OpenFaaS on Compose, or use a Kubernetes install. |
| `Only failed or cancelled runs can be resumed.` | You started a rerun from a run that did not fail. | Rerun from a failed or cancelled run. |
| A node fails with `container <name> was killed for exceeding its memory limit (OOMKilled, exit <code>)` | The node's memory limit is too low. | Raise `resources.memory` for the node. |
| A node fails with `container <name> never started: <reason> <message>` | Kubernetes could not start the container, for example because the image cannot be pulled. | Fix the image reference or the registry access. The same events appear in the node's logs with the source `k8s`. |
| A node fails with `Job exceeded its timeout (activeDeadlineSeconds) and was stopped` | The node ran longer than its `timeoutSeconds`. | Raise `timeoutSeconds` (at most 24 hours), or make the node faster. |

## Related pages

- [Search and stream logs](logs.md) for a run.
- [Register and serve the model](models-serving.md) a pipeline trains.
- [Run container nodes as Kubernetes Jobs](#kubernetes).
- To write a native Prefect flow, see the pipeline runner in the
  [engineering handbook](https://kiongahq.github.io/docs/engineering-access/).
