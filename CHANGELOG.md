<!-- Each version is a top-level `# Version` section, newest first, below these comments. -->
<!-- markdownlint-disable-file MD025 -->

# Version 0.0.9 (2026-11-05)

- `workload`: the driver ends a timeline with an eventually instead of pausing faults in quiet periods. An eventually is a normal rule that, behind a rare draw, stops faults for good, waits for the system to recover, asserts what must hold once faults stop, and exits the driver to end the timeline. The driver page also explains hegel's swarm testing, which leaves a random subset of rules out of each timeline, and tells the agent to pace disruptive actions with a cooldown rather than a weight. The harness gives the driver no restart policy, and the local loop checks the eventually on its own ([#30](https://github.com/antithesishq/antithesis-plugin/pull/30))
- `launch`: always sets `SNOUTY_UNSTABLE_FEATURES=teams`, so `snouty launch --help` shows the flags the skill relies on, and always passes `--max-compute-hours`. When the user gives a compute budget, the agent adds up the hours of its finished and running runs before each launch, and stops rather than exceed it. Every run records the plugin version that launched it as `attrs.plugin_version` ([#28](https://github.com/antithesishq/antithesis-plugin/pull/28), [#33](https://github.com/antithesishq/antithesis-plugin/pull/33), [#35](https://github.com/antithesishq/antithesis-plugin/pull/35), [#36](https://github.com/antithesishq/antithesis-plugin/pull/36))
- Before a long unattended task, such as building a workload, the agent asks the user up front for everything it can foresee needing, such as a compute budget and permission to change their code, then works to the end. A property that fails without a clear cause keeps its assertion and is reported to the user as a possible bug ([#32](https://github.com/antithesishq/antithesis-plugin/pull/32))
- `workload`: the run loop classifies every failing property as a SUT bug, a workload bug or expected before changing anything, never relaunches an unchanged workload, and cancels a run still going before launching the next. The final report lists any step the agent skipped or changed ([#29](https://github.com/antithesishq/antithesis-plugin/pull/29))
- `debug`: the agent cancels each debug run it started as soon as it's done with it ([#29](https://github.com/antithesishq/antithesis-plugin/pull/29))
- A new reference page, `references/antithesis/faults.md`, describes what each fault does, how it ends, and how it interacts with a pause. The harness and log pages link to it ([#31](https://github.com/antithesishq/antithesis-plugin/pull/31))
- `triage`: the main agent reads each triage page only when it reaches the step that needs it, and leaves the log guide to the subagents that download logs ([#34](https://github.com/antithesishq/antithesis-plugin/pull/34))

# Version 0.0.8 (2026-11-04)

The first tagged release of the Antithesis plugin. It gives a coding agent one skill, `antithesis`, as the entry point to any task that involves Antithesis. The skill picks one of its modules from the request:

- `workload`: build or extend a workload for the system under test. A driver generates requests with [Hegel](https://www.hegel.dev) and starts the workload, the harness runs it under Docker Compose, and the agent iterates locally before it spends compute.
- `properties`: import the system's guarantees, or define new ones, and express them as Antithesis assertions.
- `launch`: launch a run of a workload with `snouty launch`, with fault flags.
- `triage`: monitor a run in progress, summarize a finished one, and root-cause its failures.
- `debug`: run commands inside Antithesis at a moment of a run, to debug a failure or a property.
- `patterns`: optional pieces that only some workloads need, such as client containers for stateful client libraries, and log forwarding.

The skill needs snouty 0.9.0 or later, Docker or Podman with Docker Compose, and jq. The plugin installs on Claude Code, Codex and Cursor from this repository's marketplace, and has setup notes for Devin and Replit.
