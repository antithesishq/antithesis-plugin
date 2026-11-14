# Verify a fix

Input: a bug, and the commits or PR that fix it. The bug may come from an Antithesis run or from anywhere else, such as production, an issue or a user's report. Output: an evidence document that shows, with Antithesis, whether the fix resolves the bug.

A passing run proves nothing unless the same workload, on the unfixed version, fails, and on the fixed version reaches the bug's trigger.

1. **Pin down the failure.** From the bug's evidence, write down its trigger, such as an operation under a fault, and its symptom. For an Antithesis bug, rebuild them as "Characterize the failure" in `references/bug-report/MODULE.md` says.
2. **Make the workload see it.** Use the property that failed. Without one, add a guarantee assertion that fails on the symptom, with `references/properties/MODULE.md`. Make sure the workload drives the trigger, with `references/workload/MODULE.md`, and add an `assert_reachable` or `assert_sometimes` on the trigger ("Exploration assertions" in `references/properties/assertions.md`). Remove any workload change that avoids the trigger, such as one marked with a link to the bug's report.
3. **Fail before the fix.** Run the workload against the version just before the fix. If an earlier run of this workload and version already failed the property, reuse it. Otherwise launch one with `references/launch/MODULE.md`. If it doesn't fail, the workload doesn't catch the bug: improve it and run again, or report that the fix can't be verified this way.
4. **Pass after the fix.** Launch the same workload against the fixed version, with the same launcher, flags and at least the same compute. The fix is verified when the property passes and the trigger's exploration assertion passes. A failure of the same property is evidence the fix is incomplete: triage it with `references/triage/MODULE.md`.
5. **Check outside Antithesis.** If the bug has a reproducer, run it against both versions.
6. **Write the evidence document.** Use the format below, or the user's, and get it reviewed as "Get an independent check" in `references/bug-report/MODULE.md` says.

```markdown
# Fix verified: {title}

{verdict}: {bug_summary}, fixed by {fix_link}.

| | Version | Antithesis run | `{property}` | `{trigger}` | Reproducer |
| --- | --- | --- | --- | --- | --- |
| Before | {before_version} | [`{before_run_id}`]({before_run_link}) | {before_property} | {before_trigger} | {before_reproducer} |
| After | {after_version} | [`{after_run_id}`]({after_run_link}) | {after_property} | {after_trigger} | {after_reproducer} |

{evidence}
```

`{verdict}` is `Fixed`, `Not fixed` or `Inconclusive`. Each property and trigger cell gives the pass/fail counts from `snouty runs properties`, and each reproducer cell its result, or `—`. `{evidence}` labels each claim confirmed, inferred or open, as "Draft the report" in `references/bug-report/MODULE.md` describes, and says what the runs can't show, such as a trigger the workload reaches only rarely.
