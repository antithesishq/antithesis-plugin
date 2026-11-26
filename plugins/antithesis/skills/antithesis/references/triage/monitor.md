# Monitor a running run

Follow the run with `snouty runs stream` in the background, as "Read the properties" in `references/triage/MODULE.md` describes, so you can triage while it runs. Send its output to a file, and don't wake on each line: every check after a long wait re-writes your context's cache, which costs more than the check itself. Check in batches instead:

- **Pick the interval:** 2½ minutes per hour of the run's `--max-compute-hours`, between 15 and 60 minutes, such as 30 minutes for a 12-hour run. Use the user's interval if they give one.
- **Wait in the background** with `snouty runs wait <run_id> --timeout <interval>`, which also returns as soon as the run is complete. Don't poll or read the stream's file before it returns.
- **Check:** read the stream's new lines. If the stream exited with an error, start it again and read `snouty runs properties <run_id>`.
  - Tell the user about each property that failed.
  - Triage each failing property in its own subagent, following "Investigate a failing property" in `references/triage/MODULE.md`.
  - Report each failure as its triage finishes. See "Report" in `references/triage/MODULE.md`.
- Repeat from "Wait in the background" until the stream prints `completed`, then continue with `references/triage/summary.md`.
