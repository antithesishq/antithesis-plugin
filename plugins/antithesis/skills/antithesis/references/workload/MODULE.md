# Build a workload

Input: a system to test in Antithesis, and optionally the behaviors to focus on.

## Compute budget

Runs launched while working on the workload spend the task's compute budget, from the user or the default in `SKILL.md`.

## What a workload is

- **The driver.** One program written with [hegel](https://hegel.dev), run from hegel's main entry point for its language. It picks actions at random, sends them to the system, and records each outcome in a model of what the system should contain. Every random choice comes from hegel, so Antithesis controls it.
- **Exploration assertions,** in the driver and in the system's own code, which show Antithesis the states worth reaching. Put an assertion on a node's internal state in that node's code, where you can change it, so it fires at the moment the state occurs.
- **Patterns,** only for systems that need them: running the system's stateful client library in faulted client containers, or forwarding the system's logs to the driver. `references/patterns/MODULE.md` says when each applies.

The driver binary is the main process of its own fault-excluded container. It waits for the system, reports setup complete, then waits for `/workload-active`, which the container's one `first_` test command creates when fuzzing starts. Every decision is made in the driver.

The SUT and the driver are built with Antithesis coverage instrumentation.

## Steps

1. **Map what the workload must reach.** Follow `references/workload/surface.md`.
2. **Pick the patterns.** Read `references/patterns/MODULE.md`, and adopt only the patterns whose conditions hold for this system. By default, adopt none.
3. **Pick the driver's language.** Follow "Pick the driver's language" in `references/workload/languages.md`.
4. **Pick the model.** For every in-scope item, decide what the driver must record so an assertion can judge each response.
5. **Lay out the workload,** its README and its scripts. Follow `references/workload/layout.md`.
6. **Instrument the software.** Follow "Instrument the software" in `references/workload/languages.md`. Add exploration assertions to its code, following "Exploration assertions" in `references/properties/assertions.md`. They are the default way to see a node's internal state.
7. **Write the driver,** including its startup: the waits for the system, admin setup, setup complete and the `/workload-active` wait. Follow `references/workload/driver.md`.
8. **Wire up the harness:** the `driver` container with its `first_` test command, any shared volumes, the fault flags, and debug tools in every image. Follow `references/workload/harness.md`.
9. **Build and validate.** Build the images, run the instrumentation checks, then run `snouty validate <config_dir>`. Commit every file the images build from, and check `git status --ignored`, since ignore rules can drop harness files.
10. **Iterate locally** on coverage and the exploration assertions (`references/properties/assertions.md`). Follow `references/workload/local-loop.md`.
11. **Iterate on Antithesis runs** until a 24-hour run passes its checks. Follow `references/workload/run-loop.md`.
12. **Update the README and scripts, and report to the user,** including the driver's language, which patterns you adopted and why, and any step you skipped or changed, and why.
