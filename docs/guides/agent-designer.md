---
icon: material/vector-polyline
description: Build an agent graph in the native Agent Designer, test it in the playground, debug a failed node, evaluate it against test cases, publish an immutable version, deploy it and roll back.
---

# Build agents in the Agent Designer

The Agent Designer is Kionga's native visual agent builder. You draw a graph of
typed components, run it in a playground with a node-by-node trace, check it
against regression test cases, and publish an immutable version that runs and
deploys without the editor.

Graphs are data, not code. Each node is a registered component that the
isolated **designer runner** (part of `agent-runtime`) interprets. Graphs store
the IDs of Kionga resources such as models, knowledge bases and API connections,
never their credentials. Kionga checks your project access on every resource
call.

## Before you begin

- You need the `agents` service and access to the project. Viewers can open
  designs but cannot change or run them.
- The playground and evaluations need the designer runner. The local stack
  (`make local-up`) starts it as `agent-designer-runner`. If it is missing, **Run**
  reports *The agent designer runner is not configured*.
- Without provider keys, the stack uses the deterministic `mock` chat model. To
  use a real model, set `MLAIOPS_LLM_BACKEND` and the provider key (see
  [Build agents](agents.md#using-a-real-llm)). Model calls go out through the
  trace-proxy.

## 1. Build a prompt → model → output agent

1. Open **Agents → Agent designer**.
2. Choose **New design**, then a project.
3. Add a **Prompt** node and set its template to `Answer briefly: {input}`.
4. Add a **Model** node. **Platform chat model** (`llm`) uses the runtime's
   configured model. A Kionga model ID calls that deployed model instead.
5. Connect **Input → Prompt → Model → Output**. Select a node's output port (on
   its right edge), then the next node's input port.
6. Select **Validate**. The **Validation** tab lists any errors, and badges
   appear on the affected nodes. Select **Show node** to jump to one.
7. Select **Save revision**.

Templates can use these placeholders:

| Placeholder | Value |
| --- | --- |
| `{input}` | The user's message. |
| `{context}` | Every value flowing into the node, joined by blank lines. |
| `{node-id}` | The output of one upstream node, for example `{retrieve}`. |

Substitution happens once and is literal. Text from a user or a tool is never
scanned again for placeholders.

## 2. Build a RAG assistant with a knowledge base and RustFS

1. Under **Start from**, choose **RAG assistant**.
2. On the **Search knowledge** node, choose a knowledge base. The list shows only
   the bases in your project. Queries are embedded with the SDK hashing embedder
   at the base's dimensions, so add chunks with the same embedder.
3. To ground the answer in a file instead, use the **Dataset-grounded answer**
   template. Pick a project dataset and an object key. Kionga reads the object
   from RustFS and keeps the read inside the dataset's prefix.
4. Save, then ask a question in the **Playground**. Expand the knowledge node's
   row in **Run trace** to see the retrieved text.

## 3. Build a tool-using agent with managed API credentials

1. An administrator registers an API connection for the project. The connection
   holds an endpoint and an `env:` credential reference; the secret stays on the
   gateway.
2. Start from **API lookup**, or add an **API call** node and choose the
   connection. The request template is rendered and sent as JSON. For example,
   `{"query": "{input}"}` is sent as is, and text that is not JSON is sent as
   `{"input": ...}`.
3. **Kionga tool** nodes invoke a registered tool's serverless function in the
   same way.
4. Tool and API calls can change external systems. In the playground, select
   **Allow tools and API calls that change external systems** before you run.
   Without it, the node fails with `side_effects_not_approved` and Kionga makes
   no call.

## 4. Debug a failed node and inspect its trace

Each run streams events into **Run trace**. A row shows a node's status, how
long it took, its tokens, and its redacted input and output. Kionga masks bearer
tokens, keys, passwords and similar values in these previews before they leave
the runner.

| Error code | Meaning | What to do |
| --- | --- | --- |
| `resource_denied` | Kionga refused the resource call (401, 403 or 404). | Check that the resource is still in the project and that your access is current. A revoked grant stops the next call, even in a running graph. |
| `resource_unavailable` | The backend or endpoint did not answer. | Retry. Nodes with a retry budget retry automatically. |
| `side_effects_not_approved` | A tool or API node ran without approval. | Allow side effects for the run. |
| `timeout` | A node exceeded its timeout, or the run exceeded `timeout_seconds`. | Raise the run limit, or simplify the node. |
| `budget_exceeded` | The run went over `max_steps` or `max_tokens`, or the runner is at capacity. | Raise the budget, or wait and run again. |
| `invalid_graph` | A setting is missing or invalid at run time. | Select **Validate**. |

To isolate a node, select it and choose **Test up to this node**. Kionga runs
the node and everything upstream of it, then stops. **Cancel** stops a running
graph, and its run credential stops working at once. Previous runs are listed
under the design (the newest 50 are kept).

Condition nodes route to a **T** (true) or **F** (false) branch. Only the
selected branch runs; nodes on the other branch show as `skipped`. A condition
is `operator:argument`: `contains:refund`, `not_contains:`, `equals:`,
`matches:<regex>`, `longer_than:<n>`, `empty` or `not_empty`.

## 5. Use templates, groups and revisions

- **Start from** opens a template as a new, unsaved design. **Import** loads a
  graph that was exported with **Export JSON**.
- To organize a large canvas, give nodes a **Group** label. Groups are visual
  only. Use **Fit** and the zoom buttons to navigate. **Undo** and **Redo**
  (Ctrl+Z / Ctrl+Shift+Z) cover graph edits.
- Every save creates a revision. If someone else saved first, your save is
  rejected and nothing is lost: reload, then reapply your change. Restore any of
  the 20 earlier revisions from the inspector, and save it as a new revision.
- Drafts saved before graph schema version 2 open unchanged. They gain port
  defaults when you open them. A free-text condition from an old draft still
  saves, but it must use the operator grammar before the draft can run.

## 6. Run evaluations, compare versions and enforce gates

1. In the playground, choose **Save as test case** after a good run. You can also
   add cases in **Test cases**. A case lists text the reply must contain or must
   not contain, and optionally an exact reply, a regular expression or a maximum
   latency. Matching ignores case. Save the cases.
2. In **Evaluations**, choose the saved revision or a published version, set the
   quality gate (the percentage of cases that must pass), and select **Run
   evaluation**. Cases run one at a time in the runner.
3. The table shows the pass rate, whether the gate passed, P95 latency, cost and
   failure reasons. Select **View** to see each case's reply and the assertion it
   failed. Select two evaluations, then **Compare selected**, to see which cases
   were fixed or regressed and how pass rate, latency and cost changed.

Every evaluation stores a copy of its cases, so you can reproduce it later. The
newest 20 evaluations per design are kept, along with any evaluation a published
version cites.

## 7. Publish, deploy, canary, monitor and roll back

1. In **Versions**, select **Publish**. A version is an immutable snapshot that
   records the saved graph, a behavior hash, the component registry version,
   the source revision and you as the author.
2. To gate the release, choose a passing evaluation of this exact revision under
   **Quality gate**. Kionga refuses the evaluation if it did not pass or if it
   tested different behavior.
3. Moving nodes or renaming them does not change behavior. Publishing again
   without other changes returns the existing version.
4. **Run** on a version executes it independently of the draft.
5. **Deploy** creates a managed agent on the Kubernetes agent runtime. Kionga
   mounts the version read-only, and the runtime refuses to start if the
   behavior hash does not match. To require a passing evaluation at deploy time,
   select **Only deploy versions published with a passing evaluation**. In the
   local Compose profile, Deploy reports that a managed runtime is required; use
   **Run** on the version instead.
6. Watch the deployment in **Agents**: readiness, sessions, traces, tokens and
   cost. Set canary traffic there.
7. To roll back, deploy an earlier version.

The metric cards at the top of the designer count designs, published versions,
deployments, runs over the last 24 hours, success rate, P95 latency and cost.
Each value comes from stored runs. A window with no runs shows a dash instead of
a number.

## Automate with the Python SDK

```python
from mlaiops_sdk import MLAIOpsClient

client = MLAIOpsClient()
template = next(t for t in client.agent_designer_templates() if t["id"] == "structured-extraction")
design = client.create_agent_design("prj-demo", "Order extractor", template["graph"])
run = client.run_agent_design(design["id"], "Ada wants order 42 refunded")
print(run["status"], run["output"])

cases = [{"id": "order", "input": "Grace needs order 7 cancelled", "expected": {"contains": ["7"]}}]
fixtures = client.get_agent_test_cases(design["id"])
client.save_agent_test_cases(design["id"], cases, revision=fixtures["revision"])
evaluation = client.evaluate_agent_design(design["id"], gate=0.9)
version = client.publish_agent_design(design["id"], design["revision"], evaluation_id=evaluation["id"])
client.deploy_agent_version(version["id"], require_evaluation=True)
```

See the [Agent graph reference](../reference/agent-graph.md) for schemas,
components, API routes, limits and security.
