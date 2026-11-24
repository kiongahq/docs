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

## Prepare the cluster and install

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
   [Deploy on Kubernetes](../managed-kubernetes.md#install-the-chart), then apply the
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

1. List the platform resources:

    ```bash
    kubectl --context CONTEXT -n kionga-system get pods,services,ingress,hpa,pdb
    kubectl --context CONTEXT -n kionga-system get externalsecrets
    ```

    Every pod is `Running` and ready, and every ExternalSecret has the
    `Ready` condition set to `True`.

2. Run the production verifier from
   [Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, with
   `--context CONTEXT`. It exits with status 0 after it prints the cluster and
   HTTP checks, such as `Cluster: replicas, probes, digests, TLS ingress, HPA,
   isolation, and node spread pass`. On a failure it prints
   `Acceptance failed: <reason>` and exits with status 1.

With `--enable-dataplane-v2`, GKE treats `ipBlock` rules for Pod and Service ranges in its own way. Test Kionga's network policies against your actual VPC and DNS paths before you allow user workloads. The preflight does not prove IAM permissions, policy behavior, disk attachment or recovery. Run restore and failover drills before you admit users.

## Troubleshooting

The preflight in step 5 prints `Preflight passed. Confirm actual policy
enforcement, IAM, PVC provisioning, and failover in staging.` when every check
passes. On a failure it prints `Preflight failed: <reason>` and exits with
status 1.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Preflight failed: --project is required for gke` or `--location is required for gke` | The command lacks the flag | Add `--project PROJECT` and `--location LOCATION` |
| `Preflight failed: GKE cluster is not RUNNING` | The cluster is creating, updating, reconciling or in error | Wait until `gcloud container clusters describe` reports `RUNNING` |
| `Preflight failed: GKE Workload Identity Federation is disabled` | The cluster has no workload pool | Turn on Workload Identity Federation for the cluster |
| `Preflight failed: GKE needs Dataplane V2 or enabled NetworkPolicy` | The cluster uses neither `ADVANCED_DATAPATH` nor the NetworkPolicy add-on | Create the cluster with `--enable-dataplane-v2`, or enable network policy enforcement |
| `Preflight failed: GKE PD CSI driver is disabled` | The Compute Engine persistent disk CSI driver add-on is off | Turn it on |
| `Preflight failed: kubectl context points to a different cluster endpoint` | The `--context` does not point at the cluster you named | Run `kubectl config get-contexts`, then pass the context for this cluster |
| `Preflight failed: at least three Ready nodes are required` | The cluster has fewer than three nodes in the `Ready` condition | Add nodes, or wait for them to become `Ready` |
| `Preflight failed: Ready nodes must span at least two zones` | The Ready nodes carry fewer than two distinct `topology.kubernetes.io/zone` labels | Spread the node group across two or more zones |
| `Preflight failed: kionga-pd-balanced uses an unexpected provisioner` | The class `kionga-pd-balanced` exists with another provisioner | Apply the example class from step 4. A class keeps its provisioner, so replace a class that has another one |
| `Preflight failed: storage class must allow expansion`, `must delay binding until scheduled` or `must retain volumes` | The class differs from the example in `allowVolumeExpansion`, `volumeBindingMode` (`WaitForFirstConsumer`) or `reclaimPolicy` (`Retain`) | Create the class from the example file with those three settings. A class keeps its binding mode and reclaim policy, so replace a class that differs |
| `Preflight failed: Command '[...]' returned non-zero exit status` | The cloud CLI or `kubectl` failed, for example because you are not signed in or the cluster name is wrong | Run the command shown in the message by hand and read its error |
| An ExternalSecret is not `Ready` | The Google service account cannot read the Kionga secret versions in Secret Manager, or the `kionga-secret-reader` service account cannot impersonate it | Check the project, cluster name and location in `deploy/helm/secretstore-gcp.example.yaml` and the impersonation binding |
| Pods stay in `ImagePullBackOff` | The `ghcr-pull` Secret is missing from a namespace | See [Troubleshooting](../troubleshooting.md#pods-stay-in-imagepullbackoff-or-errimagepull) |

## Related pages

- [Deploy on Kubernetes](../managed-kubernetes.md)
- [Production readiness](../production-operations.md)
- [Troubleshooting](../troubleshooting.md#kubernetes)
- [GKE network policy](https://cloud.google.com/kubernetes-engine/docs/how-to/network-policy)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [PD CSI driver](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver)
- [External Secrets for Google](https://external-secrets.io/latest/provider/google-secrets-manager/)
