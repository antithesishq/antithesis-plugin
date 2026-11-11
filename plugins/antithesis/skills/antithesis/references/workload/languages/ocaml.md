# OCaml

## Antithesis SDK

None. Write assertions and setup complete as JSON lines, following `references/workload/languages/fallback.md`. Put that in one small module, with a function for each assertion type the code uses.

## Instrumentation

OCaml isn't among the languages Antithesis instruments.

## Local coverage

Use the standard coverage tool for OCaml.

## Hegel driver

- **Package:** `hegel` on opam, with the `ppx_hegel_test` preprocessor.
- **Latest version:** `opam update && opam install hegel` takes the latest release on opam, which ships with its engine. opam can lag the repository; the README says how to pin a newer release, and how the package finds the engine: <https://github.com/hegeldev/hegel/tree/main/frontends/ocaml>.
- **Docs:** <https://hegel.dev/ocaml>. Read `Hegel.main`, `Stateful` and `Concurrency`.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/ocaml/examples/sqlite_bank>, a concurrent bank workload run from `let%hegel_main`, with its `dune` file.

| In `driver.md`              | In OCaml                                                              |
| --------------------------- | --------------------------------------------------------------------- |
| Main entry point            | `let%hegel_main workload tc = ...`, then `let () = workload ()`       |
| Concurrent state machine    | `module%hegel_concurrent_state_machine`, or `Stateful.run_concurrent` |
| Rule, its groups and weight | `[@@rule { groups = [ "g" ]; weight = 6 }]`                           |
| Always-run invariant        | `[@@invariant { always_check = true }]`                               |
| Unbounded step count        | `~step_count:max_int`                                                 |
| Generate only               | the setting `phases = [ Generate ]`, in `[@@settings { ... }]`        |
| Weighted boolean draw       | `draw tc (booleans ~p ())`                                            |

- Workers run on OCaml threads by default (`Concurrency.threads`). State the rules share must be safe to use from several threads.

Build stage: base it on the "OCaml build image" row in `references/workload/images.md`, install the dependencies with `opam`, build with `dune build --release`, and copy the driver binary to `/out/driver`.
