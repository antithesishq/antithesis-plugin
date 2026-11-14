# Instrumentation triage

Use this guide to verify that the system under test (SUT) and its client programs are instrumented and that their symbols are registered. Without instrumentation and symbols, Antithesis cannot do coverage-guided fuzzing or thread pausing. This limits how much of the system Antithesis can test. Treat missing instrumentation as a setup problem.

## Step 1: check the setup properties

```bash
snouty runs properties "${RUN_ID}" --detail --name "software was instrumented"
snouty runs properties "${RUN_ID}" --detail --name "every instrumented module has symbols"
```

Both are default properties: their examples carry values, not moments.

Each `Software was instrumented` example is one instrumented module that registered during the run:

```json
{"module": "inventory-server", "language": "native", "instrumentor": "llvm-sancov", "total_locations": 18342, "has_catalog": true}
```

- `module` — the module's name: an executable, jar, assembly or package, depending on the language ("Instrumentation" in `references/workload/languages/<language>.md`). A module registers when its code loads, so it appears even if its process is short-lived. A module loaded in several containers appears once.
- `total_locations` — the number of instrumentation points (basic blocks or control flow graph edges) in the module.
- `has_catalog` — whether the module has a symbol catalog.

`Every instrumented module has symbols` fails when a module registered without a symbol catalog, or a file in a `/symbols` directory has nothing to symbolize. Its counterexamples name the file and the reason, such as `not coverage-instrumented`, which means a binary built without coverage, or `symbol catalog has no source locations`, which means a binary built without debug info.

Neither property shows that a particular component is instrumented: `Software was instrumented` passes when any one module registers, such as the driver's.

For code in `/opt/antithesis/catalog/` (Java, .NET, JavaScript and Python), also check the properties whose names contain `paths found` and `invalid paths`. `Paths found for Antithesis instrumentation` lists each image's catalog directories by language, and `No invalid paths found during Antithesis instrumentation` fails on a symlink to a symlink there. Python has no module, so its directory in `paths found` is the only sign its assertions are cataloged. See `snouty docs show /docs/reference/default_properties/`.

## Step 2: compare against the expected components

The setup normally instruments the SUT binaries, including any client programs that run the system's client library. Whether the workload's own binaries are instrumented depends on its build. A workload built with this skill instruments its driver too, when the driver's language allows. Build the expected list from the source code when you have access to it — the harness and build files show which components the setup instruments, and the language pages say what each module is called. Without source access, infer the list from the user's request, the run description, and the containers in the run.

- **Any expected component has no module in `Software was instrumented`** — it's uninstrumented, even though the property passes. Report a setup problem. With access to the image, confirm it with the instrumentation check under "Instrumentation" in `references/workload/languages/<language>.md`.
- **`Every instrumented module has symbols` or `No invalid paths found during Antithesis instrumentation` fails, or an expected catalog directory is missing from `paths found`** — report a setup problem with each counterexample's file and reason.
- **Every expected component has a module with a catalog** — instrumentation works. Report the modules and their `total_locations`.

Either way, link the [instrumentation documentation](https://antithesis.com/docs/product/writing_tests/instrumentation/coverage_instrumentation/) in a report of a setup problem.

When you cannot build an expected list, report what the properties show.
