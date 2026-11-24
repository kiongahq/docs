---
icon: material/clipboard-check-outline
description: What a Kubernetes cluster needs before Kionga can run applications, functions and model endpoints on it, including cert-manager, KEDA and its HTTP add-on, KServe, an ingress controller, wildcard DNS, a registry and Pod Security settings.
---

# Kubernetes prerequisites

Kionga's applications, functions, request-based autoscaling and model endpoints
use a few cluster add-ons. The Helm chart does not install them silently: they are
yours to choose, version and operate. This page lists what you need, why, and how
to check it. For the base install, see
[Deploy on Kubernetes](managed-kubernetes.md).

You need each add-on only for the features you turn on:

| Feature | Needs |
| --- | --- |
| Applications | An ingress controller, wildcard DNS, wildcard TLS (cert-manager), KEDA with the HTTP add-on for request scaling and scale to zero, a registry for Git builds |
| Functions | KEDA with the HTTP add-on |
| Agents scaled on requests | KEDA with the HTTP add-on. CPU scaling needs only metrics-server. |
| Model endpoints | KServe in RawDeployment mode, an S3-compatible object store |
| Pipelines | Nothing extra. Kubernetes runs them as Jobs. |

!!! info "Available in a later release"
    The chart in deploy v0.2.0 doesn't yet install Kionga's resource definitions
    for applications, functions and model deployments, set the operator and
    gateway variables, run the preflight checks described below, or label the
    namespace that runs builds. A later chart release adds them, together with a
    script that installs the add-ons at pinned versions. Until then, install the
    add-ons yourself, apply the resource definitions from the platform
    release, and set the variables named on each page.

## Before you begin

