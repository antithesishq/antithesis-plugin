# Launch an Antithesis run

Input: a workload to run in Antithesis, and optionally the launcher, compute budget or other parameters to use.

## Steps

1. **Pick the workload.** Work out from context which workload to launch and where its config directory is. If it's unclear, ask.
2. **Check the config directory.** `snouty launch` copies all of it into the config image, so it should only contain a docker-compose.yaml (or Kubernetes manifest), any files referenced in mounts, and any environment files (like .env). Consider using a `.dockerignore` if you can't restructure the config directory.
3. **Build it.** For a Docker Compose workload, run `docker compose build` in the config directory.
4. **Validate it.** Run `snouty validate <config_dir>` and continue only once it passes.
5. **Pick the launcher.** Use `basic_test` for Docker Compose and `basic_k8s_test` for Kubernetes, unless the user names another.
6. **Pick the flags.** Use the flags from context, such as the workload's harness. Pick the faults with `--fault-tolerance`, and keep containers out of them with `--fault-exclusions`, rather than with `--param`. Always pass `--max-compute-hours`, rather than relying on the server's default. For the faults, compute budget and tier, see `--fault-tolerance`, `--fault-exclusions`, `--max-compute-hours` and `--performance-tier` in `snouty launch --help`. Add `--param attrs.plugin_version=<version>` with the plugin version from `SKILL.md`.
7. **Launch it** with `snouty launch` and report the run ID from its output to the user.

## Compute budget

The task's compute budget, from the user or the default in `SKILL.md`, covers every run and debugging session you start for the task. Before each launch, add up:

- the compute hours of your runs that have ended, from `snouty runs usage --after <when the task started>`. It lists every run on the tenant, so count only your run IDs;
- the `--max-compute-hours` of your runs still going, which `runs usage` doesn't list until they end;
- the new run's `--max-compute-hours`.

Launch only if the total stays within the budget. Otherwise, stop and tell the user what you've spent and what you'd run next.

## Setup timeout

Fuzzing starts only once the workload reports setup complete, so keep setup fast. Raise `--setup-timeout` only if setup genuinely can't finish within the default.
