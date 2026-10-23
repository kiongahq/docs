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

## Steps

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
   [Deploy on Kubernetes](../managed-kubernetes.md#steps). Then apply the
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

## Verify

The preflight reads reported configuration only. It does not prove IAM
permissions, network policy enforcement, EBS volume attachment or failover.
Follow [Verify](../managed-kubernetes.md#verify) in the Kubernetes guide, then
run restore and failover drills before you admit users.

## Next steps

- In CI, deploy with a short-lived federated AWS role, not a long-lived access
  key.
- [Production readiness](../production-operations.md).

Related: [EKS VPC CNI network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html),
[IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html),
[EBS CSI StorageClass](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html),
[External Secrets for AWS](https://external-secrets.io/latest/provider/aws-secrets-manager/).
