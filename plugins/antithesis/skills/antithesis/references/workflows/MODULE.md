# Workflows

A workflow is a sequence of steps, each done with one module, that reaches the user's goal. Derive it from what the user's prompt asks for:

- **Find the goal.** Read the prompt for what the user wants at the end, such as a workload, a tested release, or the root cause of a failure, and for what they already have, such as a workload, a run or a known failure. Look in the project for anything the prompt leaves out, such as whether a workload exists.
- **Plan the steps.** List the steps that get from what exists to the goal, and the module for each. Include every step the prompt asks for, in its order, and only the steps the goal needs. Leave out what already exists, and add what the goal depends on, such as a workload before a launch. The examples below show common shapes. Use them as a starting point, not a menu.
- **Ask if unclear.** If you can't tell what the goal is, ask the user before you read any module.
- **Read the plan's modules.** Before you start, read the `MODULE.md` of every module in the plan, and any other page you need to see what a step will ask of the user. Collect every question the steps will raise, such as which guarantees to import, so the user can answer them all at once.
- **Tell the user the plan, and ask.** In one message, tell the user the workflow you're about to run, step by step, so they know what to expect and how to prompt for a different one next time, and ask the questions you collected, as `SKILL.md` says.
- **Follow the plan.** Read each step's other pages when you reach it. Revise the plan when a step's results call for it, such as a run that shows the workload needs work.
- **Report the workflow you ran,** with the results, including any step you added, skipped or changed, and why.

Keep what the prompt adds, such as the behaviors to focus on, where to report, or a compute budget. A budget covers the whole workflow, across every module.

## Examples

### Set up a system

- Build a workload, with `references/workload/MODULE.md`.
- Import the system's 10 most important current guarantees, with `references/properties/MODULE.md`.

### Heal a workload

- Find what changed in the system since the workload last changed, from the version control history of both and any release notes: new, changed and removed APIs, configuration, behaviors and guarantees.
- Update the workload to cover the changes, with `references/workload/MODULE.md`.
- Re-import changed guarantees, with `references/properties/MODULE.md`.

### Test a system

- Set up or heal its workload first, as in "Set up a system" or "Heal a workload".
- Launch a run, with `references/launch/MODULE.md`.
- Triage it live, with `references/triage/MODULE.md` in `monitor` mode, to verify which findings are real.
- Root-cause the likely bugs, in the triage module's `root-cause` mode.
- Report the findings, with the triage module's `summary` mode once the run ends.
