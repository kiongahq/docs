# Contributing to the documentation

The documentation should help readers complete a task or answer a precise
question. Keep marketing claims out of procedures and distinguish code that
exists from integrations that have been tested in a live environment.

## Choose the right section

| Content | Section |
| --- | --- |
| First install and first successful run | Getting started |
| Platform concepts and architecture | Understand |
| A user task with steps and an expected result | Build |
| Exact fields, endpoints, permissions, or service contracts | Reference |
| Deployment, security, recovery, and incident procedures | Operations |

Add a page to `mkdocs.yml` under one primary section. Prefer linking to an
existing reference page over copying a table of settings into several guides.
Keep existing URLs stable when reorganizing navigation; add a redirect plan
before moving a published page.

## Page format

1. Use one descriptive `#` title and a short opening paragraph that states the
   page's purpose and scope. Avoid a heading called “Overview” immediately below
   the title unless it adds distinct information.
2. For a task guide, state prerequisites, then give steps in execution order.
   Show the expected result and link to troubleshooting or next steps.
3. For a reference, group facts by resource or interface. Use tables only when
   readers need to compare repeated fields; include units, defaults, and the
   owning component where relevant.
4. For an operations page, state the environment and trust boundary first.
   Include validation, rollback or recovery, and the evidence needed before
   admitting users.
5. Use sentence-case headings, fenced code blocks with a language, and relative
   links for pages in this repository. Keep examples copyable and avoid tokens,
   passwords, or personal hostnames except explicitly labeled local defaults.

## Accuracy and status

- Check commands, flags, paths, and defaults against the owning repository.
- Mark optional engines as optional. A control-plane API does not imply the
  external engine is installed or reachable.
- Do not describe mock-backed tests, a successful build, or a health endpoint as
  production acceptance. Update [implementation status](docs/reference/implementation-status.md)
  when a capability changes delivery or verification level.
- Document local credentials as development-only. Public deployment guidance must
  use the [production acceptance checklist](docs/operations/production-operations.md).
- Keep product agent documentation. Coding-assistant prompts and local assistant
  state do not belong in this repository.

## Review checklist

- [ ] The page has a clear audience, title, scope, and correct section in `mkdocs.yml`.
- [ ] Internal links and code examples work from the documented workspace layout.
- [ ] Security and deployment claims match the current implementation status.
- [ ] No secrets, machine-specific paths, generated site files, or assistant state
      have been added.
- [ ] `make docs-build` passes with strict mode.
