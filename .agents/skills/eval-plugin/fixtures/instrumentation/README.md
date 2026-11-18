# Instrumentation fixture

One Antithesis deployment of small programs, one container each, built correctly and in the ways a build commonly goes wrong, in every language the skill instruments. Use it to check the claims in "Instrumentation" in each `plugins/antithesis/skills/antithesis/references/workload/languages/<language>.md`, and the run check in `references/triage/instrumentation.md`: that each language's local check passes on a correct build and fails on a broken one, and that a run lists a module for each correct build and none for a broken one. Re-run it when a language page's check, an SDK, an instrumentor or snouty changes.

The programs only loop doing a little branching work. The Go `driver` reports setup complete and holds the test template. There's no workload to speak of.

| Container | Build | Local check | Modules in a run |
| --- | --- | --- | --- |
| `driver` | Go, toolexec | passes | `instrfixture/cmd/driver`, `instrfixture/internal/work` |
| `goworker` | Go, toolexec, shares `internal/work` with the driver | passes | `instrfixture/cmd/worker`, `instrfixture/internal/work` |
| `gonoop` | Go, `-default-no-op` SDK with `-tags` on the command line | fails: `init_coverage` count 0 | none |
| `rustok` | Rust, rustflags and release debug info | passes | `rustfixture` |
| `rustnoflags` | Rust, no coverage rustflags | fails: no sancov sections | none |
| `rustnodebug` | Rust, no release debug info | fails: no `.debug_info` | `rustfixture`, and a `symbol catalog has no source locations` counterexample |
| `cppok` | C++, header and coverage flags | passes | `cppfixture` |
| `cppnoflags` | C++, header without the coverage flags | fails: no sancov sections | none |
| `java` | Java, `com.antithesis:ffi` on the classpath | passes | `javafixture` |
| `javanoffi` | Java, no `ffi` | fails | none: it crashes with `NoClassDefFoundError` |
| `dotnet` | .NET | passes | `dotnetfixture` |
| `node` | JavaScript | passes | `nodefixture` |
| `python` | Python, `antithesis` package, `python -m antithesis` | passes | `pythonfixture` |
| `pythonnosdk` | Python, no SDK | fails | none, and `No Antithesis build errors` fails with code 4010 |

## Use it

`fixture.py` needs Docker that can build `linux/amd64` images, and for `check-run`, a snouty that is logged in and has `snouty runs modules`. Run it from this directory:

```sh
./fixture.py build          # build every image from scratch, with the latest SDKs
./fixture.py check-local    # each language's local check, against the table above
snouty validate config
snouty launch --launcher basic_test --config config --test-name instr-fixture \
  --description "Instrumentation fixture" --max-compute-hours 12
./fixture.py check-run <run_id>
```

Each check prints one row per container, and exits 1 if any row differs from the table. `check-run` also compares the setup properties' counterexamples with the table, as one row per property. Modules appear a few minutes after the run is ready, so run `check-run` again if early rows are missing. The setup properties, such as `Every instrumented module has symbols`, are reported only near the end of the run, which takes about 22 minutes and bills about 13 compute hours at a 12-hour cap. Until they're reported, `check-run` marks their rows `wait`, and doesn't count them. If you only need the modules, cancel the run once `check-run` passes: cancelled after a few minutes, it bills about 2.5 compute hours.

To add a language or a failure mode, add a directory with a Dockerfile, a row to `COMPONENTS` in `fixture.py`, a service to `config/docker-compose.yaml`, and a row to the table above.
