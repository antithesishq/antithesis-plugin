# Report a bug

Input: a candidate SUT bug, as a failing property or anomaly in a run, from the triage or workload module or the user. Output: a confirmed report, or the evidence that the candidate isn't a SUT bug, and how to keep the bug from hiding others.

## Characterize the failure

1. Find every failing example of the property across timelines with `snouty runs search`, and the passing ones near them. Note what the failing ones share and the passing ones lack: an operation, an active fault, a configuration, a vtime.
2. Pick one representative failing moment. Rebuild its history from the log (`references/triage/logs.md`): each operation and fault from the timeline's start that touched the state the property checks, with timestamps.
3. Cross-reference that history with the SUT's and workload's source, as in "Investigate a failing property" in `references/triage/MODULE.md`. If the property itself, or the workload's model of the system, is wrong, it's a workload bug: stop and return that, with the evidence.

## Confirm it in Antithesis

Don't trust the workload's verdict. Run commands at the failing moment to read the SUT's state directly, with its own tools or API, such as reading back the record the workload says was lost. Pick the run with `references/debug/MODULE.md`, and cancel each debugging session you started as "When you're done" in `references/debug/MODULE.md` says.

## Reproduce it outside Antithesis

Where feasible, write a small program that triggers the bug deterministically without Antithesis. Inject the timing or fault the history shows, such as a pause between two calls, instead of hoping for it. Run it against the release under test. Ask the user whether to also run it against the latest upstream version, and record which versions reproduce. Keep it out of the user's repository unless they ask.

If a reproducer isn't feasible, say why in the report.

## Draft the report

Use the destination and format the user gave. Look in the SUT's repository for its own bug report guidance, such as an issue template or `CONTRIBUTING.md`, and follow it. Otherwise use `references/bug-report/template.md`.

Label each claim **confirmed** (shown by command output, a reproducer or the log), **inferred** (follows from the source or the docs, but not shown), or **open** (unknown).

## Get an independent check

Before the user sees the draft, have a fresh subagent review it. Give it the draft, the SUT's source, and the evidence files, but not your reasoning. Tell it to check every claim against the source, docs and evidence, and to list each claim that doesn't hold or is labeled stronger than its evidence supports. If you are a subagent and can't start one, return the draft and ask your caller to run the review.

Fix or relabel each claim it lists. If a fix changes the conclusion, review again.

## Report and return

Check for an existing report first, as "Duplicates" in `references/bug-report/template.md` says. Then file or print the report.

Tell the caller how to keep this bug from hiding others in later runs, such as a workload change that avoids its trigger. Keep the failing assertion, and mark the change with a link to the report so it can be removed once the bug is fixed.
