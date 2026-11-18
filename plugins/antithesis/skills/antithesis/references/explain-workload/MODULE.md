# Explain a workload

Input: a workload built with `references/workload/MODULE.md`, in the state defined in "Launch a run" in `references/workload/run-loop.md`. Build it first if there is none.

This module explains to the user what their workload tests, in their system's language, so they can improve it. Explain the workload's actions and sequences, not how Antithesis or hegel work.

## Write the explainer

Read the driver, the workload's README and the last run. Write for a reader who knows the system and nothing about Antithesis. Use the system's own terms: for a bank, "we open accounts, then deposit, withdraw and transfer between them," not "the driver generates operations."

Open with: `Antithesis tests <system> by running this workload against it. Antithesis only tests what this workload does: any action or workflow it doesn't perform goes untested.` Then write these sections:

- **The system under test.** A symmetrically laid out diagram of how the nodes are related with arrows. Don't label the arrows. Show how the driver or equivalent fits into the SUT.
- **The workload.** A diagram of what the driver sends the system and what comes back, and a table or explanation of the state tests start from.
- **Actions.** A table of each action, grouped by kind, with what it does and its chance of being picked.
- **One test over time.** A timeline of one test shown horizontally, with actions, faults and the check after faults stop, and a short note on each key moment.
- **Coverage.** How many tests in the last run reached each situation, named as a state of the system, such as "a transfer from an empty account". Then the situations not reached yet, and why a longer run should reach them.
- **Scope.** What the workload doesn't test, from the "Map what the workload must reach" step in `references/workload/MODULE.md`.

Keep each section simple: a diagram or table, and a sentence or two around it. Where showing everything would crowd it, show a few examples and say how many there are, such as 3 of up to 24 runs on a timeline. Add detail only if the user asks. Leave out the driver's code. Don't invent anything. Say what each number means.

## Get an independent check

Before the user sees the explainer, have a fresh subagent review it. Give it the explainer, the driver's code and the last run's results, but not your reasoning. Tell it to check every number, example and diagram arrow against them, and that chances add up to 100%, and to list each one that doesn't hold. If you are a subagent and can't start one, return the explainer and ask your caller to run the review.

Fix each item it lists. Check every updated explainer the same way.

## Show it

Use the richest format the platform offers: an artifact in Claude Code, a site in Codex, or else an HTML file you tell the user to open.

## Iterate with the user

Ask the user:

1. Is there anything about the workload you don't understand?
2. Are there actions, or guarantees of the system, you want tested that aren't?

Wait for the user's answers before going on to other work.

Then, each round:

- **Change the workload** for every missing action the user asks for, all in one round, following `references/workload/MODULE.md`. Tell the user to wait for the run loop for the next explainer.
- **Collect guarantees** for `references/properties/MODULE.md`. Don't add assertions for finding bugs here.
- **Update the explainer,** show it again, and repeat the questions.

Stop when the user doesn't ask for changes or says the workload is good. Report the changes you made and any guarantees you collected, to hand to the properties module.
