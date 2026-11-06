# Build a workload

Input: a system to test in Antithesis, and optionally the behaviors to focus on.

## What a workload is

- **The driver.** One Rust binary written with [hegel](https://hegel.dev), using `#[hegel::main]`. It picks actions at random, sends them to the system, and records each outcome in a model of what the system should contain. Every random choice comes from hegel, so Antithesis controls it.
- **Exploration assertions,** in the driver and in the system's own code, which show Antithesis the states worth reaching. Put an assertion on a node's internal state in that node's code, where you can change it, so it fires at the moment the state occurs.
- **Patterns,** only for systems that need them: running the system's stateful client library in faulted client containers, or forwarding the system's logs to the driver. `references/patterns/MODULE.md` says when each applies.

The driver binary is the main process of its own fault-excluded container. It waits for the system, reports setup complete, then waits for `/workload-active`, which the container's one `first_` test command creates when fuzzing starts. Every decision is made in the driver.

The SUT itself is built with Antithesis coverage instrumentation.

## Steps

1. **Map what the workload must reach.** Follow `references/workload/surface.md`.
2. **Pick the patterns.** Read `references/patterns/MODULE.md`, and adopt only the patterns whose conditions hold for this system. By default, adopt none.
3. **Pick the model.** For every in-scope item, decide what the driver must record so an assertion can judge each response.
4. **Instrument the SUT.** Follow `references/workload/instrumentation.md`. Add exploration assertions to its code, following "Exploration assertions" in `references/properties/assertions.md`. They are the default way to see a node's internal state.
5. **Write the driver,** including its startup: the waits for the system, admin setup, setup complete and the `/workload-active` wait. Follow `references/workload/driver.md`.
6. **Wire up the harness:** the `driver` container with its `first_` test command, any shared volumes, and the fault flags. Follow `references/workload/harness.md`.
7. **Build and validate.** Build the images, run the instrumentation checks, then run `snouty validate <config_dir>`. Commit every file the images build from, and check `git status --ignored`, since ignore rules can drop harness files.
8. **Iterate locally** on coverage and the exploration assertions (`references/properties/assertions.md`). Follow `references/workload/local-loop.md`.
9. **Iterate on short Antithesis runs.** Follow `references/workload/run-loop.md`.
10. **Launch the final run** with `--max-compute-hours 24` on the standard tier. Follow `references/launch/MODULE.md` with the launcher and fault flags in `references/workload/harness.md`, and read the run with the triage module.
11. **Report, or keep going.** Go by what the user asked for. A compute budget is a ceiling, not a request to spend it. If they asked only for a workload, report to the user, including which patterns you adopted and why, and any step you skipped or changed, and why, then stop. If they asked you to find bugs, keep going until the goal is met or their compute budget runs out. If they gave no budget, don't launch past step 10: report, and ask for one. Triage each run, and confirm each finding with evidence before you report it, following the triage module and, to check the system's state at the failing moment, `references/debug/MODULE.md`. Keep each confirmed bug from hiding others, for example by having the driver avoid its trigger, while keeping its assertion. Widen what the workload exercises, and launch again. When you stop, report the same things, and each bug you confirmed.

Each pattern you adopt adds to steps 4 to 9. Its page says what.
