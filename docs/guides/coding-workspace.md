---
description: Start and open the browser IDE, install VS Code extensions, and generate project starters with Codex, Claude Code, or your own coding agent.
---

# Use the browser IDE and coding agents

The browser IDE is code-server, the open-source browser build of VS Code. It
shares the `/workspace` volume with the [Jupyter workbench](workbench.md), so a
project you create in one appears in the other. This guide covers starting and
opening the IDE, installing extensions, and generating code with coding agents.

## Before you begin

- You can open the IDE: the `ide` service for a normal user, or the `engineer`,
  `operator` or `admin` role. Viewers and personal API keys cannot open
  workspaces.
- On Compose, the IDE is optional. An operator starts it with the steps in
  [Start the IDE on Compose](#start-the-ide-on-compose). On Kubernetes, the IDE
  is part of each user's workspace when the `ide` service is assigned.
- To use Codex or Claude Code without signing in to them interactively, an
  operator sets `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `deploy/.env`.

## Start the IDE on Compose

Run these commands from the folder that holds your Kionga checkouts.

1. Start the IDE:

    ```bash
    make -C deploy ide-up
    ```

    The first run downloads the code-server image.

2. Optional: to add the Codex and Claude Code command-line tools to the IDE
   terminal, build the larger agents image instead:

    ```bash
    make -C deploy ide-agents-up
    ```

    This downloads Node.js and both pinned tools, so it takes longer. The
    Jupyter workbench already includes them.

The IDE has no published port. It opens only through the gateway, which signs
you in with your console session. Never publish its internal port.

**Verify:** in the console, **Settings > Developer workspaces** shows **Browser
IDE** as `Ready · uses your Kionga session` instead of `IDE is offline`.

To stop the IDE without deleting any files, run `make -C deploy ide-down`.

## Open the IDE

1. Sign in to the console.
2. Open the IDE in one of these ways:
    - In the sidebar, click **IDE workspace ↗**.
    - Open a project and click **Open in IDE ↗** to open its folder,
      `/workspace/projects/<namespace>`.

The IDE opens at `/workspace.html?tool=ide`. The workspace toolbar switches to
JupyterLab and back to the console. If the link says the IDE is offline, an
operator runs `make -C deploy ide-up`, and then you click the link again.

**Verify:** the IDE opens with `/workspace` or the project folder in the
explorer.

## Install VS Code extensions

code-server installs extensions from [Open VSX](https://open-vsx.org), not from
the Microsoft marketplace, so some proprietary extensions are missing or do not
work.

1. Open **Extensions** in the IDE, search for an extension (for example
   **Claude Code for VS Code**), and install it. Or run this in the IDE terminal:

    ```bash
    code-server --install-extension anthropic.claude-code
    ```

2. To install a trusted `.vsix` file you downloaded, use **Extensions: Install
   from VSIX** or pass the file to `code-server --install-extension`.

Extensions, their settings and user data are stored under
`/workspace/.kionga/ide`, so they survive IDE restarts and image upgrades.
User-level Python packages go to `/workspace/.kionga/ide/python-user`, and with
the agents image, `npm install --global` writes to `/workspace/.kionga/ide/npm`.
An extension's own account sign-in is separate from your Kionga session.

**Verify:** `code-server --list-extensions --show-versions` lists the extension.

If an install fails with `EAI_AGAIN`, the workspace cannot resolve `open-vsx.org`
or `openvsx.eclipsecontent.org`. Retry when the workspace has internet access.

## Generate a starter with a coding agent

`kionga scaffold` generates a runnable starter from a template, and can hand it
to a coding agent that works only inside the new folder. Run it in the IDE
terminal or the Jupyter terminal.

1. Check which agents are ready:

    ```bash
    kionga agents
    ```

    The output shows whether `codex` and `claude` are installed and have
    credentials, and whether a custom agent is configured.

2. Generate the starter and pass the task to an agent:

    ```bash
    kionga scaffold churn-service \
      --template production-ml \
      --agent codex \
      --prompt "Train, evaluate, and expose a churn classifier with tests"
    ```

    Use `--agent claude` for Claude Code, or `--agent none` (the default) for a
    starter without any LLM.

3. Review the agent's changes and run the tests before you commit.

Kionga runs Codex in its `workspace-write` sandbox and starts Claude Code in the
generated folder with edit acceptance. The agent gets your prompt plus an
instruction to work only in that folder and not to access credentials.

The templates are `production-ml`, `distributed-training`, `production-agent`,
`fullstack-ai` and `blank-python`. For larger work, create the project in the
console or the API first and run its scaffold command, so the template version,
framework, accelerator and profile are recorded on the project. See
[Create a project from a template](project-templates.md).

**Verify:** the command prints `Created /workspace/churn-service` (or the folder
under your `KIONGA_WORKSPACE`), and the agent's changes are in that folder.

### Use another command-line agent

Connect any command-line agent that accepts a task as its last argument:

```bash
export KIONGA_CUSTOM_AGENT_COMMAND="your-agent --non-interactive"
kionga scaffold experiment --template production-ml --agent custom \
  --prompt "Build a reproducible classification experiment"
```

Kionga runs the command from the new project folder and appends the task as the
final argument. Configure only agents whose permission model you understand.

## Run agents directly

Codex and Claude Code are installed in the Jupyter workbench, and in the IDE
when you use the agents image. Start them in a terminal:

```bash
codex
claude
```

Their sign-in and configuration state is stored in separate volumes, not in
your project files.

## Security notes

- Agent API keys come from the deployment environment and are never written
  into projects.
- JupyterLab and the IDE share source files, but only JupyterLab mounts object
  storage as files.
- On Compose, all users share one IDE and one workspace volume, so the paths
  above are shared. On Kubernetes, each user's workspace has its own volume.

## Next steps

- [Scaffold a project](scaffolding.md) from the console.
- [Connect a project to Git](distributed-workspaces.md#connect-a-project-to-git).
- [Work in the Jupyter workbench](workbench.md).
