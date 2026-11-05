# Launch an Antithesis run

Input: a workload to run in Antithesis, and optionally the launcher, compute budget or other parameters to use.

Always run `snouty launch` with `SNOUTY_UNSTABLE_FEATURES=teams` set, including `snouty launch --help`, for example `SNOUTY_UNSTABLE_FEATURES=teams snouty launch --help`.

## Steps

1. **Pick the workload.** Work out from context which workload to launch and where its config directory is. If it's unclear, ask.
2. **Build it.** For a Docker Compose workload, run `docker compose build` in the config directory.
3. **Validate it.** Run `snouty validate <config_dir>` and continue only once it passes.
4. **Pick the launcher.** Use `basic_test` for Docker Compose and `basic_k8s_test` for Kubernetes, unless the user names another.
5. **Pick the flags.** Use the flags from context, such as the workload's harness. Pick the faults with `--fault-tolerance`, and keep containers out of them with `--fault-exclusions`, rather than with `--param`. For the faults, compute budget and tier, see `--fault-tolerance`, `--fault-exclusions`, `--max-compute-hours` and `--performance-tier` in `snouty launch --help`.
6. **Launch it** with `snouty launch`, and report the run ID from its output to the user. To follow the run, use the triage module.

## Setup timeout

Fuzzing starts only once the workload reports setup complete, so keep setup fast. Raise `--setup-timeout` only if setup genuinely can't finish within the default.
