# AI coding and IDE workspace

Kionga treats `/workspace` as the primary development surface. JupyterLab and
the optional browser IDE mount the same persistent volume, so a project created
in either interface appears immediately in the other.

## Start the IDE

```bash
make -C deploy ide-up
```

The first run downloads the code-server image and installs only the packages
needed for the editor. If you also want Codex and Claude Code CLI tools inside
the IDE terminal, run `make -C deploy ide-agents-up`; this optional image build downloads
Node.js and both pinned CLIs and can take longer. Jupyter's coding-agent tools
are unaffected.

Sign in to the console, then choose **IDE workspace**. It opens through the
authenticated gateway at `/workspace.html?tool=ide`; no separate password or
published IDE port is needed in Compose. The link explains when the IDE is
offline. Select a project first to open its shared folder. The workspace toolbar
switches between Jupyter and the IDE and takes you back to the console.
Stop it without deleting projects:

```bash
make -C deploy ide-down
```

The IDE is code-server, the open-source browser build of VS Code. It is an
opt-in Compose profile and is not exposed by the public deployment overlay.
If the IDE link says it is offline, run `make -C deploy ide-up` from the workspace folder,
then click the link again. The console checks readiness before launching it.

## Install AI coding extensions

Open **Extensions** in the browser IDE and install from Open VSX. For example,
search for **Claude Code for VS Code**, or run this in the IDE terminal:

```bash
code-server --install-extension anthropic.claude-code
code-server --list-extensions --show-versions
```

The IDE stores installed extensions, their settings and their user data under
`/workspace/.kionga/ide`, not in the replaceable container filesystem. They
survive IDE restarts and image rebuilds. A downloaded, trusted `.vsix` can also
be installed through **Extensions: Install from VSIX** or passed to
`code-server --install-extension`. code-server uses [Open VSX rather than the
Microsoft marketplace](https://github.com/coder/code-server/blob/main/docs/FAQ.md#why-cant-code-server-use-microsofts-extension-marketplace),
so some proprietary extensions may be unavailable or incompatible. If an
Open VSX install fails with `EAI_AGAIN`, retry when the workspace can resolve
`open-vsx.org` and `openvsx.eclipsecontent.org`; the extension registry is an
external service. The coding extension's own account sign-in is separate from
the Kionga session.

When using the optional `ide-agents-up` image, `npm install --global` writes
user-installed coding-agent CLIs to `/workspace/.kionga/ide/npm` instead of the
replaceable system path. User-level Python packages similarly use
`/workspace/.kionga/ide/python-user`.

Compose has one shared development workspace, so these paths are shared by its
users. On Kubernetes, each provisioned `KiongaWorkspace` has its own PVC, making
the same paths user-specific. For JupyterLab extensions and Python packages,
see the [workbench guide](workbench.md#install-your-own-coding-tools).

The Compose gateway and IDE build from the small `platform/go/` and
`workspace/` contexts. If Docker cannot download the Go builder image,
an operator with local Go installed can cross-compile into `platform/go/build/gateway`
and package that binary with `platform/go/Dockerfile.local` for the matching Docker CPU
architecture. This is a local recovery path, not the normal release build.

## Generate a starter

Run this in either the Jupyter terminal or the IDE terminal:

```bash
kionga scaffold churn-service \
  --template production-ml \
  --agent codex \
  --prompt "Train, evaluate, and expose a churn classifier with tests"
```

Canonical templates are `production-ml`, `distributed-training`,
`production-agent`, `fullstack-ai`, and `blank-python`. Use `--agent none` for a
deterministic runnable starter without an LLM, or choose `codex` or `claude`. The
[template catalog](project-templates.md) lists supported frameworks, accelerators,
required services, and generated boundaries.

Other command-line agents can be connected without changing Kionga:

```bash
export KIONGA_CUSTOM_AGENT_COMMAND="your-agent --non-interactive"
kionga scaffold experiment --template production-ml --agent custom \
  --prompt "Build a reproducible classification experiment"
```

Kionga appends the task as the final command argument and runs it from the new
project directory. Only configure agents whose permission model you understand.

```bash
kionga agents
```

shows whether each CLI and its API credential are available.

For substantial workloads, create the project through the API/console first and
run the returned `scaffold_command`. This preserves template version, framework,
accelerator, resource-profile intent, capabilities, and Git lineage in control-plane
state instead of leaving those decisions only in generated files.

## Direct agent use

Pinned Codex and Claude Code CLIs are installed in Jupyter, and in the IDE after
`make -C deploy ide-agents-up`:

```bash
codex
claude
```

For unattended scaffolding, Kionga runs Codex with workspace-write sandboxing.
Claude Code starts in the generated project with edit acceptance. Review agent
changes and tests before committing.

## Security boundary

- Agent API keys are injected from `.env`; they are not written into projects.
- Agent configuration volumes persist login/config state separately from code.
- The Compose IDE has no published port and delegates authentication to the
  Kionga gateway. Never expose its internal port directly to the internet.
- Jupyter and the IDE share source files, but only Jupyter receives FUSE and
  `SYS_ADMIN` for the object-store mount.

For production multi-user deployments, replace the single shared code-server
container with isolated per-user `KiongaWorkspace` pods. A GPU or custom resource
profile bounds the workspace; pipeline job requests are enforced separately.
