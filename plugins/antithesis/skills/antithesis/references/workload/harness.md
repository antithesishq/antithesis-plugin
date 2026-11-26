# Wire up the harness

`docker-compose.yaml` lives in `config/` (`references/workload/layout.md`). Every service needs an explicit `image:`. snouty rejects services without one.

## The driver container

Build the driver into its own image, and add it to `docker-compose.yaml` as a service named `driver`. The driver program is the container's main process (`references/workload/driver.md`). Give it no `restart:` policy: an eventually ends its timeline by exiting the driver with status 0.

```yaml
driver:
  container_name: driver
  hostname: driver
  platform: linux/amd64
  build:
    context: ..
    dockerfile: driver/Dockerfile
  image: driver:latest
  environment:
    KV_URLS: http://kv1:8000,http://kv2:8000
```

`driver/Dockerfile`, for a driver that compiles to one binary. Its build stage, from `references/workload/languages/<language>.md`, leaves the binary at `/out/driver`. If Antithesis instruments the driver's language, instrument it like any other component ("Instrument the software" in `references/workload/languages.md`), and copy its symbol files from `/symbols` too. When you choose a base image, take it from `references/workload/images.md`. An interpreted driver keeps its runtime in the final image and runs its script as `CMD`; the test template lines stay the same:

```dockerfile
# The driver's build stage, from references/workload/languages/<language>.md

FROM <Runtime image>
COPY --from=build /out/driver /usr/local/bin/
# Only for an instrumented driver:
COPY --from=build /symbols /symbols
COPY driver/first_start_workload driver/serial_driver_wait /opt/antithesis/test/v1/main/
RUN chmod 755 /opt/antithesis/test/v1/main/*
CMD ["/usr/local/bin/driver"]
```

## The test template

The driver image's test template, `/opt/antithesis/test/v1/main/`, holds exactly two test commands, `first_start_workload` and `serial_driver_wait`. No other container has a test template. The directory name `main` is the test name; any name works.

`driver/first_start_workload`:

```sh
#!/bin/sh
touch /workload-active
```

Antithesis runs the first command once at the start of every timeline, after setup complete and the root snapshot, in the container that holds it. So the file appears exactly when fuzzing starts, and every timeline starts from a snapshot without it.

`driver/serial_driver_wait`:

```sh
#!/bin/sh
sleep 30
exit 0
```

This driver keeps the timeline running as long as Antithesis finds it interesting. Without it, most timelines stop after about 20 seconds of fuzzing.

Test commands must be executable, which the Dockerfile's `chmod` ensures. `snouty validate` reports any that aren't.

## Shared volumes

Use a shared volume only when containers need to share files, such as for out-of-band facts ("Shared volumes for out-of-band facts" in `references/workload/driver.md`). Mount one named volume in the node that writes and in the driver:

```yaml
kv1:
  volumes: [shared:/shared]
driver:
  volumes: [shared:/shared]
volumes:
  shared:
```

A new volume takes the ownership of its mount point in the image. If the node runs as a non-root user, create the mount point owned by that user in its Dockerfile, for example `RUN mkdir /shared && chown 999:999 /shared`; otherwise Docker creates it owned by root, and the node can't write there.

## Pick the faults, and exclude the driver

Launch every run of the workload with the `basic_test` launcher, unless the user names another, following `references/launch/MODULE.md`, and these flags:

```bash
--fault-tolerance high_availability
--fault-exclusions '^driver$'
```

`--fault-tolerance` picks the fault profile (`references/antithesis/faults.md`). `high_availability` kills, stops and partitions containers. Use `resilient` only for a system that isn't meant to survive losing a node or a partition, such as a single-node system; it pauses containers and degrades the network, but never kills or partitions them.

`--fault-exclusions` is a regex matched against container names, so `^driver$` relies on the driver's `container_name: driver` ("The driver container"); without it, Compose names the container `<project>-driver-1` and the regex matches nothing. Exclude only the driver. The exclusion also keeps all of the driver's connections unfaulted, which `references/patterns/stateful-clients.md` and `references/patterns/log-forwarding.md` rely on, so a regex that misses the driver silently faults them.

## Debug tools

To debug a failure, you run commands at a moment in a container with `snouty runs exec` (`references/debug/MODULE.md`). In the Antithesis environment, exec can only access tools included in the image. So ensure that workload images contain useful debugging tools such as `curl`, `jq`, and the SUT's admin or inspection CLI, such as `fdbcli`, `etcdctl`, or `psql`.

A pattern you adopted (`references/patterns/MODULE.md`) may add services and environment variables.
