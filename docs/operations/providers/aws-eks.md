---
description: Prepare an Amazon EKS cluster for Kionga (VPC CNI network policy, EBS storage, IRSA for Secrets Manager) and install the Helm chart with the EKS overlay.
---

# Deploy on Amazon EKS

This guide shows you how to prepare an Amazon EKS cluster for Kionga and
install the chart with the EKS overlay. It adds the AWS-specific steps to
[Deploy on Kubernetes](../managed-kubernetes.md); read that guide first.

The overlay `deploy/helm/providers/eks.example.yaml` targets managed EC2 node
groups with the EBS CSI driver. It is not a recipe for EKS Auto Mode, which
uses a different storage provisioner.

## Before you begin

- An EKS cluster with managed node groups on private networking: at least three
  Ready nodes across two or more Availability Zones.
- The add-ons VPC CNI, CoreDNS, metrics-server and the AWS EBS CSI driver,
  installed and active.
- The AWS CLI, `kubectl` and Helm, signed in with an identity that can describe
  the cluster.
- The dependencies listed in [Deploy on Kubernetes](../managed-kubernetes.md#before-you-begin),
  for example Amazon RDS for PostgreSQL (TLS with `verify-full`), Redis,
  S3-compatible storage, Kafka with Kafka REST and your ML engines, with their
  credentials in AWS Secrets Manager.
- An ingress controller, wildcard DNS and TLS certificates for the console and
  workspace hosts. The overlay sets `ingress.className: nginx`; change it if
  you use another controller.

## Prepare the cluster and install

1. **Turn on network policy enforcement.** Set `enableNetworkPolicy` to `true`
   in the VPC CNI add-on configuration. Having the NetworkPolicy API is not
   enough; the CNI must enforce it.

2. **Set up IRSA.** Enable the cluster's OIDC issuer and associate the IAM OIDC
   provider. This issuer is for workload identity and is separate from the
   identity provider your users sign in with.

3. **Create the secret-reader role.** Create an IAM role that trusts the
   `kionga-secret-reader` service account in `kionga-system` and allows only
   `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` on the
   Kionga secret. Put the role ARN and region into
   `deploy/helm/secretstore-aws.example.yaml`.

4. **Create the namespace, CRDs and pull Secret**, as in steps 1 and 2 of
   [Deploy on Kubernetes](../managed-kubernetes.md#install-the-chart). Then apply the
   secret store:

    ```bash
    aws eks update-kubeconfig --name CLUSTER --region REGION --alias kionga-eks
    kubectl --context kionga-eks apply -f deploy/helm/secretstore-aws.example.yaml
    ```

5. **Create the storage class.** Check the EBS CSI driver's IAM and KMS
   permissions, then apply the example class `kionga-ebs-gp3` (encrypted gp3,
   expandable, retained, bound on first use):

    ```bash
    kubectl --context kionga-eks apply -f deploy/helm/providers/eks-storageclass.example.yaml
    ```

    EBS volumes are zonal and single-writer. Keep shared project data in object
    storage, not in a volume shared by many workspaces.

6. **Run the preflight check.**

    ```bash
    python3 deploy/scripts/cloud-preflight.py eks --context kionga-eks --cluster CLUSTER --region REGION
    ```

    It confirms that the context points at this cluster, that the cluster is
    active, that the IAM OIDC provider is associated, that the VPC CNI (with
    network policy) and EBS CSI add-ons are active, that there are three Ready
    nodes in two zones, and that the storage class is configured as above.

7. **Check and install** with the EKS overlay after your values file:

    ```bash
    bash deploy/scripts/deploy-kubernetes.sh kionga-eks kionga-system /secure/production.yaml deploy/helm/providers/eks.example.yaml
    bash deploy/scripts/deploy-kubernetes.sh kionga-eks kionga-system /secure/production.yaml deploy/helm/providers/eks.example.yaml --apply
    ```

In CI, deploy with a short-lived federated AWS role, not a long-lived access key.

## Verify

1. List the platform resources:

    ```bash
    kubectl --context kionga-eks -n kionga-system get pods,services,ingress,hpa,pdb
    kubectl --context kionga-eks -n kionga-system get externalsecrets
    ```

    Every pod is `Running` and ready, and every ExternalSecret has the
    `Ready` condition set to `True`.

2. Run the production verifier from
   [Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, with
   `--context kionga-eks`. It exits with status 0 after it prints the cluster and
   HTTP checks, such as `Cluster: replicas, probes, digests, TLS ingress, HPA,
   isolation, and node spread pass`. On a failure it prints
   `Acceptance failed: <reason>` and exits with status 1.

The preflight reads reported configuration only. It does not prove IAM permissions, network policy enforcement, EBS volume attachment or failover. Run restore and failover drills before you admit users.

## Troubleshooting

The preflight in step 6 prints `Preflight passed. Confirm actual policy
enforcement, IAM, PVC provisioning, and failover in staging.` when every check
passes. On a failure it prints `Preflight failed: <reason>` and exits with
status 1.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Preflight failed: --region is required for eks` | The command has no `--region` | Add `--region REGION` |
| `Preflight failed: EKS cluster is not ACTIVE` | The cluster is still creating, updating or failed | Wait until `aws eks describe-cluster` reports `ACTIVE` |
| `Preflight failed: EKS OIDC issuer missing (required for IRSA)` | The cluster has no OIDC issuer | Enable the issuer, as in step 2 |
| `Preflight failed: EKS IAM OIDC provider is not associated for IRSA` | The IAM OIDC provider for the cluster issuer does not exist in the account | Associate the provider, as in step 2 |
| `Preflight failed: EKS add-on vpc-cni is not ACTIVE` or `EKS add-on aws-ebs-csi-driver is not ACTIVE` | The add-on is missing, or still installing | Install or repair the add-on, then wait for `ACTIVE` |
| `Preflight failed: EKS VPC CNI NetworkPolicy is disabled` | `enableNetworkPolicy` is not `true` in the VPC CNI configuration | Set it, as in step 1 |
| `Preflight failed: kubectl context points to a different cluster endpoint` | The `--context` does not point at the cluster you named | Run `kubectl config get-contexts`, then pass the context for this cluster |
| `Preflight failed: at least three Ready nodes are required` | The cluster has fewer than three nodes in the `Ready` condition | Add nodes, or wait for them to become `Ready` |
| `Preflight failed: Ready nodes must span at least two zones` | The Ready nodes carry fewer than two distinct `topology.kubernetes.io/zone` labels | Spread the node group across two or more zones |
| `Preflight failed: kionga-ebs-gp3 uses an unexpected provisioner` | The class `kionga-ebs-gp3` exists with another provisioner | Apply the example class from step 5. A class keeps its provisioner, so replace a class that has another one |
| `Preflight failed: storage class must allow expansion`, `must delay binding until scheduled` or `must retain volumes` | The class differs from the example in `allowVolumeExpansion`, `volumeBindingMode` (`WaitForFirstConsumer`) or `reclaimPolicy` (`Retain`) | Create the class from the example file with those three settings. A class keeps its binding mode and reclaim policy, so replace a class that differs |
| `Preflight failed: Command '[...]' returned non-zero exit status` | The cloud CLI or `kubectl` failed, for example because you are not signed in or the cluster name is wrong | Run the command shown in the message by hand and read its error |
| An ExternalSecret is not `Ready` | The `kionga-secret-reader` role cannot read the Kionga secret in Secrets Manager, or the secret names do not match `externalSecrets.targets` | Check the role ARN and region in `deploy/helm/secretstore-aws.example.yaml`, and the role's `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` permissions |
| Pods stay in `ImagePullBackOff` | The `ghcr-pull` Secret is missing from a namespace | See [Troubleshooting](../troubleshooting.md#pods-stay-in-imagepullbackoff-or-errimagepull) |

## Related pages

- [Deploy on Kubernetes](../managed-kubernetes.md)
- [Production readiness](../production-operations.md)
- [Troubleshooting](../troubleshooting.md#kubernetes)
- [EKS VPC CNI network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html)
- [EBS CSI StorageClass](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)
- [External Secrets for AWS](https://external-secrets.io/latest/provider/aws-secrets-manager/)
