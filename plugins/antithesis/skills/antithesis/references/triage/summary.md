# Summarize a finished run

1. Triage each failing property in its own subagent, following "Investigate a failing property" in `references/triage/MODULE.md`.
2. Check which failures are already known, with the search in "Duplicates" in `references/bug-report/template.md`. If you don't know where issues are reported, say that this wasn't checked.
3. Summarize the run for the user:
   - each failing property, its likely cause, and whether it's new or already known
   - the instrumentation status
   - anything else that needs a closer look, such as an unusual pass/fail ratio
4. Suggest which failures to look at next in `root-cause` mode.

Unless your caller writes up bugs itself, hand each new likely SUT bug to `references/bug-report/MODULE.md`. Skip a bug already written up in this session.
