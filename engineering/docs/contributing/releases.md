---
title: Release process
description: Version, review, publish and document Kionga component releases.
---

# Release process

Each public component owns its version, changelog and release artifacts. The
shared automation repository is versioned as well. The private demonstration
repository is not a distributable package and is excluded from publication.

## Versions and release notes

Use numeric semantic versions and `vX.Y.Z` Git tags. Current automation publishes
normal releases only; preview tags are not package publication triggers. A `0.x`
release remains a development release and does not imply production readiness.

Use conventional commits: `feat` for features, `fix` for corrections, `perf` for
performance changes and `!` or `BREAKING CHANGE` for incompatible changes. Before
1.0, incompatible changes increment the minor version and compatible changes
increment the patch version. After 1.0, incompatible changes increment the major
version and features increment the minor version. Review the proposed version;
automation cannot assess API compatibility on its own.

Release Please prepares a pull request updating `version.txt`, the release
manifest and `CHANGELOG.md` together. SDK releases also update the Python package
version; deployment releases update the Helm chart version. Contract schema
versions and the chart's application-version hint remain separate concerns.

The release pull request requires the same maintainer review, current checks
and resolved conversations as every other pull request. Include upgrade steps, migration risks,
compatibility constraints and rollback instructions in its notes. The sole
maintainer reviews the diff and merges after checks pass, without a separate
approving review. Restore independent code-owner approval when another trusted
maintainer joins. Never bypass branch protection.

After the release pull request merges, Release Please creates its protected tag and GitHub
release. Publication runs on the published release event, checks that the tag
matches the reviewed version and belongs to the default branch, then publishes
artifacts. No package is published from a pull request or an arbitrary tag push.

## Artifacts

- Containers: development builds publish `edge`, short SHA and full SHA references.
  Release builds publish exact version tags, provenance and software bills of
  materials. They attach digest records to GitHub releases. They refuse to
  overwrite an existing release version. Deploy by digest.
- SDK: build and test a wheel and source distribution once. Attach them and
  checksums to the GitHub release. Optional PyPI publication uses those same
  verified files and does not block GitHub release assets. The distribution remains `kionga`; imports remain
  `kionga`.
- Deployment: lint and package the Helm chart, then attach the archive and
  checksums to its release. Deployments supply explicit component image digests;
  the chart version is not a cross-component compatibility guarantee.
- Contracts: test and attach a versioned source archive with checksums.

Dependency updates remain reviewed pull requests. When adopting a new SDK or
runtime release, update the consumer's image build arguments and matching test
requirements together, run integration tests, and release the consumer. Do not
silently float internal dependencies to the newest component version.

A published GitHub release can precede completed package uploads. Wait for the
publishing jobs to succeed. Rerun failed jobs after a transient failure; do not
rerun successful publication jobs or overwrite existing assets. Correct a bad
artifact with a new patch version. Use PyPI's yank mechanism when an already
published SDK version must be withdrawn from normal dependency resolution.

## Configure publishing

### Release automation credentials

Set `RELEASE_PLEASE_TOKEN` in each participating repository, or as an organization
secret limited to those repositories. Use an expiring fine-grained token with
Contents, Issues and Pull requests write access. An administrator must approve
organization access when required. This credential creates release pull requests and tags;
it has no branch-rule bypass and must not approve its own pull requests.

The workflow deliberately fails with a configuration error when the credential
is absent. The default workflow token cannot create pull requests under organization policy
and its release events do not start downstream publishing workflows. Do not copy
an administrator's broad CLI token into Actions to work around this boundary.

### PyPI trusted publisher

PyPI publication is on hold until a Kionga email is available, tracked in
[SDK issue #29](https://github.com/kiongahq/sdk-python/issues/29). The repository
variable `PYPI_PUBLISH_ENABLED` is `false`; an absent variable also disables PyPI.
SDK packages continue to publish as GitHub release assets during the hold.

Create a pending trusted publisher in the owning PyPI account, or add one to the
existing project if it has already been created:

| Field | Value |
| --- | --- |
| Project | `kionga` |
| GitHub owner | `kiongahq` |
| Repository | `sdk-python` |
| Workflow filename | `publish.yml` |
| GitHub environment | `pypi` |

The `pypi` environment permits release tags only. The publishing job alone receives
OIDC permission; it downloads the tested package artifact without checking out or
executing project source. After completing account setup and publisher validation,
set `PYPI_PUBLISH_ENABLED` to `true` for subsequent SDK releases. No PyPI password
or API token is required. This setup is not required for GitHub-only releases.

See [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
and [GitHub workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
for the provider requirements.

## Documentation changelog

The product changelog aggregates published releases from the public component
repositories. Pages refreshes the release snapshot during trusted builds and
every six hours. pull request builds and offline builds use the committed snapshot.
A failed API refresh stops publication and preserves the previous snapshot.
Draft releases are excluded and release text is escaped before rendering.

Run `make docs-releases` in the documentation repository to refresh the local
snapshot. Review and commit it when updating the offline catalog. Editing release
notes does not itself rebuild the docs; use the manual Pages workflow or wait for
the scheduled refresh. The catalog links to all releases, with the five most
recent entries per repository displayed locally.

## Rollout order

Merge the shared automation change first, followed by each component change and
the documentation update. Consumer workflows pin the exact reviewed shared
commit. Configure the release credential before enabling automation. Register
the PyPI publisher only when resuming PyPI publication. Run all existing required checks
and follow the configured review policy; the rollout does not waive those controls.
