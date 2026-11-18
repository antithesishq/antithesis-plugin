# Instrumentation triage

Use this guide to verify that the system under test (SUT) and its client programs are instrumented and that their symbols are registered. Without instrumentation and symbols, Antithesis cannot do coverage-guided fuzzing or thread pausing. This limits how much of the system Antithesis can test. Treat missing instrumentation as a setup problem.

## Step 1: list the run's modules

```bash
snouty runs modules "${RUN_ID}" --detail
```

Each row is one instrumented module that a program loaded, in one container: its module ID, name, container, program, language, number of instrumented locations, and whether Antithesis has its symbols. `snouty runs modules --help` explains each column. A module appears once a program loads it, even a short-lived one, so while the run is in progress more can appear. If the command doesn't work, follow "If snouty runs modules doesn't work" instead.

SYMBOLS is `yes` when Antithesis has a symbol catalog for the module, which maps its locations to functions. It doesn't mean the catalog has source files and lines: a binary built without debug information shows `yes` too.

## Step 2: check the setup properties

```bash
snouty runs properties "${RUN_ID}" --detail --name "every instrumented module has symbols"
```

It fails when a module loaded without its symbols, or a file in a `/symbols` directory has nothing to symbolize. Its counterexamples name the file and the reason, such as `not coverage-instrumented`, a binary built without coverage, or `symbol catalog has no source locations`, a binary built without debug info.

For code in `/opt/antithesis/catalog/` (Java, .NET, JavaScript and Python), also check the properties whose names contain `paths found` and `invalid paths`. `Paths found for Antithesis instrumentation` lists each image's catalog directories by language, and `No invalid paths found during Antithesis instrumentation` fails on a symlink to a symlink there. See `snouty docs show /docs/reference/default_properties/`.

## Step 3: compare against the expected components

The setup normally instruments the SUT binaries, including any client programs that run the system's client library. Whether the workload's own binaries are instrumented depends on its build. A workload built with this skill instruments its driver too, when the driver's language allows. Build the expected list from the source code when you have access to it — the harness and build files show which components the setup instruments. For each, note the module ID where its build provides one, or else its name and container ("Instrumentation" in `references/workload/languages/<language>.md`), and whether its process runs from the start of every timeline, or starts only when something triggers it, such as a CLI tool, a repair job or a rarely used helper. Without source access, infer the list from the user's request, the run description, and the containers in the run.

- **A component whose process is running has no module** — it's uninstrumented. Its logs or SDK assertions show that it's running. Report a setup problem, and with access to the image, confirm it with the instrumentation check under "Instrumentation" in `references/workload/languages/<language>.md`.
- **A component that starts only when something triggers it has no module** — judge it after the run. If the run shows its process ran, it's uninstrumented. If not, its code wasn't reached, which is a coverage finding, not a setup problem.
- **A module has SYMBOLS `no`, a setup property fails, or an expected catalog directory is missing from `paths found`** — report a setup problem with each file and reason.
- **Every expected component has a module with symbols** — instrumentation works. Report the modules and their locations.

Either way, link the [instrumentation documentation](https://antithesis.com/docs/product/writing_tests/instrumentation/coverage_instrumentation/) in a report of a setup problem.

When you cannot build an expected list, report what `snouty runs modules` and the setup properties show.

## If snouty runs modules doesn't work

An older snouty has no `runs modules`, and a run created before release 67 has no module list. Read the modules from the examples of this property instead, then follow "check the setup properties" and "compare against the expected components":

```bash
snouty runs properties "${RUN_ID}" --detail --name "software was instrumented"
```

Each example is one module, with its name, language and number of locations, but not its container. Don't judge a component by the property passing: it passes when any one module loads, such as the driver's.
