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
   audience, expiry and nonce, and sets an HttpOnly, Secure session cookie.
4. Roles come from the token: a `roles` claim if present, otherwise the user's
   groups mapped through `KIONGA_SSO_GROUP_ROLES`. A group named like a role
   (`viewer`) still counts. Identity-provider groups never grant the internal
   `service` role. Administrator-managed access profiles keyed by the user's
   subject override token roles, as for any user.
5. **Sign out** ends the Kionga session (and workspace sessions) for both local
   and single sign-on users.

## Try it locally

```bash
make -C deploy sso-up      # Dex + a test LDAP directory, gateway in SSO mode
```

Open <http://localhost:8080/login.html> and choose **Sign in with Company
directory**. Test users, password `kionga-sso-dev`:

| User | Group | Role |
| --- | --- | --- |
| `ada` | `ml-admins` | admin |
| `grace` | `data-team` | engineer |
| `alan` | `everyone` | none (signed in, no access) |

The local `admin` account still works. `make -C deploy sso-down` returns to local
accounts only.

## Connect your directory

Edit the connector in `deploy/sso/dex.yaml` (Compose) or your Dex deployment, then
set the gateway variables.

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

Gateway settings (see [Configuration](../getting-started/configuration.md#rbac)):

```bash
OIDC_ISSUER=https://kionga.example.com/dex
OIDC_JWKS_URL=https://kionga.example.com/dex/keys
OIDC_AUTH_URL=https://kionga.example.com/dex/auth
OIDC_TOKEN_URL=https://kionga.example.com/dex/token
OIDC_REDIRECT_URL=https://kionga.example.com/auth/callback
OIDC_CLIENT_ID=kionga
OIDC_CLIENT_SECRET=...            # same as the Dex static client
OIDC_AUDIENCE=kionga
KIONGA_SSO_PROVIDERS='[{"id":"ldap","name":"Company directory","type":"ldap"},{"id":"github","name":"GitHub","type":"github"}]'
KIONGA_SSO_GROUP_ROLES='{"ml-admins":"admin","data-team":"engineer","analysts":"viewer"}'
KIONGA_SSO_SINGLE_TENANT=true     # Dex tokens carry no tenant claim
KIONGA_LOCAL_LOGIN=true           # optional break-glass; needs MLAIOPS_LOCAL_PASSWORD
```

With GitHub, group names are `org:team` (for example `your-org:ml-admins`); map
those names in `KIONGA_SSO_GROUP_ROLES`.

## Production checklist

- Serve Dex over HTTPS and use that URL as `OIDC_ISSUER`; production mode rejects
  a plain HTTP issuer.
- Give Dex persistent storage (SQL or Kubernetes CRDs). The local overlay uses
  memory storage, which forgets signing keys and refresh state on restart.
- Use TLS to the directory (`ldaps`, port 636) and a least-privilege bind account.
- Keep secrets (`OIDC_CLIENT_SECRET`, bind passwords, connector client secrets) in
  your secret manager and pass them to Dex as environment variables.
- Decide whether local break-glass login stays on. If it does, use a long random
  `MLAIOPS_LOCAL_PASSWORD` and keep it in a vault.
- Map groups to the least privileged roles, and grant project and service access
  with [access control policies](../guides/access-control.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Login page shows no SSO button | `curl $MLAIOPS_URL/auth/providers`; `KIONGA_SSO_PROVIDERS` must be valid JSON and `OIDC_ISSUER` set |
| `unknown sign-in provider` | The button id is not in `KIONGA_SSO_PROVIDERS`, or does not match a Dex connector id |
| Dex says "Invalid username or password" | Dex logs: bind DN and password, `userSearch` filter and `username` attribute |
| Signed in but no access | The user's groups are not in `KIONGA_SSO_GROUP_ROLES`; Dex logs list the groups it found at login |
| `identity token validation failed` | `OIDC_ISSUER` must equal Dex's `issuer` exactly; `OIDC_AUDIENCE` must be the client id; with `MLAIOPS_TENANT` set, enable `KIONGA_SSO_SINGLE_TENANT` |
| Gateway exits with `requires MLAIOPS_LOCAL_PASSWORD` | `KIONGA_LOCAL_LOGIN=true` next to SSO needs an explicit break-glass password |
