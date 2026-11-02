# Antithesis explainer

Antithesis is a simulation platform which applies advanced testing techniques to find bugs in arbitrary software. It runs software in a deterministic simulation environment and automatically searches for property violations via systematic exploration of the software's state space. Antithesis should be used to pressure test implementations by finding the kinds of bugs that are frequently missed using traditional testing methods.

## Definitions

- **Launcher**: An Antithesis workflow such as testing or debug.
- **Run**: A running instance of a Launcher, identified by a run ID (for example: `1d0b6331ec02e8268fee157346701f01-64-0`).
- **Moment**: A uniquely identified instant in a run. Identified by an (`input_hash`, `vtime`) tuple, where `input_hash` identifies the branch, and `vtime` identifies the virtual time.
- **Timeline**: The sequence of moments of one continuous simulated execution, in `vtime` order.
- **Branch**: A new Timeline branched from another timeline at a **Moment**.
- **Multiverse**: A tree of Timelines branched from each other.
- **Event**: A record logged at a moment. An event can be output from the system under test (stdout or stderr), the Antithesis SDK, or an Antithesis built-in event such as faults.
- **System under test (SUT)**: The system that is being tested by Antithesis.
- **Property**: An invariant of the SUT, expressed via the Antithesis SDK or via property definition files.
- **Workload**: Code designed to exercise the SUT, allowing Antithesis to explore the full state space of the SUT and find property violations.
- **Config image**: A Docker image which contains orchestration code (docker compose config or k8s manifests) to run the SUT and Workload in Antithesis.

## Test runs

An Antithesis test run is kicked off via certain launchers like the `basic_test` launcher, which is built into every tenant. The launcher deploys the Config image to the Antithesis fuzzer which sets up the SUT and Workload and starts autonomously searching for property counter examples. This process generates a multiverse.

## Debugger runs

A debugger run takes a source run & moment as input, and rewarms it into a deterministic virtual machine. Like any run, debugger sessions may rewarm many moments from one or more source runs. Debugger sessions live for six hours unless cancelled.

## Run readiness

All Antithesis runs can be used by real-time commands like `snouty runs exec`, `snouty runs search`, and `snouty runs logs` while they are running, as long as they are ready. To check if a run is ready either run `snouty runs wait --until ready <run_id>` or check that the status is `in_progress:ready` in `snouty runs show <run_id>`.

## snouty

Snouty is the official Antithesis CLI.

### Commands

When using `snouty` follow these rules:

1. Discovery commands dynamically via `snouty --help`
2. Read the subcommand's documentation via `snouty <cmd...> --help` before use
3. Pass `--detail` to every command that takes it. Pass `--json` instead only when you pipe the output into `jq` or another program. JSON costs several times as many tokens and carries mostly fields you don't need, while `--detail` keeps what the default output leaves out, such as assertion details
