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

## cert-manager

[cert-manager](https://cert-manager.io/) issues the wildcard certificate for
application host names, such as `*.kionga.company-x.net`.

- A wildcard certificate needs a DNS-01 challenge, because the HTTP-01 challenge
  can't issue wildcards. Create a `ClusterIssuer` for your DNS provider.
- Alternatively, create the certificate yourself and store it as a
  `kubernetes.io/tls` Secret in the workload namespace. Name that Secret in
  `KIONGA_APPLICATIONS_TLS_SECRET` on the operator. Without it, application URLs use
  plain `http://`.
- KServe also uses cert-manager for its webhook certificates.

## KEDA and the KEDA HTTP add-on

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
base install describes. Kionga doesn't pick one for you. The Kubernetes project
retired ingress-nginx in 2026, so don't choose it for a new install.

Application Ingresses send request-scaled traffic to the KEDA interceptor through
a Service of type `ExternalName`, and send `sso` traffic to the gateway the same
way. Your controller must allow `ExternalName` backends. Some controllers turn
this off by default.

Set the class for application Ingresses with `KIONGA_INGRESS_CLASS` on the
operator.

## Wildcard DNS

Choose a base domain for applications, for example `kionga.company-x.net`.

1. The domain must differ from the console host and from the workspace domain.
2. Create a wildcard record, `*.kionga.company-x.net`, that points at the ingress
   controller's address.
3. Set `KIONGA_APPLICATIONS_BASE_DOMAIN` on the operator and the gateway.

An application named `billing` is then served at
`billing.kionga.company-x.net`.

## Registry for Git builds

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

## Pod Security for builds

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

Until then, check by hand:

```bash
kubectl get crd | grep -E 'keda.sh|http.keda.sh|serving.kserve.io|cert-manager.io|kionga.dev'
kubectl get clusterissuer
kubectl -n kionga-workloads get secret <wildcard-tls-secret>
```

**Verify:** the first command lists the resource definitions for KEDA, the KEDA
HTTP add-on, KServe, cert-manager and Kionga, including `kiongaapplications`,
`kiongafunctions` and `kiongamodeldeployments`.

## Next steps

- [Deploy on Kubernetes](managed-kubernetes.md).
- [Deploy applications](../guides/applications.md).
- [Run functions on Kubernetes](../guides/functions.md).
- [Deploy and canary models on Kubernetes](../guides/models-kubernetes.md).
