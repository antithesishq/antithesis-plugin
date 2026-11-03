# Iterate on short runs

## 1. Launch a short run

Launch with the smallest compute budget, `--max-compute-hours 12` on the standard tier. Follow `references/launch/MODULE.md` with the launcher and fault flags in `references/workload/harness.md`, and read the run with the triage module.

## 2. Keep setup fast

Setup is everything before setup complete: the deployment booting and the driver's startup, including any admin setup. Every run spends it before fuzzing.

If a run fails because the driver didn't report setup complete within `--setup-timeout`, fix the slow setup, following the timeout rule in `references/launch/MODULE.md`. The driver's output in the run's logs shows what it was still waiting for. A setup slower than 10 minutes fails a default property even when the timeout allows it.

## 3. Check the results

- **Instrumentation.** The instrumentation properties pass ("Checking it" in `references/workload/instrumentation.md`).
- **The workload starts.** `the workload starts` passes. If it fails, the first command didn't run, or the driver didn't see `/workload-active`. `snouty runs events <run_id> first_start_workload` shows whether the first command ran.
- **Behavior that needs faults.** The exploration assertions on situations and code that need faults, in the driver and in the SUT ("Exploration assertions" in `references/properties/assertions.md`), are reached, and quiet periods start and recover.
- **Client failures.** Clients restart and get partitioned (under `high_availability`), and the driver handles it. The reachable assertion where the driver notices a new boot shows this.

## 4. Fix and repeat

Run the local loop (`references/workload/local-loop.md`) again after every change, then launch the next run. A few runs are usually enough. Expect a short run to miss sometimes assertions for rare conditions, but not common ones.
