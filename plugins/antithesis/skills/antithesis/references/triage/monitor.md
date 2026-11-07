# Monitor a running run

Follow the run with `snouty runs stream` in the background, as "Read the properties" describes, so you can triage while it runs.

1. Tell the user about each property as it fails.
2. Triage each failing property in its own subagent, following "Investigate a failing property". While the run is live, you may run commands at the failing moment in it right away: see `references/debug/MODULE.md`.
3. Report each failure as its triage finishes. See "Report".

When the stream prints `completed`, continue with `references/triage/summary.md`.
