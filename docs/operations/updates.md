---
title: Updates and rollback
description: Choose component versions, verify packages and plan a safe Kionga update.
---

# Updates and rollback

This guide shows you how to update an existing Kionga installation to a new
release, check that it works, and roll it back if it does not. Kionga is under
active development. Review the [changelog](../changelog.md) and compatibility
notes before you update. Component versions are independent; matching version
numbers do not establish compatibility.

## Before you begin

- Know which deployment you operate: the [local stack](local.md), a
  [single server](public-vm.md) or [Kubernetes](managed-kubernetes.md).
- Keep the current image digests, package versions and deployment
  configuration under version control or in a reviewed record. You need them to
  roll back.
- Have a recent backup of PostgreSQL, object storage and
  `KIONGA_CREDENTIAL_KEY`. See
  [Backups and recovery](production-operations.md#backups-and-recovery).
- Have an isolated environment with the same component versions and
  configuration shape as the target installation.

## Choose a release

Use a published release with a successful publishing workflow and the expected
artifacts. A Git tag alone does not confirm that packages are available.

| Artifact | Location | Version reference |
| --- | --- | --- |
| Service and workspace images | GitHub Container Registry under `kiongahq` | Exact `X.Y.Z` tag; pin the image digest for deployment |
| Python SDK | GitHub Releases; PyPI publication is [on hold](https://github.com/kiongahq/sdk-python/issues/29) | Exact package version |
| Kubernetes chart | Deployment repository's GitHub Releases | Chart archive and checksums |
| Contract schemas | Contracts repository's GitHub Releases | Versioned source archive and checksums |
| Documentation | This site and the documentation repository's releases | Documentation version, independent of software versions |

New container publication uses `edge` and commit references for development
builds. Existing `latest` tags are historical references and stop receiving
updates under this release process. Do not use them for new installations.
Release image digests are recorded in the release's attached files.

## Apply an update

1. Read the release notes for every component you plan to change. Check API,
   schema, runtime and SDK compatibility, including required migrations.
2. Download the artifacts and verify the supplied checksums. Record the selected
   image digests and package versions in a reviewed deployment configuration.
3. Back up persistent data and record the current configuration. Confirm whether
   any migration changes the rollback procedure.
4. Test the update in an isolated environment using the same component versions
   and configuration shape as the target installation.
5. Apply the update to the target installation:

    === "Local stack"

        Pull every clean checkout, then rebuild the images whose sources changed
        and start the stack again. `make -C deploy local-up` reuses cached images
        even when their sources changed, so use `local-build-up` after an update:

        ```bash
        make -C deploy workspace-pull
        make -C deploy local-build-up
        ```

    === "Single server"

        Replace the image digests in `deployment.json` with the reviewed digests
        of the new release, then run the start command again. Expect a short
        outage: there is one gateway.

        ```bash
        make -C deploy public-up DEPLOYMENT=/etc/kionga/deployment.json
        ```

    === "Kubernetes"

        Update the image digests in your values overlay, check the release, then
        install it. Promote the same digests through staging first.

        ```bash
        bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml
        bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml --apply
        ```

        The script runs `helm upgrade --install` with `--atomic --wait` and a
        15-minute timeout. If the upgrade fails, Helm rolls it back.

6. Verify health, authentication, workspace access, pipelines, model serving
   and agent execution, as described in [Verify](#verify).

Dependency-update pull requests follow the same tests and review requirements
as application changes. They do not automatically update running installations.

## Verify

1. Check that the gateway reports ready. It answers `{"status":"ready"}` when
   it can reach PostgreSQL:

    === "Local stack"

        ```bash
        export GATEWAY="${GATEWAY:-http://localhost:8080}"
        curl -s "$GATEWAY/api/v1/ready"
        make -C deploy local-status
        ```

    === "Single server"

        ```bash
        curl -s https://<your-domain>/api/v1/ready
        docker compose -p kionga-public ps
        ```

    === "Kubernetes"

        ```bash
        kubectl --context CONTEXT -n kionga-system rollout status deployment/kionga-gateway
        kubectl --context CONTEXT -n kionga-system get deployments -o wide
        helm history kionga --kube-context CONTEXT -n kionga-system
        ```

        The `IMAGES` column of the second command shows the digests that run.
        They match the digests you recorded in step 2. `helm history` lists the
        new revision last.

2. Run the acceptance checks for your deployment:

    - Local stack: `make -C deploy smoke`. The stack is healthy when there are
      zero failures.
    - Kubernetes: `deploy/scripts/verify-production.py`, as in
      [Verify](managed-kubernetes.md#verify). It prints
      `Acceptance failed: <reason>` and exits with status 1 when a check fails.
    - Single server: sign in, and run the checks in
      [Verify](public-vm.md#verify).

3. Work through the [acceptance checklist](production-operations.md#acceptance-checklist)
   for the features your users rely on.

## Roll back

Keep the previous image digests, package versions and deployment configuration.
Restore those references if an update fails and the release permits rollback.
For schema or data migrations, follow the release's recovery instructions;
reverting an image does not revert stored data.

=== "Single server"

    Restore the previous digests and configuration, then run the start command
    again. Back up PostgreSQL before every upgrade.

=== "Kubernetes"

    ```bash
    helm history kionga --kube-context CONTEXT -n kionga-system
    helm rollback kionga REVISION --kube-context CONTEXT -n kionga-system --wait --timeout 15m
    ```

    Rollback restores Kubernetes manifests only. It does not restore databases,
    custom resource definitions, external secrets or user data.

Never move a published version tag or overwrite its package to repair a release.
Publish a patch release with the correction and document affected versions.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Deployment failed: ... must be pinned to a verified SHA256 image digest` (single server) | `gateway_image` or `caddy_image` uses a tag | Use `repository@sha256:<64 hex characters>` |
| `Could not pull the pinned images` (single server) | The `ghcr.io/kiongahq` images are private, the digest is wrong, or the server cannot reach the registry | Sign in with a token that has `read:packages`, then check the digests and outbound HTTPS |
| `images.<name> must be an immutable repository@sha256:digest` (Kubernetes) | An image in your overlay uses a tag | Pin every image by digest |
| The upgrade fails and Helm rolls the release back (Kubernetes) | `--atomic --wait` with a 15-minute timeout: a pod did not become ready in time | Read the events and pod logs in `kionga-system`, fix the cause and run the update again |
| The gateway exits with `open PostgreSQL repository: migration <file>: <error>` | A database migration failed. Gateway replicas apply migrations one at a time under a PostgreSQL lock | Read the error. Reverting the image does not revert stored data, so follow the release's recovery instructions or restore the backup you took in step 3 |
| `dirty, not updated: <repo>` from `make -C deploy workspace-pull` (local stack) | That checkout has uncommitted changes, so the command skipped it | Commit or discard your changes in that checkout, then run the command again |
| `pull failed: <repo>` from `make -C deploy workspace-pull` (local stack) | The checkout cannot fast-forward | Resolve the branch state in that checkout, then run the command again |
| A service is unhealthy after a local update | Images are stale, or a service did not start in the right order | Follow [The stack is broken after an update](troubleshooting.md#the-stack-is-broken-after-an-update). None of its steps deletes data |
| A rotated secret has no effect | Kionga reads secret files only at startup | Restart the components that use it. On Kubernetes, `kubectl --context CONTEXT -n kionga-system rollout restart deployment/kionga-gateway` |

## Related pages

- [Changelog](../changelog.md)
- [Production readiness](production-operations.md)
- [Run locally](local.md#update)
- [Deploy on a single server](public-vm.md#upgrade-and-roll-back)
- [Deploy on Kubernetes](managed-kubernetes.md#upgrade-and-roll-back)
- [Managed operations](managed-operations.md#upgrades)
