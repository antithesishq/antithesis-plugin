# Wire up the harness

Every service in `docker-compose.yaml` needs an explicit `image:`. snouty rejects services without one.

## 1. The driver container

Build the driver into its own image, and add it to `docker-compose.yaml` as a service named `driver`. The driver binary is the container's main process (`references/workload/driver.md`). Give it no `restart:` policy: an eventually ends its timeline by exiting the driver with status 0.

```yaml
driver:
  container_name: driver
  hostname: driver
  platform: linux/amd64
  build:
    context: .
    dockerfile: driver/Dockerfile
  image: driver:latest
  environment:
    KV_URLS: http://kv1:8000,http://kv2:8000
```

`driver/Dockerfile`:

```dockerfile
FROM rust:1-bookworm AS build
WORKDIR /src
COPY driver/ .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=build /src/target/release/driver /usr/local/bin/
COPY driver/first_start_workload /opt/antithesis/test/v1/main/
RUN chmod 755 /opt/antithesis/test/v1/main/first_start_workload
CMD ["/usr/local/bin/driver"]
```

## 2. The test template

The driver image's test template, `/opt/antithesis/test/v1/main/`, holds exactly one test command, `first_start_workload`. No other container has a test template. The directory name `main` is the test name; any name works.

`driver/first_start_workload`:

```sh
#!/bin/sh
touch /workload-active
```

Antithesis runs the first command once at the start of every timeline, after setup complete and the root snapshot, in the container that holds it. So the file appears exactly when fuzzing starts, and every timeline starts from a snapshot without it.

Test commands must be executable, which the Dockerfile's `chmod` ensures. `snouty validate` reports any that aren't.

## 3. Shared volumes

For out-of-band facts ("Shared volumes for out-of-band facts" in `references/workload/driver.md`), mount one named volume in the node that writes and in the driver:

```yaml
kv1:
  volumes: [shared:/shared]
driver:
  volumes: [shared:/shared]
volumes:
  shared:
```

A new volume takes the ownership of its mount point in the image. If the node runs as a non-root user, create the mount point owned by that user in its Dockerfile, for example `RUN mkdir /shared && chown 999:999 /shared`; otherwise Docker creates it owned by root, and the node can't write there.

## 4. Pick the faults, and exclude the driver

Launch every run of the workload with the `basic_test` launcher, following `references/launch/MODULE.md`, and these flags:

```bash
--fault-tolerance high_availability
--fault-exclusions '^driver$'
```

`--fault-tolerance` picks the fault profile (`references/antithesis/faults.md`). `high_availability` kills, stops and partitions containers. Use `resilient` only for a system that isn't meant to survive losing a node or a partition, such as a single-node system; it pauses containers and degrades the network, but never kills or partitions them.

`--fault-exclusions` is a regex matched against container names, so `^driver$` relies on the driver's `container_name: driver` (section 1); without it, Compose names the container `<project>-driver-1` and the regex matches nothing. Exclude only the driver.

A pattern you adopted (`references/patterns/MODULE.md`) may add services, volumes and environment variables.
