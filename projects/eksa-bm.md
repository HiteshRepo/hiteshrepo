## Bare metal K8s cluster provisioning

- This project is to help users provision K8s cluster on bare metal with the help of EKSA (AWS EKS anywhere).
- Provide APIs/CLI to perform below:
    - Provisioning cluster - single node and multi-nodes
    - Delete cluster
    - Rollback cluster provisioning & Restart from beginning
    - Backup & Restore cluster state
    - Scaling CP & DP nodes of the cluster
    - Upgrade CP & DP nodes of the cluster
    - Terminating ongoing cluster ops and restore to previous stable state
- Tasks in pipeline: private registry support, open-api config support.
- Overview: https://docs.rafay.co/clusters/eksa_bm/overview/