- A Kubernetes cluster that meets the requirements in
  [Deploy on Kubernetes](managed-kubernetes.md#before-you-begin), and
  `kubectl` and Helm on the machine you work from.
- A cluster-administrator identity. Installing resource definitions and
  cluster-wide add-ons needs it.
- For applications: DNS you control, so you can create a wildcard record, and a
  base domain that differs from the console host and the workspace domain.
- For applications built from Git: a container registry you can push to.
- For model endpoints: an S3-compatible object store.

## Cert-manager

[cert-manager](https://cert-manager.io/) issues the wildcard certificate for
application host names, such as `*.kionga.company-x.net`.

- A wildcard certificate needs a DNS-01 challenge, because the HTTP-01 challenge
  can't issue wildcards. Create a `ClusterIssuer` for your DNS provider.
- Alternatively, create the certificate yourself and store it as a
  `kubernetes.io/tls` Secret in the workload namespace. Name that Secret in
  `KIONGA_APPLICATIONS_TLS_SECRET` on the operator. Without it, application URLs use
  plain `http://`.
- KServe also uses cert-manager for its webhook certificates.

## KEDA and its HTTP add-on

[KEDA](https://keda.sh/) with its HTTP add-on scales workloads on the number of
concurrent HTTP requests, and holds a request while a scaled-to-zero workload
starts. Install both: KEDA core and the HTTP add-on.

- Kionga's default address for the add-on's interceptor is
  `keda-add-ons-http-interceptor-proxy` in the `keda` namespace, port 8080. If you
  install it elsewhere, set `KIONGA_KEDA_HTTP_INTERCEPTOR` on the operator and
  `KIONGA_KEDA_INTERCEPTOR_URL` on the gateway.
- Allow traffic from workload pods and from the gateway to the interceptor in
  your network policies.
- The operator looks for the add-on once, at startup. Restart the operator after
  you install it.
- Without the add-on, workloads that ask for request scaling run on CPU scaling and
  keep at least one pod. Scale to zero is not available. Each affected workload
  reports `ScalingReady` as `False` with the reason `KEDAHTTPAddonMissing`.

## KServe

[KServe](https://kserve.github.io/website/) runs model servers. Kionga uses its
RawDeployment mode, which creates plain Deployments and Services, so Knative and
Istio are not required. Kionga's controllers are built against KServe 0.21; in
that release the same mode is also called `Standard`.

Model deploys also need the operator to read model artifacts from your object
store. See [Set up model serving](../guides/models-kubernetes.md#set-up).

## Ingress controller

Choose an ingress controller and name its class in `ingress.className`, as the
base install describes. Kionga doesn't pick one for you, and does not default to ingress-nginx.

Application Ingresses send request-scaled traffic to the KEDA interceptor through
a Service of type `ExternalName`, and send `sso` traffic to the gateway the same
way. Your controller must allow `ExternalName` backends. Some controllers turn
this off by default.

Set the class for application Ingresses with `KIONGA_INGRESS_CLASS` on the
operator.

## Wildcard DNS records

Choose a base domain for applications, for example `kionga.company-x.net`.

1. The domain must differ from the console host and from the workspace domain.
2. Create a wildcard record, `*.kionga.company-x.net`, that points at the ingress
   controller's address.
3. Set `KIONGA_APPLICATIONS_BASE_DOMAIN` on the operator and the gateway.

An application named `billing` is then served at
`billing.kionga.company-x.net`.

## Registry for builds

Applications deployed from a Git repository build in the cluster and push the
image to a registry you choose. Without a registry, applications from an image
still work and Git sources fail with `BuildNotConfigured`.

- Set `KIONGA_BUILD_REGISTRY` to a repository prefix such as
  `registry.example.com/kionga`.
- Create a `kubernetes.io/dockerconfigjson` Secret with push access in the
  workload namespace, and name it in `KIONGA_BUILD_PUSH_SECRET`.
- Add the same registry's pull credentials to `imagePullSecrets` if it is private.
- For a registry inside the cluster that serves plain HTTP, set
  `KIONGA_BUILD_REGISTRY_INSECURE=true`.

## Pod security for builds

Git builds use rootless BuildKit. It needs user namespaces, so the build pod runs
with an unconfined seccomp profile and an unconfined AppArmor profile. It does not
run privileged.

The Pod Security `baseline` and `restricted` levels refuse those profiles. The
namespace where builds run must therefore enforce the `privileged` level, or no
level. Application and function pods themselves run non-root with all capabilities
dropped, so they pass the `restricted` level, which the base install applies to
the workload namespace. If you want to keep the workload namespace restricted,
run builds in a separate namespace.

Treat a namespace that allows builds as less isolated, and keep it free of
other workloads. Builds run public repositories you don't control, with no
Kubernetes API token, so also limit their network access to your registry and Git
hosts.

## Preflight

The chart can refuse to install when a prerequisite is missing, so a missing add-on
shows up as an install error instead of a workload that never starts. The check
names the first missing item: a Kionga resource definition, the KEDA scaling
resources, the KServe InferenceService, cert-manager, a missing `ClusterIssuer`,
or the wildcard TLS Secret.

!!! info "Available in a later release"
    The preflight arrives with the chart release that adds applications.
    `helm template` has no cluster to read, so it skips the check unless you
    ask it to use the API versions you pass with `--api-versions`.

Until then, check by hand, as described in [Verify](#verify).

## Verify

1. Check that the cluster serves the resource definitions:

    ```bash
    kubectl get crd | grep -E 'keda.sh|http.keda.sh|serving.kserve.io|cert-manager.io|kionga.dev'
    ```

    The output lists the resource definitions for KEDA, the KEDA HTTP add-on,
    KServe, cert-manager and Kionga, including `kiongaapplications`,
    `kiongafunctions` and `kiongamodeldeployments`.

2. Check the certificate issuer and the wildcard certificate Secret:

    ```bash
    kubectl get clusterissuer
    kubectl -n kionga-workloads get secret <wildcard-tls-secret>
    ```

    The first command lists your `ClusterIssuer`. The second shows a Secret of
    type `kubernetes.io/tls`.

3. Check that the KEDA HTTP add-on interceptor exists at the address Kionga
   expects:

    ```bash
    kubectl -n keda get service keda-add-ons-http-interceptor-proxy
    ```

    The Service listens on port 8080. If you installed it elsewhere, you set
    `KIONGA_KEDA_HTTP_INTERCEPTOR` and `KIONGA_KEDA_INTERCEPTOR_URL`, so check
    that Service instead.

4. After you deploy an application, read its conditions:

    ```bash
    kubectl -n kionga-workloads get kiongaapplications
    kubectl -n kionga-workloads get kiongaapplication <name> -o yaml
    ```

    In `status.conditions`, `ScalingReady` is `True` with the reason
    `RequestsScaling` when request scaling works. `Ready` is `True` when the
    workload serves traffic.

## Troubleshooting

Read the reason in `status.conditions` of the workload, as in
[Verify](#verify) step 4.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ScalingReady` is `False` with reason `KEDAHTTPAddonMissing` and the message `requests scaling needs the KEDA HTTP add-on, which this cluster does not serve; using CPU scaling with at least one replica` | The operator did not find the KEDA HTTP add-on. It looks once, at startup | Install KEDA and its HTTP add-on, then restart the operator. Until then the workload keeps at least one pod |
| `Ready` is `False` with reason `BuildNotConfigured` and the message `source builds need KIONGA_BUILD_REGISTRY on the operator` | An application uses a Git source, and no registry is set | Set `KIONGA_BUILD_REGISTRY` and the push Secret, as in [Registry for builds](#registry-for-builds) |
| Reason `UnsupportedSource` with `source.git must be a public https:// URL without credentials` | The Git URL is not a public `https://` URL, or it embeds credentials | Use a public `https://` repository URL without credentials |
| Reason `KServeNotInstalled` with `this cluster does not serve serving.kserve.io/v1beta1 InferenceService; install KServe in RawDeployment mode` | A model deployment exists, and the operator did not find KServe | Install KServe in RawDeployment mode and restart the operator |
| Reason `StorageCredentialsMissing` with `object store Secret <name> does not exist in <namespace>` or `has no AWS_ACCESS_KEY_ID` | The Secret that holds the object store keys is missing, or lacks `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` | Create the Secret in the workload namespace with both keys. See [Set up model serving](../guides/models-kubernetes.md#set-up) |
| `IngressReady` is `False` with reason `SSOUpstreamNotConfigured` and `visibility sso needs KIONGA_SSO_UPSTREAM; the host is not served` | An application uses `sso` visibility, and the operator does not know the gateway address | Set `KIONGA_SSO_UPSTREAM` on the operator to the gateway's `host:port` |
| Application URLs start with `http://` | The operator does not know the wildcard certificate Secret | Set `KIONGA_APPLICATIONS_TLS_SECRET`, as in [Cert-manager](#cert-manager) |
| Git builds fail at pod admission | The build namespace enforces the `baseline` or `restricted` Pod Security level | Run builds in a namespace that enforces `privileged` or no level. See [Pod security for builds](#pod-security-for-builds) |
| `helm install` fails with `preflight: <value> needs <apiVersion/Kind>, which this cluster does not serve` | A prerequisite for a feature you turned on is not installed. Available with the chart release that adds the preflight | Install the named prerequisite, or turn the feature off |
| `helm install` fails with `preflight: applications.tls.clusterIssuer names ClusterIssuer <name>, which does not exist` | The `ClusterIssuer` is missing. Available with the chart release that adds the preflight | Create a DNS-01 `ClusterIssuer` for the wildcard domain, or name the correct one |
| `helm install` fails with `preflight: applications.tls.secretName <name> is missing in namespace <namespace>` | The wildcard TLS Secret is missing. Available with the chart release that adds the preflight | Create the `kubernetes.io/tls` Secret in that namespace, or set `applications.tls.clusterIssuer` |

## Related pages

- [Deploy on Kubernetes](managed-kubernetes.md)
- [Deploy applications](../guides/applications.md)
- [Run functions on Kubernetes](../guides/functions.md)
- [Deploy and canary models on Kubernetes](../guides/models-kubernetes.md)
