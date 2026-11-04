---
icon: material/account-group-outline
description: Define reusable agents, group them into a team with a coordinator, start a run, approve side effects, resume after a failure, and understand what a sandbox does and does not protect.
---

# Build and run an agent team

An agent team is a coordinator and a set of reusable agents. When you start a run,
the coordinator splits the work and starts parallel workers. Workers use tools and
code sandboxes, then hand back reports. You can do all of this from the console
without writing code.

For exact fields, tools and events, see the
[Agent teams reference](../reference/agent-teams.md).

## Before you begin

- You need the `agents` service and access to the project. Viewers can read agents,
  teams and runs but cannot change or start them.
- Teams call the designer runner for model calls. On a single server, enable it in
  your deployment file; see
  [Enable sandboxes on a single server](../operations/sandboxes.md#enable-sandboxes-on-a-single-server).
  The local stack (`make local-up`) starts it, and without provider keys it uses the
  `mock` chat model; see [Run with the mock model](#run-with-the-mock-model).
- Agents that run code need a sandbox runtime. If yours has none, sandbox tools
  report `sandbox_unavailable` and other agents keep working. See
  [Sandboxes and gVisor](../operations/sandboxes.md).

## 1. Define the agents

An agent definition is a reusable role. A team references it, and a coordinator
starts it by name.

1. Open **Agents**, then the agent definitions list, and create an agent.
2. Set **Name**, for example `bug-fixer`. Use lowercase letters, digits and hyphens.
   The name is unique in the project.
3. Set **When to use**. The coordinator reads this to choose an agent, so describe
   the work the agent suits.
4. Set **Instructions**, the agent's system prompt.
5. Set **Model**. `llm` uses the runtime's configured model.
6. Pick **Tools** from your project's resources. See [Tools](#choose-tools).
7. Set **Workspace** to **Sandbox** if the agent runs code or uses git. Otherwise
   leave it at **None**.
8. Adjust the limits on turns, tokens and time if needed, then save.

Every save creates a new revision, and Kionga keeps the last 20. Editing an agent
never changes a run that has already started.

### Choose tools

An agent can use only what its definition grants.

| Grant | What the agent gets | Needs approval |
| --- | --- | --- |
| Sandbox | Commands and file tools in its own sandbox | No |
| Git repository | Clone, diff and push for one repository | Push only |
| Tool | One registered tool | Yes |
| API connection | One API connection | Yes |
| Knowledge base | One knowledge base | No |
| Dataset | One dataset | No |

## 2. Create the team

1. Open the teams list and create a team. The `code-change` template (coordinator,
   bug fixer and reviewer) and the `research` template (coordinator, researcher and
   writer) give you a starting point.
2. Set **Name** and **Description**.
3. Set **Coordinator instructions**: how to split the work, which members to start,
   and how to check their reports.
4. Set **Coordinator model**.
5. Add 1 to 16 members.
6. Set **Shared brief**, the rules appended to every agent's system prompt.
7. Set the team limits: total workers, concurrent workers, tokens and time. Save.

## 3. Start a run

1. On the team, select **Start** and enter the task.
2. Decide whether to allow side effects. If you leave them off, any call to a tool
   with an external effect fails with `side_effects_not_approved` and nothing runs.
   See [Approve side effects](#5-approve-side-effects).
3. Start the run.

To start one through the API:

```bash
curl -X POST http://localhost:8080/api/v1/team-runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"team_id": "agt-...", "input": "Fix the failing date test", "allow_side_effects": false}'
```

The run keeps a snapshot of the team and its member definitions, so later edits do
not affect it.

## 4. Follow the run

The run view shows a live worker table with status, turns, tokens and time. It also
shows each worker's transcript, the message feed, pending approvals and the final
report. A banner appears when sandboxes are unavailable or the runtime is unsafe.

### How the coordinator behaves

- It starts members with `spawn_worker`. Starting a worker never blocks it, so it can
  run several at once, up to the team's concurrent limit.
- It has no resource tools. It works through its members.
- It wakes only when a message arrives, so a coordinator waiting on workers uses no
  model calls.
- It can check work rather than trust a report, using read-only views of a worker's
  sandbox (`read_worker_file` and `worker_diff`).
- It ends the run with `finish`, which is refused while any worker is still live.

### How workers behave

- A worker's tools come only from its definition, filtered by the access of the
  person who started the run. Kionga checks that access again before every turn and
  every tool call.
- A worker cannot start other workers.
- A worker can message only the coordinator. It hands back a report with `finish`,
  which covers the result for each item, the evidence, what was not verified, and
  follow-ups.
- A message to a completed worker resumes it with its transcript.
- If a worker exceeds its own limits, it fails and the coordinator is told. If the
  team exceeds its limits, the run fails with `budget_exceeded` and live workers are
  cancelled.

### Send a message

Use the message box in the run view, or `POST /api/v1/team-runs/{id}/messages`. Your
messages are the only ones an agent treats as instructions. Everything from a worker
or a tool reaches the model marked as data.

## 5. Approve side effects

Calls to `tool`, `connection` and `git_push` have external effects. What happens
depends on the choice you made when you started the run:

| Side effects | Result of the call |
| --- | --- |
| Not allowed | Returns `side_effects_not_approved`. Nothing runs. |
| Allowed | Creates an approval, and the worker waits in `waiting_approval`. |

- Only a person can approve: the person who started the run, or a project member with
  write access to agents.
- A message from an agent never grants anything, including a message that claims
  someone approved.
- A waiting worker has no timeout of its own. The run's time limit still applies.
- If you reject the call, the model receives an error result and can choose another
  approach.

Commands and file edits in a sandbox have no external effect, so they need no approval.

## 6. Resume after a failure

Runs are durable. Kionga handles most interruptions without you:

| What happened | What Kionga does |
| --- | --- |
| The gateway restarted | Another gateway picks up the worker when its 60 second lease expires. |
| The provider rate limited a call | The worker waits in `waiting_retry`, honoring the provider's delay. This does not use a turn. |
| The provider is unavailable | The worker retries in the same way. After 30 minutes of consecutive failure, it fails with a resumable error. |
| A tool call was interrupted | A read-only tool runs again. A tool with side effects is never repeated, and the model receives `outcome_unknown`. |

When a worker has failed and you have fixed the cause, select **Resume** in the run
view or call `POST /api/v1/team-runs/{id}/resume`. Failed workers go back in the
queue with their transcripts.

!!! warning "Check the external system first"
    `outcome_unknown` means the call may or may not have taken effect. Before you
    repeat the action, check the external system, for example whether the branch
    was pushed.

If the person who started the run is suspended or loses access to the project, the
run fails with `owner_access_lost`.

## What a sandbox protects

A sandbox limits what code from a model can do to the machine it runs on. Each worker
gets its own sandbox the first time it needs one.

- **Kernel isolation.** The code runs under gVisor, which handles its system calls in
  a separate kernel in user space. If gVisor is missing, sandboxes are refused. Kionga
  does not fall back to another runtime.
- **No network.** A sandbox cannot reach the internet, your cluster or the host.
- **No credentials.** A sandbox has no credentials in its environment, no engine
  socket and no host mounts.
- **Reduced privileges.** It runs as a non-root user with a read-only root filesystem,
  no capabilities, `no-new-privileges` and default `seccomp`.
- **Limits.** By default, a sandbox has 512 processes, 2 GiB of memory and 2 CPU cores.
  Commands time out after 120 seconds unless a call asks for longer, up to 1800.
- **Approved images only.** The image must be on your digest-pinned allowlist.
- **Separated git credentials.** A short-lived helper container does the clone or
  push, and the credential never enters the sandbox. The helper has its own network
  access; see the [known limit](../operations/sandboxes.md#limits). Pushes go only to a
  `kionga/<run-id>/<name>` branch, never to the default branch, and never force or
  delete.

## What a sandbox does not protect

- **The correctness of the work.** A sandbox says nothing about whether the code or a
  report is right or safe. Review a pushed branch as you would review any untrusted
  contribution.
- **Prompt injection.** A file, web page or tool result can try to steer an agent.
  Kionga marks that content as data and refuses to treat it as approval, which lowers
  the risk but does not remove it. An agent that was steered can still misuse the
  tools you granted.
- **Data you give the agent.** Anything in a task, a repository or a tool result is
  sent to your model provider. An agent can also include it in a branch it pushes,
  after approval.
- **Tools outside the sandbox.** `tool` and `connection` grants run with the access you
  configured, not in a sandbox. Approval is the control, so read each request.
- **Other people's sandboxes on a shared host.** Sandboxes share hosts or nodes, so
  isolation between tenants relies on gVisor alone.
- **Flaws in gVisor or the host.** gVisor reduces the kernel's exposure and does not
  eliminate it. On a single host, the sandbox manager's engine access is equivalent
  to root.
- **A development opt-in.** With the unsafe runtime, sandbox code shares the host
  kernel and a kernel exploit escapes. Public and Kubernetes deployments refuse it.

## Limits

Agent teams do not include:

- **Egress allowlists for sandboxes.** A sandbox has no network at all. You cannot grant
  it access to selected hosts.
- **Nested teams.** Workers cannot start workers, and a team cannot be a member of
  another team.
- **Teams as a canvas node.** You cannot place a team in an Agent Designer graph.
- **Deployment as a long-lived service.** The operator does not deploy teams. Teams run
  from the console and the API.
- **Per-tenant sandbox node pools.** All sandboxes in a deployment share one namespace
  and its nodes.

## Run with the mock model

Without a provider key, the `mock` chat model follows a fixed script, so you can try
the whole flow at no cost. The coordinator starts each member once, waits, then
finishes with a summary. Each worker runs one safe command if it has a sandbox, then
finishes. The output shows that the flow works, and says nothing about the quality of
a real model's work.

## Check the result

A successful run has status `succeeded` and a final report in the run view. The run
also records its usage and resume count, and writes `team_run.*` audit events.
