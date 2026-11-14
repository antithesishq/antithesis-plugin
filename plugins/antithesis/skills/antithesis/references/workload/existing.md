# Work on an existing workload

## Classify it

Read the workload's `docker-compose.yaml` and the images it builds, and classify it:

- **Hegel driver:** one container runs a driver that depends on hegel ("Hegel driver" in its language's page under `references/workload/languages/`), and its test template holds one `first_` command.
- **Test composer:** test templates, `/opt/antithesis/test/v1/<test>/`, hold commands such as `parallel_driver_` and `eventually_`, and Antithesis picks which runs when.
- **Unknown:** anything else.

Tell the user the class and the evidence. Never convert a workload to another class unless the user asks. To convert one, follow "Convert a test composer workload".

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

## Convert a test composer workload

Build a hegel driver workload with "Steps" in `references/workload/MODULE.md`, beside the old one, and port what each test command does:

| Test command              | In the driver                                                                                       |
| ------------------------- | --------------------------------------------------------------------------------------------------- |
| `first_`                  | Admin setup, in "Starting up" in `references/workload/driver.md`, before setup complete.            |
| `parallel_driver_`        | One rule per action, in the main group.                                                             |
| `serial_driver_`          | Rules in a group of their own, each holding one lock for the whole rule, so they run one at a time. |
| `singleton_driver_`       | Its steps as rules, grouped and locked as for `serial_driver_` if they need the system alone.       |
| `anytime_`                | A check without requests becomes an always-run invariant; one with requests, a rule in every group. |
| `eventually_`, `finally_` | Assertions in the driver's eventually ("Eventually" in `references/workload/driver.md`).            |

- **Random choices** a command makes, such as `$RANDOM` or a language's `random`, become hegel draws in rules. Make a `first_` command's choices fixed in setup, or move them into a rule: nothing before the state machine draws from hegel.
- **State** commands share through files, databases or environment variables becomes the driver's model.
- **Assertions** move into the driver unchanged, with the same messages, so their properties keep their history. Leave assertions in the SUT's code where they are.
- **Setup complete** comes only from the driver. Turn off every other reporter in the new workload only, such as with an environment variable its compose file sets, so the old workload still starts.

The conversion is done when a run of the new workload reaches every property that the old workload's recent runs reached, as the triage module reports them, and fails none they passed unless the failure is a SUT bug. Then ask the user before you delete the old workload's test templates.
