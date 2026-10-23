---
description: Sign people in through OIDC only, with Dex as the bundled broker for LDAP, SAML and social identity providers, and local accounts as break-glass access.
status: "accepted"
date: 2026-10-10
---

# 0006 Single sign-on through OIDC, with Dex as the bundled broker

## Context and problem statement

Organizations that run Kionga sign in with many kinds of directory: LDAP or Active
Directory, SAML providers, GitHub, Google, Microsoft Entra, GitLab, or an existing OIDC
provider. Local development needs a working sign-in with no external service. How
should the gateway authenticate people without implementing every protocol itself?

## Decision drivers

- One protocol to implement and secure in the gateway.
- Enterprise directories and social logins without gateway code per provider.
- Group membership from the directory mapped to platform roles.
- A complete, testable sign-in in the local stack.
- Access when the identity provider is down.

## Considered options

- OIDC in the gateway, with Dex as the bundled broker and local accounts as break-glass
- OIDC in the gateway against one organization issuer, with no broker
- Local accounts only

## Decision outcome

Chosen option: **OIDC in the gateway, with Dex as the bundled broker and local accounts
as break-glass**, because it keeps one protocol in the gateway while supporting every
directory type through Dex connectors, and still allows a direct issuer in production.

The gateway is an OIDC relying party (`platform/go/internal/auth`): authorization code
flow with PKCE (S256) and an ID-token nonce, JWKS verification, connector selection
through Dex's `connector_id`, group-to-role mapping through `KIONGA_SSO_GROUP_ROLES`,
and a sign-up policy for first sign-ins. The local stack runs Dex v2.46.0 (pinned by
digest) with a GLAuth test directory. Local accounts stay available next to single
sign-on only with `KIONGA_LOCAL_LOGIN=true` and an explicit password.

### Consequences

- Good, because the gateway contains one authentication protocol; LDAP, SAML, GitHub,
  Google, Microsoft, GitLab and OIDC come from Dex connectors configured in
  `deploy/sso/`.
- Good, because production can point the same settings at any OIDC issuer, with or
  without Dex. Default scopes avoid Dex-only scopes so strict providers accept them;
  Dex deployments add `federated:id` through `OIDC_SCOPES`.
- Good, because the local stack exercises the real flow end to end.
- Bad, because Dex cannot add a tenant claim, so `KIONGA_SSO_SINGLE_TENANT` assigns the
  configured tenant to tokens without one.
- Bad, because the session cookie carries the ID token itself and cannot be revoked
  server-side ([risk R8](../architecture/11-risks-and-technical-debt.md#risks)).

### Confirmation

Go unit tests with a fake identity provider cover PKCE, nonce, connectors, group
mapping and failure handling in `platform/go/internal/auth`.
`platform/tests/e2e/sso.spec.cjs` runs against Dex and LDAP in a browser.
`deploy/tests/test_sso.py` keeps the gateway and Dex configuration in agreement
(issuer, client, redirect, secret, connector IDs) and checks role mappings and image
pins.

## Pros and cons of the options

### Dex broker with OIDC in the gateway

- Good, because new directory types need configuration, not gateway code.
- Neutral, because Dex is one more service to run and pin.

### Direct organization issuer

- Good, because there is no broker to operate.
- Bad, because it covers only directories that already speak OIDC; supported as a
  configuration of the chosen option.

### Local accounts only

- Good, because nothing external is needed.
- Bad, because there is no directory integration and every account is managed by hand;
  kept as the development default when no issuer is set and as break-glass access.

## More information

Written after the fact. Evidence: OIDC verification and RBAC (`platform` commit
`160d855`, 2026-06-28); single sign-on through an OIDC broker alongside local accounts
(`platform` commit `3212a4a`, 2026-10-10, whose message lists PKCE, nonce, connector
selection, group mapping and break-glass rules); the local Dex and LDAP overlay
(`deploy` commit `c9eb66c`, 2026-10-10). The sequence is in the
[runtime view](../architecture/06-runtime-view.md#sign-in-through-single-sign-on); the
operator guide is
[single sign-on](https://kiongahq.github.io/docs/operations/single-sign-on/).
