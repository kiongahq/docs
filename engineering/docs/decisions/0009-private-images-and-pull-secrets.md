---
description: Keep Kionga's container images as private GHCR packages and supply registry credentials in every deployment, including to pods the operator creates.
status: "accepted"
date: 2026-10-23
---

# 0009 Private GHCR images, pulled with registry credentials

## Context and problem statement

Kionga's images are published to `ghcr.io/kiongahq/<image>` by the reusable image
workflow, and the packages are private. The workspace (Jupyter, IDE) and agent pods
that the operator creates could not pull them, and a single-server install failed with
a stack trace on the first pull. How should deployments obtain private images?

## Decision drivers

- Every pod that runs a Kionga image must be able to pull it, including pods the
  operator creates in the workload namespace.
- The operator must not gain access to credentials it does not need.
- Installations without a private registry must keep working unchanged.
- Failures must explain the fix.

## Considered options

- Keep the packages private and pass registry pull secrets everywhere
- Make the packages public

## Decision outcome

Chosen option: **Keep the packages private and pass registry pull secrets everywhere**.

- Helm `imagePullSecrets` (default empty) applies to platform pods and is also passed to
  the operator as `KIONGA_IMAGE_PULL_SECRETS`, a comma-separated list of Secret names.
- The operator references those Secrets from every workspace and agent pod it creates.
  The Secrets must exist in the workload namespace; the operator only references them,
  so it needs no new access to credentials.
- The single-server installer explains, on a failed pull, how to log in to `ghcr.io`
  with a token that has `read:packages`.

### Consequences

- Good, because every deployment path documents and tests how private images are
  pulled.
- Bad, because every installation needs a registry credential: a
  `kubernetes.io/dockerconfigjson` Secret in the release namespace and in the workload
  namespace, or `docker login ghcr.io` on a server.
- Neutral, because with no pull secrets configured the chart renders exactly as before.

### Confirmation

`test_private_registry_pull_secrets_reach_every_pod` and
`test_no_pull_secrets_by_default` in `deploy/tests/test_production_deploy.py`;
`test_vm_pull_failure_explains_private_registry_login` for the installer;
`platform/go/internal/operator/pull_secrets_test.go` for the operator.

## Pros and cons of the options

### Private packages with pull secrets

- Good, because image access stays under the organization's control.
- Bad, because it adds a credential to every installation.

### Public packages

- Good, because no credential is needed.
- Bad, because it changes who can pull the images; the history records the packages as
  private and keeps them so.

## More information

Written after the fact from `platform` commit `8e2d53c` and `deploy` commit `7ff9528`
(both 2026-10-23), which state that the GHCR packages are private. The same change
fixed the operator's default trace-proxy image name from the pre-rename organization to
`ghcr.io/kiongahq`. The history does not record why the packages are private; this
record documents the consequence, not that reason.
