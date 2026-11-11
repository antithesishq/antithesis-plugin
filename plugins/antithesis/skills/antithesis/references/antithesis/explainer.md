# Antithesis explainer

Antithesis is a simulation platform for finding bugs that traditional testing misses. It runs software in a deterministic simulation and systematically explores its state space for property violations.

## Definitions

- **Tenant**: An organization's Antithesis instance, at `<tenant>.antithesis.com`.
- **Launcher**: The kind of Antithesis run to start, such as a test (`basic_test`) or a debugging session.
- **Run**: A running instance of a launcher, identified by a run ID (for example: `1d0b6331ec02e8268fee157346701f01-64-0`).
- **Compute hour**: The unit Antithesis bills by: one core running for one hour. A run's compute budget and performance tier set how long it fuzzes.
- **System under test (SUT)**: The system that is being tested by Antithesis.
- **Fault**: A disruption Antithesis injects, such as a network partition, a killed or paused container, or a thread pause.
- **Timeline**: One continuous simulated execution of the system.
- **Virtual time (`vtime`)**: The simulated clock of a timeline.
- **Moment**: An instant on a timeline, identified by an (`input_hash`, `vtime`) pair. `input_hash` is a hash of every input Antithesis sent up to that point.
- **Branch**: A timeline that splits off another timeline at a moment.
- **Multiverse**: A tree of timelines branched from each other.
- **Event**: A record logged at a moment: SUT output, an SDK call, or an Antithesis event such as a fault.
- **Driver**: The program that picks actions, sends them to the SUT, and checks the responses. One binary, the main process of its own container.
- **Workload**: Everything added to the deployment to exercise the SUT. In this skill: the driver, and the patterns a system needs, such as client programs that run the SUT's client library.
- **Property**: What Antithesis reports for a run: a check evaluated over the whole multiverse, passing or failing with examples (where it held) and counterexamples (where it didn't). `snouty runs properties` lists them. Assertions are the only way to define properties: each assertion, identified by its message, becomes one property. Antithesis also has default properties about the run itself, such as `Software was instrumented`.
- **Assertion**: An Antithesis SDK call, placed in the workload or the SUT. Each call is an event that Antithesis picks up. The default properties named after each assertion type (`Always`, `Sometimes`, `Reachable`, ...) judge each assertion's events on their own, and report the result as that assertion's property: for example, `Always` passes for an assertion that is hit at least once and true on every hit. A failing SDK assertion doesn't stop the program.
- **Guarantee**: Something the SUT promises, such as "acknowledged writes are never lost". The properties module implements guarantees using one or more assertions, so it shows up in a run as one or more properties.
- **Test command**: An executable that Antithesis runs in a container, found under `/opt/antithesis/test/v1/<test>/`. Its name prefix sets when it runs; a `first_` command runs once at the start of every timeline.
- **Setup**: The start of a run, when the SUT and workload are deployed and made ready. It ends when the workload reports **setup complete**; Antithesis then snapshots the system, and every timeline starts from that snapshot.
- **Config image**: A Docker image with the Docker Compose file or Kubernetes manifests that run the SUT and workload.

## Test runs

A launcher starts a test run. It deploys the Config image to the Antithesis fuzzer, which sets up the SUT and Workload and searches for property counterexamples, generating a multiverse.

Every tenant has two default launchers: `basic_test` and `basic_k8s_test`. Tenants may have additional launchers.

## Debugging sessions

A debugging session is a run that takes a source run and moment as input and rewarms it into a deterministic virtual machine. Like any run, it can rewarm more moments from one or more source runs.

## Run readiness

snouty's run commands work on any ready run: status `in_progress:ready` in `snouty runs show`, or wait with `snouty runs wait --until ready`. All except `snouty runs exec` also work on completed runs. To exec at a moment when no run is ready, start a debugging session with `snouty debug`.

## snouty

Snouty is the official Antithesis CLI. When using it:

1. Discover commands via `snouty --help`.
2. Read a subcommand's `snouty <cmd...> --help` before using it. When you hand work to a subagent, tell it to read the `--help` of the snouty commands it will use.
3. Pass `--detail` where the command's `--help` lists it. Pass `--json` instead only when you pipe the output into `jq` or another program. JSON costs several times as many tokens and carries mostly fields you don't need, while `--detail` keeps what the default output leaves out, such as assertion details.

Read Antithesis documentation with `snouty docs search <terms>`, then `snouty docs show <path>`.
