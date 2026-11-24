# Summarize a finished run

- Triage each failing property in its own subagent, following "Investigate a failing property" in `references/triage/MODULE.md`.
- Check which failures are already known, with the search in "Duplicates" in `references/triage/issues.md`. If you don't know where issues are reported, say that this wasn't checked.
- Summarize the run for the user:
  - each failing property, its likely cause, and whether it's new or already known
  - the instrumentation status
  - anything else that needs a closer look, such as an unusual pass/fail ratio
- Suggest which failures to look at next in `root-cause` mode.

If you were told where to report issues, file the new ones as "Report" in `references/triage/MODULE.md` describes.
