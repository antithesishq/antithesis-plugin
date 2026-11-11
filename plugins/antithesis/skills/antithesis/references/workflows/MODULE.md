# Workflows

A workflow is a saved prompt that chains other modules toward a common goal. Pick the one that fits the user's prompt, fill its placeholders from the prompt and the project, and follow it as if the user had written it. Read each module only when you reach it.

| Workflow | Use when                                                                       |
| -------- | ------------------------------------------------------------------------------ |
| Setup    | The system has no workload yet, and the user wants one.                        |
| Heal     | The system changed since its workload was last updated, and the workload lags. |
| Test     | The user wants the system tested, and its findings triaged.                    |

If the prompt fits none, because it asks for one module's task, such as triaging a run, pick that module from the table in `SKILL.md` instead.

Keep what the user's prompt adds, such as the behaviors to focus on, where to report, or a compute budget. A budget covers the whole workflow, across every module. If the prompt gives none, ask for one up front, as `SKILL.md` says.

## Setup

> Write a new workload for `<system>` (`references/workload/MODULE.md`). Define its current guarantees as properties (`references/properties/MODULE.md`) before the run loop. Work autonomously within `<budget>` compute hours. Report the workload, its properties, and anything the runs found.

## Heal

> The workload for `<system>` lags `<version or recent changes>`. Find what changed since the workload last changed, from the version control history of both and any release notes: new, changed and removed APIs, configuration, behaviors and guarantees. Update the workload to cover them (`references/workload/MODULE.md`), changing only what the changes touch, and update the properties of the changed guarantees (`references/properties/MODULE.md`). Validate it with steps 8 to 11 of the workload module. Work autonomously within `<budget>` compute hours. Report what changed in the workload, and anything the runs found.

## Test

> Test `<system>` at `<version>`, and its current guarantees, including the features new in that version. If it has no workload, write one first, as in Setup. If its workload lags the version, heal it first. Launch a run (`references/launch/MODULE.md`), and as findings appear, triage them live to verify they are real, and root-cause the likely bugs (`references/triage/MODULE.md`). Work autonomously within `<budget>` compute hours. Report your findings here.
