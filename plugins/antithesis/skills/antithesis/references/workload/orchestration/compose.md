# Docker Compose

## The config directory

`config/` holds `docker-compose.yaml` and the files it mounts. Every service needs an explicit `image:`. snouty rejects services without one.

**Restarts.** Antithesis restarts a killed or stopped container after the time the fault chose. Give no service a `restart:` policy: Compose would bring it back early, cancelling the fault.

## The driver

Add the driver as a service named `driver`. `container_name: driver` makes the `--fault-exclusions '^driver$'` regex match: without it, Compose names the container `<project>-driver-1`, and the regex matches nothing.

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

## Shared volumes

Mount one named volume in each container that shares it:

```yaml
kv1:
  volumes: [shared:/shared]
driver:
  volumes: [shared:/shared]
volumes:
  shared:
```

A new volume takes the ownership of its mount point in the image. If a container runs as a non-root user, create the mount point owned by that user in its Dockerfile, for example `RUN mkdir /shared && chown 999:999 /shared`; otherwise Docker creates it owned by root, and the container can't write there.

## Build and validate

Run `docker compose build` in the config directory, then `snouty validate <config_dir>`, which also waits for setup complete.

## Run locally

Add `docker-compose.coverage.yaml` beside `docker-compose.yaml`. It overrides each system service with its coverage Dockerfile, mounts a shared `coverage` volume, and sets the local-loop variables on the driver ("Run the workload" in `references/workload/local-loop.md`):

```yaml
  driver:
    environment:
      ANTITHESIS_SDK_LOCAL_OUTPUT: /tmp/sdk.jsonl
```

Run the loop as one command, since `COMPOSE_FILE` applies only within it:

```bash
export COMPOSE_FILE=docker-compose.yaml:docker-compose.coverage.yaml
docker compose down -v && docker compose up -d --build &&
docker compose exec -T driver /opt/antithesis/test/v1/main/first_start_workload &&
timeout 600 sh -c 'until docker compose exec -T driver grep -qs antithesis_setup /tmp/sdk.jsonl; do sleep 5; done' &&
sleep 300
docker compose cp driver:/tmp/sdk.jsonl .
# For each SUT service with assertions:
docker compose cp <service>:/coverage/<service>/sdk.jsonl sdk-<service>.jsonl
docker compose stop
```

With the same `COMPOSE_FILE`:

- **Logs:** `docker compose logs <service>`.
- **A command in a container:** `docker compose exec -T <service> <command>`.
- **Exit status:** `docker compose ps -a`. `docker compose cp` still copies from a stopped container.
- **A clean stop:** `docker compose stop <service>` returns without waiting out its 10-second timeout, and the log shows a clean shutdown.
- **Restart and pause:** `docker compose restart <service>`, and `docker compose pause <service>` then `unpause`.

## Launch

Use the `basic_test` launcher. `snouty launch` pushes every image the compose file names from the local image store, so build them first.
