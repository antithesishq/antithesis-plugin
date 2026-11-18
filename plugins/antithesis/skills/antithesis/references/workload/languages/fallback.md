# Any other language

For a language without a page of its own.

## Antithesis SDK

None. Write assertions and setup complete as JSON lines:

- **Schema:** `snouty docs show /docs/reference/sdk/fallback/schema/`.
- **Assertions:** `snouty docs show /docs/reference/sdk/fallback/assert/`. Each assertion needs two lines in `$ANTITHESIS_OUTPUT_DIR/sdk.jsonl`: its catalog entry at startup, so one that's never reached still fails, and one each time it's evaluated.
- **Setup complete:** `snouty docs show /docs/reference/sdk/fallback/lifecycle/`.

Put this in one small module, with a function for each assertion type the code uses, and honor `ANTITHESIS_SDK_LOCAL_OUTPUT` as the SDKs do, so the local loop can read the assertions (`references/workload/local-loop.md`).

## Instrumentation

- **Languages compiled through LLVM:** `snouty docs show /docs/reference/sdk/fallback/`. Check each binary with the checks under "Instrumentation" in `references/workload/languages/cpp.md`.
- **Any other:** check the list of supported languages in `snouty docs show /docs/product/writing_tests/instrumentation/coverage_instrumentation/`. If the language isn't there, the component can't be instrumented: tell the user, and instrument the rest.

## Local coverage

Use the language's standard coverage tool.

## Hegel driver

Not supported yet: hegel has no frontend for the language. Don't write the driver in it; pick another language with `references/workload/languages.md`.
