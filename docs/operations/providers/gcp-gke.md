---
description: Prepare a Google Kubernetes Engine cluster for Kionga (network policy, PD storage, Workload Identity for Secret Manager) and install the Helm chart with the GKE overlay.
---

# Deploy on Google GKE

This guide shows you how to prepare a GKE Standard cluster for Kionga and
install the chart with the GKE overlay. It adds the Google Cloud steps to
[Deploy on Kubernetes](../managed-kubernetes.md); read that guide first.

## Before you begin

- A GKE Standard cluster with at least three Ready nodes across two or more
  zones.
- Workload Identity Federation, network policy enforcement
  (`--enable-dataplane-v2`, or another enforced NetworkPolicy provider) and the Compute Engine persistent disk CSI driver
  turned on.
- The `gcloud` CLI, `kubectl` and Helm, signed in with an identity that can
  describe the cluster.
- The dependencies listed in [Deploy on Kubernetes](../managed-kubernetes.md#before-you-begin),
  with their credentials in Secret Manager.
- External Secrets Operator, an ingress controller, wildcard DNS and TLS
  certificates. The overlay sets `ingress.className: nginx`; change it if you
  use another controller.

## Steps

1. **Get cluster credentials** and note the context name; use it explicitly in
   every command:

    ```bash
    gcloud container clusters get-credentials CLUSTER --project PROJECT --location LOCATION
    kubectl config current-context
    ```

2. **Create the secret-reader identity.** Create a Google service account that
   can read only the Kionga secret versions in Secret Manager, and allow the
   Kubernetes service account `kionga-secret-reader` in `kionga-system` to
   impersonate it. Put the project, cluster name and location into
   `deploy/helm/secretstore-gcp.example.yaml`.

3. **Create the namespace, CRDs and pull Secret**, as in steps 1 and 2 of
   [Deploy on Kubernetes](../managed-kubernetes.md#steps), then apply the
   secret store:

    ```bash
    kubectl --context CONTEXT apply -f deploy/helm/secretstore-gcp.example.yaml
    ```

4. **Create the storage class** `kionga-pd-balanced` (balanced PD, expandable,
   retained, bound on first use):

    ```bash
    kubectl --context CONTEXT apply -f deploy/helm/providers/gke-storageclass.example.yaml
    ```

    Persistent disks are zonal and single-writer. Keep shared project data in
    object storage.

5. **Run the preflight check.**

    ```bash
    python3 deploy/scripts/cloud-preflight.py gke --context CONTEXT --cluster CLUSTER --project PROJECT --location LOCATION
    ```

    It confirms that the context points at this cluster, that the cluster is
    running, that Workload Identity, network policy (`--enable-dataplane-v2` or
    the NetworkPolicy add-on) and the PD CSI driver are on, that there are three
    Ready nodes in two zones, and that the storage class is configured as above.

6. **Check and install** with the GKE overlay after your values file:

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml deploy/helm/providers/gke.example.yaml
    bash deploy/scripts/deploy-kubernetes.sh CONTEXT kionga-system /secure/production.yaml deploy/helm/providers/gke.example.yaml --apply
    ```

## Verify

With `--enable-dataplane-v2`, GKE treats `ipBlock` rules for Pod and Service ranges in its own way.
Test Kionga's network policies against your actual VPC and DNS paths before you
allow user workloads. The preflight does not prove IAM permissions, policy
behavior, disk attachment or recovery. Follow
[Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, then run
restore and failover drills before you admit users.

## Next steps

- [Production readiness](../production-operations.md).

Related: [GKE network policy](https://cloud.google.com/kubernetes-engine/docs/how-to/network-policy),
[Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity),
[PD CSI driver](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver),
[External Secrets for Google](https://external-secrets.io/latest/provider/google-secrets-manager/).
