# C and C++

## Antithesis SDK

- **Source:** the header-only library at `github.com/antithesishq/antithesis-sdk-cpp`. It compiles only with a recent clang, as C++20: the top of the header states the minimum. C has no released SDK: follow `references/workload/languages/fallback.md`.
- **Latest version:** `gh api repos/antithesishq/antithesis-sdk-cpp/tags --jq '.[0].name'`.
- **Reference:** the header itself, `https://raw.githubusercontent.com/antithesishq/antithesis-sdk-cpp/<tag>/antithesis_sdk.h`.
- **Init:** none.
- **Setup complete:** `antithesis::setup_complete(details)`.
- **Assertions:** macros, such as `ALWAYS`, `SOMETIMES`, `REACHABLE` and `SOMETIMES_GREATER_THAN`.
- **Cataloging:** follow `snouty docs show /docs/reference/sdk/cpp/`.

## Instrumentation

`snouty docs show /docs/reference/sdk/cpp/instrumentation/`.

## Local coverage

- Build with clang's `-fprofile-instr-generate -fcoverage-mapping`.
- Set `LLVM_PROFILE_FILE=/coverage/<service>/%c%m.profraw`. `%c` writes counters as they change, so the data survives a killed process. `%m` merges restarts into one file. Don't use `%p`: every container's process is PID 1, so a restart overwrites the data.
- Read it with `llvm-cov`.

## Hegel driver

Hegel's frontend is C++ only.

- **Package:** the `hegel` CMake library, fetched with `FetchContent` from `https://github.com/hegeldev/hegel.git`, at the latest `frontends/cpp/<version>` tag, with `SOURCE_SUBDIR frontends/cpp`. The build compiles the engine with `cargo`, so the build stage needs a Rust toolchain, unless you pass a prebuilt engine with `-DHEGEL_LIBHEGEL_LIBRARY`. See the frontend's README: <https://github.com/hegeldev/hegel/tree/main/frontends/cpp>.
- **Latest version:** `git ls-remote --tags --refs https://github.com/hegeldev/hegel.git 'frontends/cpp/*' | sed 's#.*refs/tags/##' | sort -V | tail -1`.
- **Docs:** <https://hegel.dev/cpp>. "Write a workload program" covers `HEGEL_MAIN`.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/cpp/examples/sqlite_bank>, a concurrent bank workload run from `HEGEL_MAIN`, with its `CMakeLists.txt`.

| In `driver.md`              | In C++                                                                           |
| --------------------------- | -------------------------------------------------------------------------------- |
| Main entry point            | `HEGEL_MAIN(workload, {{settings}})(hegel::TestCase& tc) {{ ... }}`              |
| Concurrent state machine    | `hegel::stateful::run_concurrent(machine, tc, min_concurrency, max_concurrency)` |
| Rule, its groups and weight | a rule's `.groups = {{"g"}}` and `.weight = 6.0`                                 |
| Always-run invariant        | an invariant's `.always_check = true`                                            |
| Unbounded step count        | the setting `.stateful_step_count = INT64_MAX`                                   |
| Generate only               | the setting `.phases = {{hegel::Phase::Generate}}`                               |
| Weighted boolean draw       | no generator: draw an integer in a range, and compare it with a threshold        |

Build stage: base it on `rust:1-bookworm`, so `cargo` is there for the engine, and install `cmake` and the latest clang the image offers, which the SDK needs. Build with CMake, and copy the driver binary to `/src/target/release/driver`.
