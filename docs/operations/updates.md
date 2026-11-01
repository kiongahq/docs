---
title: Updates and rollback
description: Choose component versions, verify packages and plan a safe Kionga update.
---

# Updates and rollback

Kionga is under active development. Review the [changelog](../changelog.md) and
compatibility notes before updating an installation. Component versions are
independent; matching version numbers do not establish compatibility.

## Choose a release

Use a published release with a successful publishing workflow and the expected
artifacts. A Git tag alone does not confirm that packages are available.

| Artifact | Location | Version reference |
| --- | --- | --- |
| Service and workspace images | GitHub Container Registry under `kiongahq` | Exact `X.Y.Z` tag; pin the image digest for deployment |
| Python SDK | PyPI as `mlaiops-sdk`, after publisher setup; GitHub Releases | Exact package version |
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
5. Apply the update, then verify health, authentication, workspace access,
   pipelines, model serving and agent execution.

Dependency-update pull requests follow the same tests and review requirements
as application changes. They do not automatically update running installations.

## Roll back

Keep the previous image digests, package versions and deployment configuration.
Restore those references if an update fails and the release permits rollback.
For schema or data migrations, follow the release's recovery instructions;
reverting an image does not revert stored data.

Never move a published version tag or overwrite its package to repair a release.
Publish a patch release with the correction and document affected versions.
