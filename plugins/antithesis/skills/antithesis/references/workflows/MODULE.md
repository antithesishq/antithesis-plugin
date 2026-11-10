# Workflows

A workflow chains other modules to reach a common goal. It adds no steps of its own: follow each module it names, read only when you reach it, as that module says. If the user gave a compute budget, it covers the whole workflow, across every module.

| Workflow | Use when                                                                       |
| -------- | ------------------------------------------------------------------------------ |
| `setup`  | The system has no workload yet, and the user wants one.                        |
| `heal`   | The system changed since its workload was last updated, and the workload lags. |
| `test`   | The user wants the system tested, and found bugs triaged.                      |

If the request fits none, pick the module from `SKILL.md` instead.

## Setup

Build a workload for the system end to end: follow every step of `references/workload/MODULE.md`. If the user named guarantees or a source of them, add them with `references/properties/MODULE.md` before the run loop (step 10).

## Heal

Input: an existing workload, and the system it tests.

1. **Find what changed.** List the system's changes since the workload last changed, from the version control history of both, and the release notes for a release. Note new or changed APIs, configuration, behaviors and guarantees, and removed ones.
2. **Update the workload** to cover them. Follow `references/workload/MODULE.md` from step 1, but change only what the changes touch: the surface map, the model, instrumentation, exploration assertions, the driver and the harness. Update the properties that the changed guarantees affect with `references/properties/MODULE.md`.
3. **Validate and report** with steps 8 to 11 of the workload module.

## Test

Input: a system, and optionally a workload, a version to test and the behaviors to focus on.

1. **Get a workload.** If the system has none, run "Setup". If a version to test is given and the workload lags it, run "Heal".
2. **Launch** a run of the workload with `references/launch/MODULE.md`.
3. **Triage it live** with `references/triage/MODULE.md`, in `monitor` mode. Don't wait for the run to finish.
4. **Root-cause each failure** that the triage judges likely to be a real bug of the system, in `root-cause` mode.
5. **Summarize** with the triage module's `summary` mode once the run ends: what passed, what failed, the root causes, and what's new.

Launch more runs only within the budget, and only when they can answer something the last run couldn't.
