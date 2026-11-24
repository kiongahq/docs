---
description: Prepare an Azure Kubernetes Service cluster for Kionga (Cilium network policy, Azure Disk storage, Workload ID for Key Vault) and install the Helm chart with the AKS overlay.
---

# Deploy on Azure AKS

This guide shows you how to prepare an AKS cluster for Kionga and install the
chart with the AKS overlay. It adds the Azure steps to
[Deploy on Kubernetes](../managed-kubernetes.md); read that guide first.

## Before you begin

- An AKS cluster with Linux node pools: at least three Ready nodes across two
  or more availability zones.
- The OIDC issuer and Microsoft Entra Workload ID turned on.
- A network policy engine. For new clusters, prefer Azure CNI powered by
  Cilium; Azure Network Policy Manager has a published retirement path.
- The Azure Disk CSI driver and its identity permissions.
- The Azure CLI, `kubectl` and Helm, signed in with an identity that can read
  the cluster.
- The dependencies listed in [Deploy on Kubernetes](../managed-kubernetes.md#before-you-begin),
  with their credentials in Azure Key Vault.
- External Secrets Operator, an ingress controller, wildcard DNS and TLS
  certificates. The overlay sets `ingress.className: nginx`; change it if you
  use another controller.

## Prepare the cluster and install

1. **Get cluster credentials** under a fixed context name:

    ```bash
    az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER --context kionga-aks
    ```

2. **Create the secret-reader identity.** Create a managed identity that can
   read only the Kionga secrets in Key Vault, and add a federated credential
   for the Kubernetes service account `kionga-secret-reader` in
   `kionga-system`. Put the identity's client ID and the vault name into
   `deploy/helm/secretstore-azure.example.yaml`.

3. **Create the namespace, CRDs and pull Secret**, as in steps 1 and 2 of
   [Deploy on Kubernetes](../managed-kubernetes.md#install-the-chart), then apply the
   secret store:

    ```bash
    kubectl --context kionga-aks apply -f deploy/helm/secretstore-azure.example.yaml
    ```

4. **Create the storage class** `kionga-azuredisk-premium` (Premium SSD,
   expandable, retained, bound on first use):

    ```bash
    kubectl --context kionga-aks apply -f deploy/helm/providers/aks-storageclass.example.yaml
    ```

    Azure Disks are zonal and single-writer. Keep shared project data in object
    storage, not a shared volume.

5. **Run the preflight check.**

    ```bash
    python3 deploy/scripts/cloud-preflight.py aks --context kionga-aks --cluster CLUSTER --resource-group RESOURCE_GROUP
    ```

    It confirms that the context points at this cluster, that the cluster is
    provisioned, that the OIDC issuer, Workload Identity and a network policy
    engine are on, that there are three Ready nodes in two zones, and that the
    storage class is configured as above.

6. **Check and install** with the AKS overlay after your values file:

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh kionga-aks kionga-system /secure/production.yaml deploy/helm/providers/aks.example.yaml
    bash deploy/scripts/deploy-kubernetes.sh kionga-aks kionga-system /secure/production.yaml deploy/helm/providers/aks.example.yaml --apply
    ```

## Verify

1. List the platform resources:

    ```bash
    kubectl --context kionga-aks -n kionga-system get pods,services,ingress,hpa,pdb
    kubectl --context kionga-aks -n kionga-system get externalsecrets
    ```

    Every pod is `Running` and ready, and every ExternalSecret has the
    `Ready` condition set to `True`.

2. Run the production verifier from
   [Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, with
   `--context kionga-aks`. It exits with status 0 after it prints the cluster and
   HTTP checks, such as `Cluster: replicas, probes, digests, TLS ingress, HPA,
   isolation, and node spread pass`. On a failure it prints
   `Acceptance failed: <reason>` and exits with status 1.

The preflight reads reported configuration only. It does not prove IAM permissions, policy behavior, disk attachment or recovery. Run restore and failover drills before you admit users.

## Troubleshooting

The preflight in step 5 prints `Preflight passed. Confirm actual policy
enforcement, IAM, PVC provisioning, and failover in staging.` when every check
passes. On a failure it prints `Preflight failed: <reason>` and exits with
status 1.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Preflight failed: --resource-group is required for aks` | The command has no `--resource-group` | Add `--resource-group RESOURCE_GROUP` |
| `Preflight failed: AKS cluster is not provisioned` | The cluster's `provisioningState` is not `Succeeded` | Wait for the operation to finish, or read the failure in `az aks show` |
| `Preflight failed: AKS OIDC issuer is disabled` | The OIDC issuer is off | Turn it on for the cluster |
| `Preflight failed: AKS Workload Identity is disabled` | Microsoft Entra Workload ID is off | Turn it on for the cluster |
| `Preflight failed: AKS NetworkPolicy engine is missing` | The cluster's network profile has no policy engine (`cilium`, `calico` or `azure`) | Use a cluster with a network policy engine. For new clusters, prefer Azure CNI powered by Cilium |
| `Preflight failed: kubectl context points to a different cluster endpoint` | The `--context` does not point at the cluster you named | Run `kubectl config get-contexts`, then pass the context for this cluster |
| `Preflight failed: at least three Ready nodes are required` | The cluster has fewer than three nodes in the `Ready` condition | Add nodes, or wait for them to become `Ready` |
| `Preflight failed: Ready nodes must span at least two zones` | The Ready nodes carry fewer than two distinct `topology.kubernetes.io/zone` labels | Spread the node group across two or more zones |
| `Preflight failed: kionga-azuredisk-premium uses an unexpected provisioner` | The class `kionga-azuredisk-premium` exists with another provisioner | Apply the example class from step 4. A class keeps its provisioner, so replace a class that has another one |
| `Preflight failed: storage class must allow expansion`, `must delay binding until scheduled` or `must retain volumes` | The class differs from the example in `allowVolumeExpansion`, `volumeBindingMode` (`WaitForFirstConsumer`) or `reclaimPolicy` (`Retain`) | Create the class from the example file with those three settings. A class keeps its binding mode and reclaim policy, so replace a class that differs |
| `Preflight failed: Command '[...]' returned non-zero exit status` | The cloud CLI or `kubectl` failed, for example because you are not signed in or the cluster name is wrong | Run the command shown in the message by hand and read its error |
| An ExternalSecret is not `Ready` | The managed identity cannot read the Kionga secrets in Key Vault, or the federated credential does not match the `kionga-secret-reader` service account | Check the client ID and vault name in `deploy/helm/secretstore-azure.example.yaml` and the federated credential |
| Pods stay in `ImagePullBackOff` | The `ghcr-pull` Secret is missing from a namespace | See [Troubleshooting](../troubleshooting.md#pods-stay-in-imagepullbackoff-or-errimagepull) |

## Related pages

- [Deploy on Kubernetes](../managed-kubernetes.md)
- [Production readiness](../production-operations.md)
- [Troubleshooting](../troubleshooting.md#kubernetes)
- [AKS Workload ID](https://learn.microsoft.com/en-us/azure/aks/workload-identity-deploy-cluster)
- [AKS network policies](https://learn.microsoft.com/en-us/azure/aks/use-network-policies)
- [Azure Disk CSI](https://learn.microsoft.com/en-us/azure/aks/create-volume-azure-disk)
- [External Secrets for Azure](https://external-secrets.io/latest/provider/azure-key-vault/)
