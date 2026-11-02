# Iterating on short runs

## 1. Launch a short run

Launch a run with the smallest compute budget, `--max-compute-hours 12` on the standard tier (15 minutes of fuzzing). Follow `references/launch/MODULE.md`, use the launcher and fault exclusions in `references/workload/harness.md`, and read the run with the triage module.

If a run fails because the system didn't reach setup complete within `--setup-timeout`, find out why setup is slow and fix it, rather than raising the timeout. A setup slower than 10 minutes fails a default property even when the timeout allows it.

## 2. Check the results

- **Instrumentation.** `Software was instrumented` and `Every instrumented module has symbols` should pass.
- **Behavior that needs faults.** Sometimes assertions that need faults are reached, and quiet periods start and recover.
- **Client failures.** Clients restart and get partitioned during runs, and the driver handles it. A reachable assertion where it notices a new boot makes this easy to check.
- **Coverage** of code only faults reach, and of services local coverage couldn't measure:

  ```bash
  snouty --json runs show <run_id> > run.json
  jq '.results.coverage.files | keys' run.json
  ```

  For Go, Rust and C/C++, `.results.coverage.files` maps each instrumented file, by its build path, to the functions that ran, with the spans reached (`[start_line, start_col, end_line, end_col]`).

## 3. Fix and repeat

Run the local loop again after every change, then launch the next run. A few runs are usually enough.

A short run reaches little of the system's state, so don't worry too much about failing sometimes assertions for rare conditions. Common sometimes assertions should still fire.
