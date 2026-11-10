# Triage an Antithesis run

Input: an optional mode, then an Antithesis run ID. If you were given something else, like a link to the run or "the latest run", read `references/triage/run-discovery.md` to find the run ID.

Work through the run without asking the user for input unless you are blocked.

Don't read the other pages in `references/triage/` up front. Read each one only when you reach the step that points to it. For example, you need `issues.md` only to report.

## Find the run

Get the run's status with `snouty runs show <run_id>`.

- If the run can't be found, wait 10 seconds and retry. A run can take a while to appear in the API after it starts.
- If the status is `starting`, wait for it with `snouty runs wait --until ready <run_id>`.
- If the status is `incomplete`, also follow "Diagnose an incomplete run" below.

## Pick a mode

| Mode         | Read                              | Use when                                                                             |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------------ |
| `monitor`    | `references/triage/monitor.md`    | The run is in progress. Report and triage failures as they arrive.                   |
| `summary`    | `references/triage/summary.md`    | The run has finished. Summarize its failures and what's new.                         |
| `root-cause` | `references/triage/root-cause.md` | One failing property or anomaly, in a running or finished run, needs its root cause. |

If no mode is given, use `monitor` for an `in_progress` run and `summary` for a finished one. Never wait for a run to finish before triaging it: results and failing moments are available while it runs, and a live run lets you run commands at a failing moment right away.

## Read the properties

List the failing ones, with their example counts and a sample of their moments, with `snouty runs properties <run_id> --failing --detail`. For an overview of every property, the table without `--detail` is enough. Read `references/triage/properties.md` for the assertion types and what pass/fail ratios suggest.

If the run is `in_progress`, don't wait for it to finish. Follow `snouty runs stream --help` to get the current results and new ones as they arrive.

If a `completed` or `cancelled` run has no properties, it has no results to triage. Report that and stop.

Also check the instrumentation properties, and include their status in your report. Read `references/triage/instrumentation.md` to find and interpret them.

## Investigate a failing property

Whoever downloads a log reads `references/triage/logs.md` first. In `monitor` and `summary` modes, the subagents download the logs for failing properties: tell each one to read it, and don't read it yourself unless you download a log too, as for an incomplete run. Then:

1. Pick the first failing example and find its moment. If the counterexample has no `moment` (properties that report a value, see `references/triage/properties.md`), the counterexample value is the evidence; skip to step 5.
2. Download the log for that moment and analyze it locally.
3. If a run is ready, run commands at the failing moment. See `references/debug/MODULE.md`.
4. If you aren't sure what caused the failure, find more moments for the same property with `snouty runs search -n 999` and compare them. Passing examples are useful for finding what differs between success and failure.
5. Cross-reference the log and command output against the source code of the system under test and the workload.
6. Work out the timeline of events that led up to the failure and its root cause.

The property status and assertion text alone are not enough. Download and read the logs before concluding on any failure that has moments. If its assertion has details, use them: its author chose those fields to show the system's state at the failure.

## Diagnose an incomplete run

An incomplete run can still have property results. Read them as for any run, and triage any failing properties as usual. Then:

1. If `snouty runs show <run_id>` gives a failure moment, download its log (`references/triage/logs.md`). Use its failure reason, if any, as a lead.
2. Look for errors in `snouty runs build-logs <run_id>`, especially if there is no failure moment.

## Report

Follow `references/triage/issues.md` to report what you found.

## Before you report

Check each report against these:

- Every property status you report came from the properties data or the stream, not inference.
- Conclusions about failures with moments rest on evidence from the run, with specific log lines, command output if a run was ready, timestamps and property names.
- The report separates what the run shows from what you interpret.
- A claim that a binary isn't instrumented follows `references/triage/instrumentation.md` and doesn't rest only on the deduplicated examples of `Software was instrumented`.
