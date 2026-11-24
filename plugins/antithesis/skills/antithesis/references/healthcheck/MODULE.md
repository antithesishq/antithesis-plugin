# Healthcheck a workload

Input: a run of the workload, in progress or ended. If you were given something else, find the run ID with `references/triage/run-discovery.md`.

This module checks how the workload spends a run's compute: CPU, log volume, memory, timeline depth and progress. A workload with one of these issues can pass every property and still find few bugs. Failing properties belong to the triage module, and setup problems, such as instrumentation or a slow setup, to `references/workload/run-loop.md`.

## Gather the evidence

- **Read the efficiency properties** with `snouty runs properties <run_id> --detail --name <name>`, for each of `Virtual time per wall time`, `Test ran with full parallelism`, `Peak memory usage`, `Customer output volume` and `Logging output was limited`. They report values, not moments (`references/triage/properties.md`).
- **List the containers** from the workload's `docker-compose.yaml`.
- **Sample a moment deep in a timeline.** Pick a moment of the run at a vtime well past the workload's start, such as a sampled example of an action's exploration assertion. Choose a run to execute in as `references/debug/MODULE.md` says. In the guest, without `--container`, run `top` over 30 s of vtime, with `--events` to also capture what every container logs meanwhile:

  ```bash
  mkdir -p /tmp/healthcheck
  snouty runs exec "$RUN_ID" --events --timeout 5m "$INPUT_HASH" "$VTIME" \
    'top -b -c -w 200 -d 30 -n 2' > /tmp/healthcheck/sample.log
  ```

  The second `top` snapshot shows each process's share of CPU over the 30 s.

## Known issues

Check each. Report an issue only with evidence from the run.

- **Busy containers.** `Virtual time per wall time` times the number of containers is below 1, or a process in the sample uses CPU out of proportion to the work it does. Antithesis fast-forwards only through time when every process is idle, so CPU spent on nothing slows every timeline. Common causes:
  - A Compose `healthcheck:`. It runs its command in its container at every `interval`, for the whole run, but serves only to order startup. Remove it, change each `depends_on` on it from `condition: service_healthy` to `service_started`, and have the driver wait for the service ("Starting up" in `references/workload/driver.md`). Or raise its `interval` to minutes, with a short `start_interval` during its `start_period`, so dependents still start soon.
  - A loop that polls or spins while idle: a sidecar's `while true; do ...; sleep 0.1; done`, a SUT worker that busy-waits, a rule that polls. Make it block, or sleep for seconds.
  - Background work configured to run constantly, or a client that retries with no backoff.
  - Code that reads the clock in a tight loop: `RDTSC` and `RDRAND` are expensive in Antithesis.
- **Excessive logs.** `Logging output was limited` fails, or `total_output_rate` in `Customer output volume` approaches its limit of 200 MB per test hour. Count each container's lines with `snouty runs search <run_id> --count 'matches({container: "<name>"})'`, then read the loudest container's lines in the sample. Lower that logger's level in the system's configuration, or adopt the retroactive-logging pattern (`references/patterns/MODULE.md`).
- **Memory pressure.** `Peak memory usage` fails or nears its 95% limit, or `Test ran with full parallelism` fails. The machine has 10 GB, shared by every container. Cap each runtime's heap and caches, such as the JVM's `-Xmx`, and shrink the data the workload writes.
- **Shallow timelines.** The eventually ends most timelines soon after `the workload starts`, so few timelines reach deep states. Compare the vtimes of the eventually's recovery assertion hits, from `snouty runs search`, with how long the workload runs before them. Lower the probability of the eventually's draw ("Eventually" in `references/workload/driver.md`).
- **A stalled driver.** The sample shows few or no driver actions in 30 s: a rule waits on a slow request, holds a lock during one, or deadlocks, and the whole round waits for it. Execute commands in the driver container at the moment to see where it waits, then follow "Keep rules fast" in `references/workload/driver.md`.
- **A system that's mostly down.** Most of the sample's requests fail, or the system's success assertions have far more counterexamples than examples. Production-scale timeouts, such as heartbeats, elections, sessions or reconnect backoff measured in minutes, keep the system recovering from one fault until the next. Scale them down to the faults' timescale, as `snouty docs show /docs/best_practices/optimizing/` says under `Configure for testing`.

## Report

List each issue found, the evidence for it, and the fix, most wasteful first, then the checks that passed. If the task includes fixing them, change the workload, and check the next run the same way (`references/workload/run-loop.md`).
