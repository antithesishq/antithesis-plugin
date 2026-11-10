# Iterate on Antithesis runs

## 1. Launch a run

Start with a short run, `--max-compute-hours 12` on the standard tier. As the workload passes the checks below and you trust it more, raise it toward 24. A longer run shows whether the workload holds up with more compute. You're done iterating when a 24-hour run passes these checks. Follow `references/launch/MODULE.md` with the launcher and fault flags in `references/workload/harness.md`, and follow the run live with the triage module's monitor mode.

## 2. Keep setup fast

Setup is everything before setup complete: the deployment booting and the driver's startup, including any admin setup. Every run spends it before fuzzing.

If a run fails because the driver didn't report setup complete within `--setup-timeout`, fix the slow setup, following the timeout rule in `references/launch/MODULE.md`. The driver's output in the run's logs shows what it was still waiting for. A setup slower than 10 minutes fails a default property even when the timeout allows it.

## 3. Check the results

Check them as they arrive, not once the run ends. A result that is final on an `in_progress` run (`references/triage/properties.md`) is final for the run.

- **Instrumentation.** The instrumentation properties pass ("Instrument the software" in `references/workload/languages.md`).
- **The workload starts.** `the workload starts` passes. If it fails, the first command didn't run, or the driver didn't see `/workload-active`. `snouty runs events <run_id> first_start_workload` shows whether the first command ran.
- **Behavior that needs faults.** The exploration assertions on situations and code that need faults, in the driver and in the SUT ("Exploration assertions" in `references/properties/assertions.md`), are reached, and eventuallys fire and find the system recovered.
- **Patterns.** Each pattern you adopted passes its own run checks.

## 4. Conclude before the next run

Classify each failing property as a SUT bug, a workload bug or expected, with the evidence for each, before you change anything or launch again. Follow the triage module. Fix workload bugs first. Tell the user about SUT bugs, and keep their assertions. Never relaunch an unchanged workload to see whether a failure repeats. You don't need the run to finish to conclude: once a final failure shows a workload bug, fix it and go to step 5.

## 5. Fix and repeat

Launch one run at a time, unless the user asks for more. If the previous run you launched is still going, cancel it with `snouty runs cancel <run_id>` before you launch the next: it tests the old workload. Run the local loop (`references/workload/local-loop.md`) again after every change, then launch the next run. A few runs are usually enough. Expect a short run to miss sometimes assertions for rare conditions, but not common ones.
