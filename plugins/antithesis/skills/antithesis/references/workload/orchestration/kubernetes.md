# Kubernetes

Antithesis runs the manifests on a single-node K3s cluster with CoreDNS and the `local-path` storage class, and no Ingress controller, ServiceLB, metrics-server or IPv6 (`snouty docs show /docs/setup/kubernetes/`). Read `snouty docs show /docs/best_practices/k8s_best_practices/` before you write the manifests.

## The config directory

`config/manifests/` holds raw manifests, and nothing else goes in `config/` but the files they need. Render a Helm chart with `helm template <release> <chart> -n <namespace> --include-crds -f <values> --output-dir`, and Kustomize with `kubectl kustomize`. Ask the user for the values file their deployment uses; a chart's own `values.yaml` holds defaults, not their setup.

Put every resource in one namespace, set explicitly, with a `Namespace` manifest. Then cut the manifests down to the SUT and what it needs to run, since every pod costs CPU in the run:

- **Drop:** service meshes and their sidecars (Istio, Linkerd), cert-manager (generate a self-signed certificate if the SUT needs TLS), `NetworkPolicy`, autoscalers, `PodDisruptionBudget`, `ResourceQuota`, `LimitRange`, observability sidecars and Prometheus operator resources, `Ingress`, cloud IAM annotations, and anti-affinity or topology spread rules that need more than one node.
- **Replace:** `ExternalSecret` and `SealedSecret` with a plain `Secret` holding test values, a `LoadBalancer` or `NodePort` Service with `ClusterIP`, and any storage class with `local-path`, `ReadWriteOnce`.
- **Ask the user** about an operator or custom resource you don't recognize: what it does, and whether the SUT needs it at runtime. Keep an operator that runs the SUT, rather than rewriting it as plain manifests.

Tell the user what you dropped or changed.

**Resources.** The requests of every pod together must stay under 1 CPU and 10 GiB of memory, or pods stay `Pending`. Divide them between the pods, such as `cpu: 250m` for each of three SUT replicas, and the driver. Set memory limits, and no CPU limits.

**Probes.** Give every SUT pod a readiness probe. Keep liveness probes lenient, or drop them: a paused or throttled node fails a tight one, and Kubernetes kills it, a fault Antithesis didn't choose.

**Restarts.** Antithesis can't restart a killed pod: Kubernetes does, with its usual restart policy, so a pod comes back after a crash backoff that grows to 5 minutes. Give the driver's eventually a deadline that allows for it.

**Images.** Name every image fully qualified, with its registry and a tag other than `latest`, or a digest: `docker.io/library/postgres:17`. Never set `imagePullPolicy: Always`: the cluster has no internet. Name each image you build as `<registry>/<name>:<tag>`, with the `registry` from `snouty settings show`. `snouty launch` doesn't push them for Kubernetes ("Launch"). An operator's images that no manifest names need `--param antithesis.images=...` (`snouty launch --help`).

## The driver

Run the driver as a bare `Pod` named `driver`, with `restartPolicy: Never`, so its exit with status 0 ends the timeline, and `--fault-exclusions '^driver$'` matches the pod's name. Reach the SUT through Service DNS names, such as `kv-0.kv` for a StatefulSet's pod behind a headless Service.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: driver
  namespace: kv
spec:
  restartPolicy: Never
  containers:
    - name: driver
      image: <registry>/driver:v1
      env:
        - name: KV_URLS
          value: http://kv-0.kv:8000,http://kv-1.kv:8000
      resources:
        requests: {cpu: 100m, memory: 256Mi}
        limits: {memory: 256Mi}
```

A pod's hostname is its name, such as `kv-0`, and faults and logs name pods the same way. Run a pattern's client containers as a StatefulSet, so each has a stable name.

## Shared volumes

Share a volume between pods with one `PersistentVolumeClaim` on `local-path`, `ReadWriteOnce`, mounted by every pod that shares it. `local-path` creates the directory writable by every user.

## Build and validate

Build each image with `docker build` under its full name, then run `snouty validate <config_dir>`. For Kubernetes it only checks the manifests, without running them: fix every finding it denies. Then deploy locally ("Run locally") until setup complete arrives, which is the check `snouty validate` gives a Compose workload.

## Run locally

Use a [k3d](https://k3d.io) cluster of your own, with its own kubeconfig, so the user's current `kubectl` context never changes. Never deploy to a cluster you didn't create without asking the user. Delete the cluster when you're done with it.

```bash
k3d cluster create <workload> --no-lb --kubeconfig-update-default=false \
  --k3s-arg '--disable=traefik,servicelb,metrics-server@server:0'
export KUBECONFIG=$(k3d kubeconfig write <workload>)
kubectl config set-context --current --namespace <namespace>
k3d image import -c <workload> <each image you built>
```

Write the coverage build as a Kustomize overlay outside `config/`, such as `coverage/kustomization.yaml`, that swaps in each system service's coverage image, mounts a `coverage` claim at `/coverage` in every pod, and sets the local-loop variables on the driver ("Run the workload" in `references/workload/local-loop.md`). Write the driver's SDK output to the claim, `ANTITHESIS_SDK_LOCAL_OUTPUT=/coverage/driver/sdk.jsonl`, so it survives the driver's exit. Then:

```bash
kapp delete -a <workload> --yes; kubectl kustomize coverage | kapp deploy -a <workload> -f - --yes &&
kubectl exec driver -- /opt/antithesis/test/v1/main/first_start_workload &&
timeout 600 sh -c 'until kubectl exec <a SUT pod> -- grep -qs antithesis_setup /coverage/driver/sdk.jsonl; do sleep 5; done' &&
sleep 300
kubectl scale statefulset,deployment --all --replicas 0   # stops the system gracefully
kubectl wait --for=delete pod -l <SUT pod label> --timeout 2m
docker exec k3d-<workload>-server-0 sh -c 'cd /var/lib/rancher/k3s/storage/*_<namespace>_coverage && tar -c .' | tar -x -C <run directory>
```

The last line copies the whole claim from the node. Rename each `<service>/sdk.jsonl` in it to `sdk-<service>.jsonl`, as "Check the behavior" in `references/workload/local-loop.md` expects. kapp waits until every resource is ready, and fails on one that never is: `kubectl get events` and `kubectl describe pod <pod>` say why.

- **Logs:** `kubectl logs <pod>`, and `--previous` for the container before its last restart.
- **A command in a pod:** `kubectl exec <pod> -- <command>`.
- **Exit status:** `kubectl get pod driver`, which shows `Completed` after an exit with status 0.
- **A clean stop:** `kubectl delete pod <pod>` returns well before the 30-second grace period ends, and `kubectl logs` beforehand, with `-f`, shows a clean shutdown.
- **Restart and pause:** `kubectl delete pod <pod>` restarts it. To pause one, `docker exec k3d-<workload>-server-0 kill -STOP <pid>`, then `-CONT`, with the PID from `ps` there.

## Launch

Use the `basic_k8s_test` launcher. `snouty launch` builds and pushes only the config image, so push each image you built first, with `docker push <registry>/<name>:<tag>`, after setting up the credential helper (`snouty docker-credential --help`).
