# Root-cause one failure

Input: a failing property or anomaly in the run, named in the request. If none is named, pick the failing property most likely to be a real bug, using the pass/fail ratios in `references/triage/properties.md`.

1. Investigate it, following "Investigate a failing property" in `references/triage/MODULE.md`. For an anomaly that isn't a property, find its moments with `snouty runs search` first.
2. Run commands at the failing moment and around it. See `references/debug/MODULE.md`.
3. If this run can't answer it, launch a targeted run that can, for example with more logging around the suspect code, even prints in hot loops, which `snouty launch --filter-logs-matching` drops from the run until `snouty runs exec --events --include-filtered-logs` recovers them, or a workload that drives the failing path harder. Launch it with `references/launch/MODULE.md`, with the original run's launcher and flags, from the command that launched it or the workload's harness (`snouty runs show` doesn't list every parameter). Then investigate the same property in that run.
4. Stop once evidence from a run shows the cause, not only the code.

Report the cause as "Report" in `references/triage/MODULE.md` describes.
