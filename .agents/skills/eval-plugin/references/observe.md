# What to look for

Read the transcripts, not only the final answers. For each finding, note the time, the session, and the evidence: a tool call, a tool result, a run ID.

## For every session

- **Loading:** which skill pages it read, and when. Did it read pages up front that its task didn't need, or skip a page its task depended on?
- **Following the docs:** for each step of the module it used, did it do what the step says? Where it deviated, was the deviation better or worse, and was it silent?
- **Where the docs ran out:** what it had to find elsewhere, such as SDK source from crates.io or proxy.golang.org, `snouty docs`, `--help`, or other sessions' transcripts. Each one is a candidate gap in the plugin.
- **snouty:** commands that failed, flags it guessed, errors it misread, and features it didn't know about.
- **Budget:** the caps it launched with, what it reported spending, and what `snouty runs usage` says it spent.
- **Claims:** check each claim in the final answer against the runs and the transcript, such as a property it says passed, or a cause it says it confirmed.
- **Cost hygiene:** did it cancel debug runs and follow-up runs once it had what it needed?
- **Isolation:** did it cancel other sessions' runs, or change their images or checkouts, and did it say so? Running commands in another session's ready run is fine.

## Per task

- **Workload:** time to the first validated launch; how far it used the local loop and what the loop found; whether it committed before each launch, so each run's recorded commit matches the code; whether it confirmed the workload was healthy (instrumentation, reachability, the eventually and quiet-period checks) or only reported failures; its own triage of its runs.
- **Triage:** whether it picked the right mode; subagent use; whether it checked for known issues upstream; how it separated SUT bugs from workload bugs; the quality of its evidence (inferred, logs, a reproducer, a debugging session).
- **Debug:** which run it executed commands in (a new `snouty debug` run, or a ready run it borrowed, and whose); rewarm time; whether the evidence proves or kills the theory; whether it cancelled what it started.
- **Properties:** whether it showed the user what it would import or just picked; whether it confirmed that the system actually promises each property; whether it broke each check on purpose to see it fail; whether the new property failed where it should.
- **Patterns:** which patterns it adopted or rejected, and why; whether it changed the existing workload or rebuilt it; the long run's health (faults throughout, not starved by quiet periods), and its triage.

## Known failure modes

Earlier evals found these. Check whether each still happens.

- Agents read about 15 reference pages before touching the repository.
- The hegel and SDK pages aren't enough to write a driver, so agents read crate source.
- Billing exceeds `--max-compute-hours` by about 2.5 per run. Agents count the cap as the spend.
- `snouty runs usage` lags run end by an hour or more, and shows 10 rows by default. On a busy tenant, agents miss their runs and report "never listed".
- `--max-compute-hours` is hidden unless `SNOUTY_UNSTABLE_FEATURES=teams` is set.
- Agents judge a run from its property table while the run is still going, and miss later failures.
- Summary mode skips the duplicates check with "I don't know where issues are reported", even when the git remote names the upstream repository.
- Workload agents triage their own runs in parallel with the triage sessions, and reach different conclusions.
- Quiet periods start from a per-round draw that grows more frequent as faults stop, so a timeline can end up with no faults. Since 0.0.9 an eventually ends the timeline instead. An eventually that fires early is fine: Antithesis branches past it.
- About half of token spend re-writes the cache after waits longer than 5 minutes.
- `snouty runs show --detail` doesn't exist, and agents keep trying it.
- A properties agent launched runs from uncommitted changes, so the run's recorded commit didn't match the code.
- Two sessions on one machine that build the same image tags launch each other's images. Workload docs don't suggest tagging images per checkout.
- In `claude -p`, a session's turn ends while it waits on background work, and it resumes on the notification. One session can log many `result` lines.
