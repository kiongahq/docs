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

## Steps

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
   [Deploy on Kubernetes](../managed-kubernetes.md#steps), then apply the
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

The preflight reads reported configuration only. It does not prove IAM
permissions, policy behavior, disk attachment or recovery. Follow
[Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, then run
restore and failover drills before you admit users.

## Next steps

- [Production readiness](../production-operations.md).

Related: [AKS Workload ID](https://learn.microsoft.com/en-us/azure/aks/workload-identity-deploy-cluster),
[AKS network policies](https://learn.microsoft.com/en-us/azure/aks/use-network-policies),
[Azure Disk CSI](https://learn.microsoft.com/en-us/azure/aks/create-volume-azure-disk),
[External Secrets for Azure](https://external-secrets.io/latest/provider/azure-key-vault/).
