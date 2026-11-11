# Workflows

A workflow is a sequence of steps, each done with one module, that reaches the user's goal. Derive it from what the user's prompt asks for:

1. **Find the goal.** Read the prompt for what the user wants at the end, such as a workload, a tested release, or the root cause of a failure, and for what they already have, such as a workload, a run or a known failure. Look in the project for anything the prompt leaves out, such as whether a workload exists.
2. **Plan the steps.** List the steps that get from what exists to the goal, and the module for each. Include every step the prompt asks for, in its order, and only the steps the goal needs. Leave out what already exists, and add what the goal depends on, such as a workload before a launch. The examples below show common shapes. Use them as a starting point, not a menu.
3. **Ask if unclear.** If you can't tell what the goal is, ask the user before you read any module.
4. **Tell the user the plan.** Before you start, tell the user the workflow you're about to run, step by step, so they know what to expect and how to prompt for a different one next time.
5. **Follow the plan.** Read each module only when you reach its step. Revise the plan when a step's results call for it, such as a run that shows the workload needs work.
6. **Report the workflow you ran,** with the results, including any step you added, skipped or changed, and why.

Keep what the prompt adds, such as the behaviors to focus on, where to report, or a compute budget. A budget covers the whole workflow, across every module. If the prompt gives none, use 60 compute hours for the whole workflow.

## Examples

### Set up a system

For a system with no workload.

1. Build a workload, with `references/workload/MODULE.md`.
2. Import the system's 10 most important current guarantees, with `references/properties/MODULE.md`.

### Heal a workload

For a workload that lags changes to its system.

1. Find what changed in the system since the workload last changed, from the version control history of both and any release notes: new, changed and removed APIs, configuration, behaviors and guarantees.
2. Update the workload to cover the changes, with `references/workload/MODULE.md`.
3. Re-import changed guarantees, with `references/properties/MODULE.md`.

### Test a system

1. Set up or heal its workload first, as in "Set up a system" or "Heal a workload".
2. Launch a run, with `references/launch/MODULE.md`.
3. Triage it live, with `references/triage/MODULE.md` in `monitor` mode, to verify which findings are real.
4. Root-cause the likely bugs, in the triage module's `root-cause` mode.
5. Report the findings, with the triage module's `summary` mode once the run ends.
