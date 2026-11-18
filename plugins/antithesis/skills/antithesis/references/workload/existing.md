# Work on an existing workload

## Classify it

Read the workload's deployment, a `docker-compose.yaml` or Kubernetes manifests, and the images it builds, and classify it:

- **Hegel driver:** one container runs a driver that depends on hegel ("Hegel driver" in its language's page under `references/workload/languages/`), and its test template holds one `first_` command.
- **Test composer:** test templates, `/opt/antithesis/test/v1/<test>/`, hold commands such as `parallel_driver_` and `eventually_`, and Antithesis picks which runs when.
- **Unknown:** anything else.

On Kubernetes, the same classes hold, with pods in place of containers. Keep it on Kubernetes, and adapt this module's Compose commands with `snouty docs show /docs/setup/kubernetes/`.

Tell the user the class, the deployment, and the evidence. Never convert a workload to another class unless the user asks. To convert one, follow "Convert a test composer workload".

## Find what to improve

Iterating closes gaps between what the workload reaches and what it should, without losing what it checks. Start from the user's goal, such as a feature to cover or a failed run. Without one, find the gaps:

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

Describe the workload to the user, and ask whether to improve it as it is or build a hegel driver workload beside it. To improve it, follow "Find what to improve", then `references/workload/local-loop.md` and `references/workload/run-loop.md`, with only the checks that fit.

## Convert a test composer workload

Don't translate the old workload command by command. Build a new one:

1. **Learn the SUT,** with `references/workload/surface.md`.
2. **Learn the old workload:** what it aims to test, its setup, and what each test command does and asserts. Read each command by its type:
   - `first_`: setup every timeline needs, run without faults. Decide whether it's something to test or vary per timeline, or fixed setup that belongs before setup complete.
   - `parallel_driver_`: the actions clients take concurrently, the core of what to exercise.
   - `serial_driver_`: actions that need the system to themselves.
   - `singleton_driver_`: a whole scenario, once per timeline, often an existing test. One that wraps a unit or integration test framework may not port at all.
   - `anytime_`: checks meant to hold at any moment, while actions run.
   - `eventually_`, `finally_`: guarantees that must hold once faults stop and the system recovers.
3. **Build a hegel driver workload** with "Steps" in `references/workload/MODULE.md`. Draw on the old workload when you pick rules, invariants and assertions, and reuse what you can: its container machinery, setup logic, configuration, actions, checks and assertions. Keep each reused assertion's message, so its property keeps its history.

Setup complete comes only from the driver. Turn off every other reporter in the new workload only, such as with an environment variable its deployment sets, so the old workload still starts.

Migrate in steps if that's easier: Antithesis picks one test template per timeline, so the driver's template can run beside old templates not yet worth porting, whatever "The test template" in `references/workload/harness.md` says.

The conversion is done when the new workload, with any old templates you kept, reaches every property the old workload's recent runs reached (per the triage module), and fails none they passed unless the failure is a SUT bug. Then ask the user before you delete the old templates you didn't keep.
