# Monitor a running run

Follow the run with `snouty runs stream` in the background, as "Read the properties" in `references/triage/MODULE.md` describes, so you can triage while it runs. Send its output to a file, and don't wake on each line: every check after a long wait re-writes your context's cache, which costs more than the check itself. Check in batches instead:

- **Pick the interval:** a quarter of the run's expected wall-clock time, between 15 and 60 minutes. Estimate that time per compute hour from the `Elapsed` of your earlier runs in `snouty runs show`, or else as 1½ minutes per hour of `--max-compute-hours`. Use the user's interval if they give one.
- **Wait in the background** with `snouty runs wait <run_id> --timeout <interval>`, which also returns as soon as the run is complete. Don't poll or read the stream's file before it returns.
- **Check:** read the stream's new lines. If the stream exited with an error, start it again and read `snouty runs properties <run_id>`.
  - Tell the user about each property that failed since the last check.
  - Triage each of them in its own subagent, following "Investigate a failing property" in `references/triage/MODULE.md`.
  - Report each failure as its triage finishes. See "Report" in `references/triage/MODULE.md`.
- Repeat from "Wait in the background" until the wait prints a final status: `completed`, `cancelled` or `incomplete`. Then continue with `references/triage/summary.md`, and for an `incomplete` run also follow "Diagnose an incomplete run" in `references/triage/MODULE.md`.
