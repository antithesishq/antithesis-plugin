# Monitor a running run

Follow the run with `snouty runs stream` in the background, as "Read the properties" in `references/triage/MODULE.md` describes, so you can triage while it runs.

1. Tell the user about each property as it fails.
2. Triage each failing property in its own subagent, following "Investigate a failing property" in `references/triage/MODULE.md`.
3. Report each failure as its triage finishes. See "Report" in `references/triage/MODULE.md`.

When the stream prints `completed`, continue with `references/triage/summary.md`.
