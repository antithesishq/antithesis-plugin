# Work on an existing workload

## Classify it

Read the workload's `docker-compose.yaml` and the images it builds, and classify it:

- **Hegel driver:** one container runs a driver that depends on hegel ("Hegel driver" in its language's page under `references/workload/languages/`), and its test template holds one `first_` command.
- **Test composer:** test templates, `/opt/antithesis/test/v1/<test>/`, hold commands such as `parallel_driver_` and `eventually_`, and Antithesis picks which runs when.
- **Unknown:** anything else.

Tell the user the class and the evidence. Never convert a workload to another class unless the user asks. To convert one, build a hegel driver workload with "Steps" in `references/workload/MODULE.md`, port the old workload's actions and assertions into it, and keep the old one until the new one reaches everything it did.

## Find what to improve

Iterating closes the gaps between what the workload reaches and what it should, without losing what it already checks. Start from the user's goal, such as a feature to cover or a failed run. Without one, find the gaps:

- **The surface:** each in-scope item from `references/workload/surface.md` that the workload never exercises.
- **Recent runs,** read with the triage module: failing properties, unreached assertions, slow setup.
- **Coverage:** the system's code that a local loop, run before any change, never reaches.

Fix workload bugs first, then the gaps real clients depend on most.

## Hegel driver

Follow only the "Steps" in `references/workload/MODULE.md` that the gaps need, then build, validate and run both loops. Keep the layout, language and patterns unless a gap needs a change.

## Test composer

Keep its test templates and conventions. Read `snouty docs show /docs/product/writing_tests/test_templates/test_best_practices/` first. Close each gap with a new or changed test command, and assertions in the commands or the SUT (`references/properties/assertions.md`). `references/workload/driver.md` and the driver's parts of `references/workload/harness.md` don't apply.

Run commands locally as `/docs/product/writing_tests/test_templates/testing_locally/` says, in place of the driver in `references/workload/local-loop.md`. Then follow `references/workload/run-loop.md`, skipping its driver checks.

## Unknown

Describe the workload to the user, and ask whether to improve it as it is or build a hegel driver workload beside it. To improve it, follow "Find what to improve", then `references/workload/local-loop.md` and `references/workload/run-loop.md`, using only the checks that fit it.
