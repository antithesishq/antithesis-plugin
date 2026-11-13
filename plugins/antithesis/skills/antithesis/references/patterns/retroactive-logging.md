# Retroactive logging

With retroactive logging, the system logs at a verbose level, such as trace, and Antithesis drops the lines that match a filter while it fuzzes, so they cost little. A command executed at a moment later gets them back. Read "Retroactive logging" in `snouty docs show /docs/product/launching_tests/` first.

## 1. Pick the lines to filter

Turn on the verbose level through the system's own configuration. Then write the filter, an RE2 pattern:

- `--filter-logs-matching` drops each line that matches, such as its trace and debug lines;
- `--filter-source-matching` drops all output of a source, usually a process name, such as a chatty sidecar.

Check the pattern against the system's real lines from the local loop (`references/workload/local-loop.md`). It must leave the lines that triage reads in `snouty runs logs`: the driver's output, and the system's normal-level lines, such as warnings and errors.

## 2. Launch with the filter

Pass the filter flag in the workload's launch script (`references/workload/layout.md`), on every launch. `snouty runs show --json` carries the run's launch parameters, so whoever debugs the run can see the filter there. Say in `antithesis/README.md` which lines the filter drops.

## 3. Recover the lines

Execute a command at a moment with `--events --include-filtered-logs` (`references/debug/MODULE.md`). The events include the filtered lines logged while the command runs:

```bash
snouty runs exec "$RUN_ID" "$INPUT_HASH" "$VTIME" --events --include-filtered-logs 'sleep 30'
```

The command runs on a new branch from that moment, so it shows what happens next, not what led up to the moment. To see the verbose lines before a failure, start a few seconds before it. Antithesis drops the lines outside the system's virtual machine, so recovering them doesn't change how the system runs, and a script that only sleeps usually repeats the failure: check its events for it. Turning on verbose logging or attaching a debugger at the moment changes the system's timing, and a race can stop happening.

## Checking it

- **Locally,** the pattern matches the verbose lines and no others.
- **In a short run,** the `Logging output was limited` property passes, and a `snouty runs exec` with `--include-filtered-logs` returns filtered lines.
