# Instrumentation triage

Use this guide to verify that the system under test (SUT) and its client programs are instrumented and that their symbols are registered. Without instrumentation and symbols, Antithesis cannot do coverage-guided fuzzing or thread pausing. This limits how much of the system Antithesis can test. Treat missing instrumentation as a setup problem.

## Step 1: check the setup properties

```bash
snouty runs properties "${RUN_ID}" --detail --name "software was instrumented"
snouty runs properties "${RUN_ID}" --detail --name "every instrumented module has symbols"
snouty runs properties "${RUN_ID}" --detail --name "thread pausing was enabled"
```

All three are default properties: their examples carry values, not moments.

Each `Software was instrumented` example is one instrumented module that loaded during the run:

```json
{"module": "/usr/local/bin/geo", "language": "Go", "instrumentor": "/go/bin/antithesis-go-toolexec", "total_locations": 17, "has_catalog": true}
```

- `module` — identifies the module, usually as an executable path. One binary can appear in several examples, one per instrumented module in it.
- `total_locations` — the number of instrumentation points (basic blocks or control flow graph edges) in the module.
- `has_catalog` — whether the module has a symbol catalog.

`Every instrumented module has symbols` fails when a module loaded without a symbol catalog, or a binary provided for symbols wasn't cataloged in full, for example after link-time optimization. Failing examples name the module or binary.

**Deduplication caveat:** Antithesis deduplicates these two example lists by debug id. The same binary that starts in many containers appears once. Distinct binaries that share a debug id — for example several Go binaries built from one instrumented module — also collapse into one entry. An expected binary can be absent from the list even when it is instrumented.

Each `Thread pausing was enabled` example is a `"binary (container)"` string. This list is per container, and it is not deduplicated by debug id. A binary in this list is instrumented. A binary absent from this list can still be instrumented.

For Java, Python and .NET, also check the properties whose names contain `paths found` and `invalid paths`. See `snouty docs show /docs/reference/default_properties/`.

## Step 2: compare against the expected binaries

The setup normally instruments the SUT binaries, including any client programs that run the system's client library. Whether the workload's own binaries are instrumented depends on its build. A workload built with this skill instruments its driver too, when the driver's language allows. Build the expected list from the source code when you have access to it — the harness and build files show which binaries the setup instruments. Without source access, infer the list from the user's request, the run description, and the containers in the run.

- **Any of these properties fails** — a significant finding: something is probably wrong with the instrumentation setup. Report a setup problem and link the [instrumentation documentation](https://antithesis.com/docs/product/writing_tests/instrumentation/coverage_instrumentation/).
- **Every expected binary appears in a property** — instrumentation works. Report the modules and their `total_locations`.
- **Some expected binaries are missing** — do not conclude that they are uninstrumented; deduplication can hide them. Report which binaries the properties confirm, and state that the deduplicated lists cannot confirm the rest.

When you cannot build an expected list, report what the properties show and note the deduplication caveat.
