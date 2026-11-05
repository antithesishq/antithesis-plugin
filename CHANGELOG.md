<!-- Each version is a top-level `# Version` section, newest first, below these comments. -->
<!-- markdownlint-disable-file MD025 -->

# Version 0.0.9-rc.1 (2026-11-05)

No changes to the plugin since 0.0.8. This candidate tests the new release process, which releases from a pushed tag.

# Version 0.0.8 (2026-11-04)

The first tagged release of the Antithesis plugin. It gives a coding agent one skill, `antithesis`, as the entry point to any task that involves Antithesis. The skill picks one of its modules from the request:

- `workload`: build or extend a workload for the system under test. A driver generates requests with [Hegel](https://www.hegel.dev) and starts the workload, the harness runs it under Docker Compose, and the agent iterates locally before it spends compute.
- `properties`: import the system's guarantees, or define new ones, and express them as Antithesis assertions.
- `launch`: launch a run of a workload with `snouty launch`, with fault flags.
- `triage`: monitor a run in progress, summarize a finished one, and root-cause its failures.
- `debug`: run commands inside Antithesis at a moment of a run, to debug a failure or a property.
- `patterns`: optional pieces that only some workloads need, such as client containers for stateful client libraries, and log forwarding.

The skill needs snouty 0.9.0 or later, Docker or Podman with Docker Compose, and jq. The plugin installs on Claude Code, Codex and Cursor from this repository's marketplace, and has setup notes for Devin and Replit.
