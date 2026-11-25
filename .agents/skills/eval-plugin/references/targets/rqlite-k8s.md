# Target: rqlite on Kubernetes

The Kubernetes fixture: rqlite, as in `references/targets/rqlite.md`, deployed from rqlite's own Kubernetes manifests instead of Docker Compose. Run it as its own track, and compare it with an `rqlite` track to see what the orchestration changes: the same system, the same focus and the same bugs to find.

- **Repository:** <https://github.com/rqlite/rqlite>, at the same commit as the `rqlite` track. The sandbox needs Go and Cargo, as for `rqlite`, and `kubectl`, `k3d`, `kapp` and `helm`.
- **Deployment:** "We run rqlite on Kubernetes, from the StatefulSet in <https://github.com/rqlite/kubernetes-configuration> (`statefulset-3-node.yaml` and `service.yaml`), so I want the workload to run it that way too."
- **Focus, catalog, property to define, client library, cross-node checks:** as in `references/targets/rqlite.md`.

## What the manifests test

rqlite's manifests break several Antithesis rules, so a workload session that follows the plugin has to fix each one. Score whether it does, before its first launch:

- `image: rqlite/rqlite` is neither fully qualified nor pinned to a tag, and is the upstream build, not the instrumented one: the session must build its own image, name it under the tenant registry, and push it before launching.
- `storageClassName: "standard"` leaves the claims `Pending`: it must become `local-path`.
- No namespace is set on any resource.
- No resource requests: the pods and the driver together must request under 1 CPU.
- The liveness probe (`/readyz?noleader`, 3 failures of 2 s) is tight enough to kill a paused node.
- `-disco-mode=dns` with `publishNotReadyAddresses` must still form a cluster after a pod restarts with a new IP address.

And during the session:

- It validates locally on its own k3d cluster, leaves the user's `kubectl` context alone, and deletes the cluster at the end.
- It uses `kubectl exec` from the guest, not `snouty runs exec --container`, to run commands in a pod.

## Setup and cost

No eval has run this target yet. Record the image build time, the local k3d loop's time, setup time in a run, and billing here after the first one.

## Expected findings

The bugs in `references/targets/rqlite.md`, at the same commit. Kubernetes restarts a killed pod after its own backoff, rather than when the fault ends, which may change which of them a run reaches. Never mention them in a prompt.

## Quirks

- A killed pod's fault event has `max_duration` `"0"`, since Kubernetes, not Antithesis, restarts it.
