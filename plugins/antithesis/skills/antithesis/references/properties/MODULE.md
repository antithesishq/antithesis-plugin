# Properties

This module imports or defines the SUT's guarantees, such as "acknowledged writes are never lost", and checks each with one or more Antithesis SDK assertions, in the driver or the system's own code. Assertions are the only way to define properties: each assertion becomes a property in the run, and the guarantee holds when its properties pass.

Add them to a workload built with `references/workload/MODULE.md`. If there is none, build it first.

- `define`: add one guarantee the user describes. Follow "Define a guarantee".
- `import`: add guarantees from a source the user points to. Follow "Import guarantees".

If the request names no guarantee or source, suggest guarantees to import by reading the system's docs, tests, comments, and past bugs.

## Define a guarantee

Input: a guarantee the user wants tested, in their words. For example: "transfers between accounts never change the total balance."

### 1. Make it checkable

Restate the guarantee as one or more conditions checkable in code. Confirm the system promises it, from its docs, its API contract, what its real clients rely on, and its code. A system that copies another's API, such as an S3-compatible store, often promises less than the original. Don't assume the original's guarantees. Ask the user about anything the code can't answer, such as whether the total is ever expected to change, or whether account balances can go negative.

Pick the assertion type for each condition from "Types" in `references/properties/assertions.md`.

### 2. Add the check

Put the check where it can see the condition, following `references/properties/checks.md`:

- **A driver rule**, for what clients see. See "Responses, against the model".
- **The log thread**, for a node's internal state. See "Node state, from the logs".
- **A quiet period**, for what must hold once faults stop. See "After faults stop".
- **The system's code**, only when nothing outside it can see the condition. Tell the user, since it changes their code. Read the SDK's API for the system's language in `references/workload/sdk.md`.

Then add exploration assertions on the situations that lead up to the guarantee being tested, such as an account balance reaching zero ("Exploration assertions" in `references/properties/assertions.md`). Don't add one just to show the guarantee's check ran: its assertion already fails if it's never reached.

### 3. Check it locally

Run the local loop in `references/workload/local-loop.md`. Its assertions should pass. Then break the condition on purpose, for example by applying a transfer's debit without its credit, and confirm they fail. Undo the change.

If an assertion fails without a change, read the system's code. A broken promise is a real bug: keep the assertion. A check stricter than the guarantee, such as treating a transfer whose response timed out as never applied, needs fixing. Otherwise, ask the user whether it's a bug.

### 4. Check it in a short run

Launch a short run as `references/workload/run-loop.md` describes, and read it with the triage module. Its properties should pass, including those for the situations leading up to it.

Treat early failures as in step 3. To find a failure's cause, use the triage module's `root-cause` mode.

## Import guarantees

Input: a source of guarantees, such as a property catalog for this kind of system, the user's documents (a spec, design doc or SLA), existing tests or checks, or past bugs.

Work in batches of up to 10 guarantees, unless the request says otherwise.

1. List the guarantees the source states or implies that apply to this system. For a past bug, confirm its cause from the fix, not only the report.
2. Show the user the most important batch, and ask which to add, unless the request already says which.
3. Define each chosen guarantee with steps 1 to 3 of "Define a guarantee", then check them all in one short run (step 4).
4. If the source has more, ask the user whether to import the next batch, unless the request already says.

### Template property catalogs

The Antithesis docs provides property catalogs for some common system shapes. Read one with `snouty docs show <path>`:

- **Key-value datastores:** `/docs/resources/kv_property_catalog/`
- **Message queues:** `/docs/resources/message_queues_property_catalog/`
- **Blockchains:** `/docs/resources/blockchain_property_catalog/`
- **Any software system:** `/docs/resources/reliability_properties/`
