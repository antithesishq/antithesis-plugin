# Build a workload

Input: a system to test in Antithesis, and optionally the behaviors to focus on.

## What a workload is

- **The driver.** One Rust binary written with [hegel](https://hegel.dev), using `#[hegel::main]`. It picks actions at random, has them sent to the system, and records each outcome in a model of what the system should contain. Every random choice comes from hegel, so Antithesis controls it.
- **Client programs,** each in a client container faulted like the servers, that run the system's real client library and execute what the driver sends. `references/workload/clients.md` says when to skip them.
- **Log forwarding:** the system's logs go to the driver, which parses them into each node's state.

The driver binary is the main process of its own fault-excluded container. It waits for the system, reports setup complete, then waits for `/workload-active`, which the container's one `first_` test command creates when fuzzing starts. Every decision is made in the driver.

The SUT itself is built with Antithesis coverage instrumentation.

## Steps

1. **Map what the workload must reach.** Follow `references/workload/surface.md`.
2. **Pick the model.** For every in-scope item, decide what the driver must record so an assertion can judge each response.
3. **Write the client program.** Follow `references/workload/clients.md`.
4. **Instrument the SUT,** including the client library. Follow `references/workload/instrumentation.md`. Add exploration assertions to its code, following "Exploration assertions" in `references/properties/assertions.md`.
5. **Write the driver,** including its startup: the waits for the system, admin setup, setup complete and the `/workload-active` wait. Follow `references/workload/driver.md`.
6. **Wire up the harness:** the `driver` container with its `first_` test command, the client containers, any shared volumes, and the fault flags. Follow `references/workload/harness.md`.
7. **Build and validate.** Build the images, run the instrumentation checks, then run `snouty validate <config_dir>`. Commit every file the images build from, and check `git status --ignored`, since ignore rules can drop harness files.
8. **Iterate locally** on coverage and the exploration assertions (`references/properties/assertions.md`). Follow `references/workload/local-loop.md`.
9. **Forward the system's logs.** Follow `references/workload/system-logs.md`, then iterate locally again.
10. **Iterate on short Antithesis runs.** Follow `references/workload/run-loop.md`.
11. **Launch the final run** with `--max-compute-hours 24` on the standard tier. Follow `references/launch/MODULE.md` with the launcher and fault flags in `references/workload/harness.md`, and read the run with the triage module.
12. **Report to the user.**
