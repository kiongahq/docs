# Single sign-on

Kionga signs people in through an OIDC broker, [Dex](https://dexidp.io). Dex
connects to the identity systems you already run and gives Kionga one trusted
issuer, so the gateway never handles LDAP binds, SAML assertions or provider
OAuth secrets itself.

| Identity system | Dex connector |
| --- | --- |
| LDAP, Active Directory | `ldap` |
| Okta, ADFS, Entra ID, any SAML 2.0 IdP | `saml` |
| GitHub, GitLab (OAuth) | `github`, `gitlab` |
| Google Workspace | `google` |
| Microsoft Entra ID | `microsoft` |
| Keycloak, Okta OIDC, Auth0, any OIDC provider | `oidc` |

Local accounts can stay enabled next to single sign-on as break-glass access, for
example when the directory is down.

## How sign-in works

1. The login page reads `/auth/providers` and shows a button per provider, plus the
   local form when local accounts are enabled.
2. **Sign in with …** goes to `/auth/sso/login?connector=<id>`. The gateway sends the
   browser to Dex with that connector, a PKCE challenge and a nonce. Unknown
   connector ids are rejected.
3. Dex authenticates the user with the upstream system and returns a code. The
   gateway exchanges it (proving PKCE), verifies the ID token signature, issuer,
   audience, expiry and nonce, and sets an HttpOnly session cookie, marked
   Secure when `OIDC_REDIRECT_URL` is https (production requires https).
   The login starts on the callback's host: opening the console at
   `127.0.0.1` moves the browser to `localhost` first, so the login cookies
   reach the callback.
4. Roles come from the token: a `roles` claim if present, otherwise the user's
   groups mapped through `KIONGA_SSO_GROUP_ROLES`. A group named like a role
   (`viewer`) still counts. Identity-provider groups never grant the internal
   `service` role. Someone with no mapped group is an unprovisioned `user`: they
   reach only their profile, access requests and personal settings.
   Administrator-managed access profiles keyed by the user's subject override
   token roles, as for any user.
5. On a person's first sign-in, [sign-up](#sign-up) decides whether they get an
   account.
6. **Sign out** ends the Kionga session (and workspace sessions) for both local
   and single sign-on users.

## Sign-up

A person signing in through single sign-on for the first time, with no Kionga
account and no directory group mapped to a role above `user`, gets an account
according to `KIONGA_SIGNUP`:

| Mode | First sign-in creates | The person sees |
| --- | --- | --- |
| `approval` (default) | An access request ("Signed up with github") for the requested default services | A "waiting for approval" banner; no service until an administrator provisions them in **Users & access** |
| `open` | An active `user` account with the `KIONGA_SIGNUP_PROFILE` resource profile (default `starter`) | The console, at once |
| `off` | Nothing | Access only through mapped directory groups or an administrator |

Rules that always hold:

- Signing in again never creates a second request, and a declined request is
  not refiled. The person can ask again from **My access**.
- An existing account is never changed by signing in: a suspended account stays
  suspended.
- People whose directory groups grant `admin`, `operator`, `engineer` or `viewer`
  are skipped, because a stored profile would replace that role.
- `KIONGA_SIGNUP_EMAIL_DOMAINS=example.com,corp.io` limits sign-up to emails at
  those domains that the identity provider marked verified.
- `KIONGA_SIGNUP_SERVICES` overrides the default services (overview, projects,
  pipelines, models, features, storage, catalog, workbench, ide).

The gateway logs each sign-up (`sign-up for <subject> via "github": requested`),
and `/api/v1/me` reports `connector` and the latest `access_request` status.

## Try it locally

`make -C deploy local-up` starts every sign-in method. Open
<http://localhost:8080/login.html>:

| Option | Try it |
| --- | --- |
| **Company directory** (LDAP through Dex, GLAuth test directory) | Password `kionga-sso-dev` for every user below |
| **Demo account (local only)** (Dex's no-credentials OAuth round trip) | One click; the first sign-in signs up as Kilgore Trout |
| **GitHub, Google, GitLab, Microsoft** | Appear once their client id and secret are set (below) |
| Local form | `admin` / `mlaiops-local` (break-glass) |

| Directory user | Group | Result |
| --- | --- | --- |
| `ada` | `ml-admins` | admin |
| `grace` | `data-team` | engineer |
| `alan` | `everyone` | signs up: an access request waits for approval |

### Add an OAuth provider locally

1. Register an OAuth app at the provider with callback URL
   `http://localhost:5556/dex/callback`.
2. Put the client id and secret in `deploy/.env`:

    ```bash
    KIONGA_GITHUB_CLIENT_ID=...
    KIONGA_GITHUB_CLIENT_SECRET=...
    KIONGA_GITHUB_ORG=your-org        # optional: members only, teams become groups
    # likewise KIONGA_GOOGLE_*, KIONGA_GITLAB_* (+ KIONGA_GITLAB_URL),
    # KIONGA_MICROSOFT_* (+ KIONGA_MICROSOFT_TENANT)
    ```

3. `make -C deploy sso-reload`.

Dex renders `deploy/sso/dex.yaml` (a gomplate template) with the connectors
whose client ids are set, and writes the login-page list from the same rendered
config to a volume the gateway reads, so a button exists exactly when its
connector does and the gateway needs no restart. Secrets stay `$VARS` that Dex
expands when it loads the config; the rendered file never holds them.

## Connect your directory

With Compose, point the LDAP connector at your directory with `KIONGA_LDAP_HOST`,
`KIONGA_LDAP_BIND_DN`, `DEX_LDAP_BIND_PASSWORD`, `KIONGA_LDAP_BASE_DN`,
`KIONGA_LDAP_GROUP_BASE_DN` and `KIONGA_LDAP_INSECURE_NO_SSL=false`, or add a
connector to `deploy/sso/dex.yaml` (SAML, generic OIDC). For your own Dex
deployment use connectors like these, then set the gateway variables.

=== "LDAP / Active Directory"

    ```yaml
    - type: ldap
      id: ldap
      name: Company directory
      config:
        host: dc.example.com:636
        rootCA: /etc/dex/ldap-ca.pem
        bindDN: CN=dex,OU=Service Accounts,DC=example,DC=com
        bindPW: $DEX_LDAP_BIND_PASSWORD
        userSearch:
          baseDN: OU=People,DC=example,DC=com
          filter: "(objectClass=person)"
          username: sAMAccountName
          idAttr: objectGUID
          emailAttr: mail
          nameAttr: displayName
        groupSearch:
          baseDN: OU=Groups,DC=example,DC=com
          filter: "(objectClass=group)"
          userMatchers: [{userAttr: DN, groupAttr: member}]
          nameAttr: cn
    ```

=== "SAML (Okta, ADFS, Entra)"

    ```yaml
    - type: saml
      id: okta
      name: Okta
      config:
        ssoURL: https://example.okta.com/app/.../sso/saml
        ca: /etc/dex/saml-ca.pem
        redirectURI: https://kionga.example.com/dex/callback
        usernameAttr: name
        emailAttr: email
        groupsAttr: groups
    ```

=== "GitHub"

    ```yaml
    - type: github
      id: github
      name: GitHub
      config:
        clientID: $GITHUB_CLIENT_ID
        clientSecret: $GITHUB_CLIENT_SECRET
        redirectURI: https://kionga.example.com/dex/callback
        orgs: [{name: your-org, teams: [ml-admins, data-team]}]
    ```

Gateway settings (see [Configuration](../reference/configuration.md#rbac)):

```bash
OIDC_ISSUER=https://kionga.example.com/dex
OIDC_JWKS_URL=https://kionga.example.com/dex/keys
OIDC_AUTH_URL=https://kionga.example.com/dex/auth
OIDC_TOKEN_URL=https://kionga.example.com/dex/token
OIDC_REDIRECT_URL=https://kionga.example.com/auth/callback
OIDC_CLIENT_ID=kionga
OIDC_CLIENT_SECRET=...            # same as the Dex static client
OIDC_AUDIENCE=kionga
OIDC_SCOPES="openid profile email groups federated:id"   # federated:id is Dex-only
KIONGA_SSO_PROVIDERS='[{"id":"ldap","name":"Company directory","type":"ldap"},{"id":"github","name":"GitHub","type":"github"}]'
# or KIONGA_SSO_PROVIDERS_FILE=/path/providers.json, re-read when it changes
KIONGA_SSO_GROUP_ROLES='{"ml-admins":"admin","data-team":"engineer","analysts":"viewer"}'
KIONGA_SSO_SINGLE_TENANT=true     # Dex tokens carry no tenant claim
KIONGA_LOCAL_LOGIN=true           # optional break-glass; needs MLAIOPS_LOCAL_PASSWORD
KIONGA_SIGNUP=approval            # approval | open | off
KIONGA_SIGNUP_EMAIL_DOMAINS=example.com
```

`compose.public.yaml` runs the same Dex at `https://$MLAIOPS_DOMAIN/dex` with the
test directory and demo account off, Dex's own email and password admin
(`DEX_ADMIN_EMAIL`, `DEX_ADMIN_PASSWORD_HASH`) on, and requires
`MLAIOPS_LOCAL_PASSWORD`. Register OAuth apps with callback
`https://$MLAIOPS_DOMAIN/dex/callback`.

With GitHub, group names are `org:team` (for example `your-org:ml-admins`); map
those names in `KIONGA_SSO_GROUP_ROLES`.

## Production checklist

- Serve Dex over HTTPS and use that URL as `OIDC_ISSUER`; production mode rejects
  a plain HTTP issuer.
- Give Dex persistent storage (SQL or Kubernetes CRDs). The Compose stack uses
  memory storage, which forgets signing keys on restart and signs everyone out.
- Choose a sign-up mode. `approval` is the safe default; use `open` only with
  `KIONGA_SIGNUP_EMAIL_DOMAINS` or a provider that admits only your people
  (a GitHub org, a Google hosted domain, an Entra tenant).
- Turn the demo account off (`KIONGA_SSO_DEMO=false`; the public overlay does).
- Use TLS to the directory (`ldaps`, port 636) and a least-privilege bind account.
- Keep secrets (`OIDC_CLIENT_SECRET`, bind passwords, connector client secrets) in
  your secret manager and pass them to Dex as environment variables.
- Decide whether local break-glass login stays on. If it does, use a long random
  `MLAIOPS_LOCAL_PASSWORD`, keep it in a vault, and deliver it as a file with
  `MLAIOPS_LOCAL_PASSWORD_FILE` like the other secrets. With
  `KIONGA_ENVIRONMENT=production` the gateway refuses to start when that password
  is shorter than 16 characters or contains `local`, `change-me`, or `password`.
  Failed local sign-ins are throttled per account (a doubling delay after 5
  failures, up to 60 s). While local sign-in is on, administrators can also issue
  local passwords to provisioned users; turn it off (`KIONGA_LOCAL_LOGIN` unset)
  when the identity provider must own every credential.
- Map groups to the least privileged roles, and grant project and service access
  with [access control policies](../guides/access-control.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Login page shows no SSO button | `curl $MLAIOPS_URL/auth/providers`; `KIONGA_SSO_PROVIDERS` (or the file) must be valid JSON and `OIDC_ISSUER` set |
| An OAuth button is missing after editing `.env` | `make -C deploy sso-reload`; `docker compose logs dex` lists each `config connector` |
| `invalid login state` on `/auth/callback` | The login cookies did not come back: the browser blocks cookies for this site, the login took over 10 minutes, or `OIDC_REDIRECT_URL` names a host the browser cannot reach as the same site |
| A first sign-in created no access request | `KIONGA_SIGNUP` is `off`, the email is outside `KIONGA_SIGNUP_EMAIL_DOMAINS` or unverified, or a directory group already grants a role; the gateway logs `sign-up for ...` |
| `unknown sign-in provider` | The button id is not in `KIONGA_SSO_PROVIDERS`, or does not match a Dex connector id |
| Dex says "Invalid username or password" | Dex logs: bind DN and password, `userSearch` filter and `username` attribute |
| Signed in but no access | Waiting for approval (the console banner says so), or the user's groups are not in `KIONGA_SSO_GROUP_ROLES`; Dex logs list the groups it found at login |
| `identity token validation failed` | `OIDC_ISSUER` must equal Dex's `issuer` exactly; `OIDC_AUDIENCE` must be the client id; with `MLAIOPS_TENANT` set, enable `KIONGA_SSO_SINGLE_TENANT` |
| Gateway exits with `requires MLAIOPS_LOCAL_PASSWORD` | `KIONGA_LOCAL_LOGIN=true` next to SSO needs an explicit break-glass password |
| Gateway exits with `must be at least 16 characters and not a development default` | Production mode rejects a short or default break-glass password; set a long random `MLAIOPS_LOCAL_PASSWORD` (or `MLAIOPS_LOCAL_PASSWORD_FILE`) |
| Local form says "Too many failed attempts for this account" | After 5 failures each attempt waits up to 60 s; wait, then use the correct password. Failures reset after 15 minutes or on success |
| SSO works on this machine but not from another | Ports bind to `127.0.0.1` by default, and the browser is sent to `localhost`. Set `KIONGA_BIND_ADDRESS`, `KIONGA_GATEWAY_URL`, and `DEX_ISSUER` as in [Network exposure](local.md#network-exposure) |
