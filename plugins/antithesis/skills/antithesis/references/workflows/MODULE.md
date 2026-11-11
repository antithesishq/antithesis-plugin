# Workflows

A workflow is a sequence of steps, each done with one module, that reaches the user's goal. Derive it from what the user's prompt asks for:

1. **Find the goal.** Read the prompt for what the user wants at the end, such as a workload, a tested release, or the root cause of a failure, and for what they already have, such as a workload, a run or a known failure. Look in the project for anything the prompt leaves out, such as whether a workload exists.
2. **Plan the steps.** List the steps that get from what exists to the goal, and the module for each. Include every step the prompt asks for, in its order, and only the steps the goal needs. Leave out what already exists, and add what the goal depends on, such as a workload before a launch. The examples below show common shapes. Use them as a starting point, not a menu.
3. **Ask if unclear.** If you can't tell what the goal is, ask the user before you read any module.
4. **Follow the plan.** Read each module only when you reach its step. Revise the plan when a step's results call for it, such as a run that shows the workload needs work.

Keep what the prompt adds, such as the behaviors to focus on, where to report, or a compute budget. A budget covers the whole workflow, across every module. If the prompt gives none, ask for one up front, as `SKILL.md` says, and until the user answers, use 60 compute hours for the whole workflow.

## Examples

### Set up a system

For a system with no workload.

1. Build a workload, up to the "Iterate on Antithesis runs" step in `references/workload/MODULE.md`.
2. Define the system's current guarantees, with `references/properties/MODULE.md`.
3. Finish the workload, from the "Iterate on Antithesis runs" step in `references/workload/MODULE.md` on.

### Heal a workload

For a workload that lags changes to its system.

1. Find what changed in the system since the workload last changed, from the version control history of both and any release notes: new, changed and removed APIs, configuration, behaviors and guarantees.
2. Update the workload to cover them, with `references/workload/MODULE.md`, changing only what the changes touch.
3. Update the properties of the changed guarantees, with `references/properties/MODULE.md`.
4. Validate the workload, with the workload module's steps from "Build and validate" in `references/workload/MODULE.md` on.

### Test a system

For a system to test, such as a new release, with its findings triaged.

1. Set up or heal its workload first, if it has none or it lags, as in "Set up a system" or "Heal a workload".
2. Launch a run, with `references/launch/MODULE.md`.
3. Triage it live, with `references/triage/MODULE.md` in `monitor` mode, to verify which findings are real.
4. Root-cause the likely bugs, in the triage module's `root-cause` mode.
5. Report the findings, with the triage module's `summary` mode once the run ends.
