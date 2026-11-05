# Launch an Antithesis run

Input: a workload to run in Antithesis, and optionally the launcher, compute budget or other parameters to use.

Always run `snouty launch` with `SNOUTY_UNSTABLE_FEATURES=teams` set, including `snouty launch --help`, for example `SNOUTY_UNSTABLE_FEATURES=teams snouty launch --help`.

## Steps

1. **Pick the workload.** Work out from context which workload to launch and where its config directory is. If it's unclear, ask.
2. **Build it.** For a Docker Compose workload, run `docker compose build` in the config directory.
3. **Validate it.** Run `snouty validate <config_dir>` and continue only once it passes.
4. **Pick the launcher.** Use `basic_test` for Docker Compose and `basic_k8s_test` for Kubernetes, unless the user names another.
5. **Pick the flags.** Use the flags from context, such as the workload's harness. Pick the faults with `--fault-tolerance`, and keep containers out of them with `--fault-exclusions`, rather than with `--param`. For the faults, compute budget and tier, see `--fault-tolerance`, `--fault-exclusions`, `--max-compute-hours` and `--performance-tier` in `snouty launch --help`.
6. **Launch it** with `snouty launch`, and add `--param attrs.plugin_version=<version>` with the plugin version from `SKILL.md`, so the run records which plugin version launched it. Report the run ID from its output to the user. To follow the run, use the triage module.

## Compute budget

If the user gave a compute budget, it covers every run and debug run you start for the task. Before each launch, add up:

- the compute hours of your runs that have ended, from `snouty runs usage --after <when the task started>`. It lists every run on the tenant, so count only your run IDs;
- the `--max-compute-hours` of your runs still going, which `runs usage` doesn't list until they end;
- the new run's `--max-compute-hours`, or the server's default of 48 if you don't pass one.

Launch only if the total stays within the budget. Otherwise, stop and tell the user what you've spent and what you'd run next.

## Setup timeout

Fuzzing starts only once the workload reports setup complete, so keep setup fast. Raise `--setup-timeout` only if setup genuinely can't finish within the default.
