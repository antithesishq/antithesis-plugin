# Task prompts and budget

Each prompt reads like a message from a user who knows the project but not the plugin. Fill the bracketed parts from the target's profile in `references/targets/`, the budget split below, and the eval so far, and keep the rest of the wording as it is, so evals stay comparable.

## Budget split

For a 300 compute-hour eval of one target on the standard tier:

| Task | Compute hours | Notes |
| --- | --- | --- |
| Workload | 80 | Eval 2's workload billed 96 against a 100 budget. |
| Triage root-cause, each round | 10 | Often uses one short run, or nothing. Eval 2's used 6.1. |
| Debug | 10 | With one session at a time there's no other ready run to borrow, so the session starts its own debugging session. That bills about 48 compute hours per hour of wall time, so 10 buys about 12 minutes. Eval 3's billed 14.5 for 18 minutes. |
| Monitor run | 24 | You launch it for the monitor task; plain-language triage uses it too. |
| Properties | 30 | |
| Patterns | 125 | The long run alone needs about 100: 2 hours of fuzzing on 48 cores is 96, plus setup. |

These caps add up to 289, counting root-cause twice, which leaves 11 for billing over each cap (see **Budget** in `SKILL.md`), so ask each session to count that overrun against its budget. Summary, monitor and the plain-language triage launch nothing themselves. Scale the split to the user's budget and the target's setup time.

## Templates

### workload

Run in a fresh clone of the target's latest release, and record the commit in `notes/`.

```text
/antithesis workload

I want to start testing [project] (this repo) with Antithesis. Please build a workload for it end to end, and get it to the point where it's validated on Antithesis and we've had a couple of smoke runs that look healthy. I mostly care about [focus].

You have a total budget of [workload budget] compute hours on Antithesis for this. That covers both validating the workload and the smoke runs. Keep track of what you spend and don't go over it.

I'm going to step away for a while, so work autonomously and make reasonable calls instead of waiting on me. If something truly blocks you, tell me what you need. When you're done, give me a summary of what you built, the runs you launched (run IDs and compute hours each), and what they showed.
```

### triage-summary

Run the first round of triage in the workload's checkout, on runs the workload session launched, and the second round in the patterns clone, on its long run.

```text
/antithesis triage summary [run id]
```

### triage-rootcause

```text
/antithesis triage root-cause [run id] "[property]"

If you need follow-up runs, keep them to [root-cause budget] compute hours total.
```

### triage-monitor

```text
/antithesis triage monitor [run id]
```

### triage-nl

Send while the monitor run is still going, with no mode, to test how the skill picks one.

```text
how's the latest antithesis run looking? anything failing yet? we're out of compute budget, so don't launch anything new.
```

### debug

Pick a failing property that triage explained with a theory but no proof. State the theory, and ask for evidence from the live system.

```text
/antithesis debug

In run [run id], "[property]" failed [N] times. Our theory: [the mechanism, in a user's words.] I want proof from the live system, not just log lines: [the state that would confirm it, such as goroutines, internal state, or on-disk data at a failing moment], and anything else that confirms or kills the theory.

Keep it under [debug budget] compute hours.
```

### properties

Run in the workload's checkout, after the workload task. Prefer a property to define that triage suggests can fail.

```text
/antithesis properties

We now have an Antithesis workload for [project] in antithesis/ (branch [branch]). I'd like more of [project]'s guarantees covered. Two things:

1. Import properties from the Antithesis [catalog]: whatever applies to [project] and isn't already covered by the workload.
2. Define this one: "[property to define]" [why]

You can use up to [properties budget] compute hours on Antithesis to check them.
```

### patterns

Run in a new clone of the target's upstream with the workload branch fetched in, so the clone's path has no memory from earlier sessions. Name the gaps, but not the patterns, so the agent has to find them in the skill.

```text
/antithesis workload

We already have an Antithesis workload for [project] in antithesis/ (branch [branch]). I want to improve it rather than start over. Two gaps I see:

- [client library]
- We can't check things that span nodes, like [cross-node checks].

Look at the patterns the antithesis skill offers, adopt the ones that actually fit [project], and iterate on the workload with short runs until it's healthy. Then do one longer run, at least 2 hours of fuzzing, to make sure it holds up over a longer rollout, and triage what it finds.

You have up to [patterns budget] compute hours on Antithesis for all of this, including the long run. Work autonomously. When you're done, tell me what you changed and why, which patterns you adopted or rejected, the runs you launched with their compute hours, and what the long run showed.
```
