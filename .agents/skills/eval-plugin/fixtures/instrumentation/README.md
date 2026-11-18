# Instrumentation fixture

One Antithesis deployment of small programs, one container each, built correctly and in the ways a build commonly goes wrong, in every language the skill instruments. Every eval runs it, to test whether the triage module finds the instrumentation problems ("Instrumentation triage" in `SKILL.md`). It also checks the claims in "Instrumentation" in each `plugins/antithesis/skills/antithesis/references/workload/languages/<language>.md`: that each language's local check passes on a correct build and fails on a broken one, and that a run lists a module for each correct build and none for a broken one.

The names are neutral, so an agent triaging a run of the fixture can't tell the broken builds by name. The programs only loop doing a little branching work. The `driver` reports setup complete and holds the test template. There's no workload to speak of.

| Container | Build | Local check | Modules in a run |
| --- | --- | --- | --- |
| `driver` | Go, toolexec | passes | `shop/cmd/driver`, `shop/internal/work` |
| `orders` | Go, toolexec, shares `shop/internal/work` with the driver | passes | `shop/cmd/orders`, `shop/internal/work` |
| `ledger` | Go, `-default-no-op` SDK with `-tags` on the command line | fails: `init_coverage` count 0 | none |
| `pricing` | Rust, rustflags and release debug info | passes | `rust-service` |
| `search` | Rust, no coverage rustflags | fails: no sancov sections | none |
| `shipping` | Rust, no release debug info | fails: no `.debug_info` | `rust-service`, and a `symbol catalog has no source locations` counterexample |
| `cache` | C++, header and coverage flags | passes | `cpp-service` |
| `index` | C++, header without the coverage flags | fails: no sancov sections | none |
| `billing` | Java, `com.antithesis:ffi` on the classpath | passes | `java-service` |
| `audit` | Java, no `ffi` | fails | none: it crashes with `NoClassDefFoundError` |
| `accounts` | .NET | passes | `DotnetService` |
| `web` | JavaScript | passes | `node-service` |
| `reports` | Python, `antithesis` package, `python -m antithesis` | passes | `python-service` |
| `alerts` | Python, no SDK | fails | none, and `No Antithesis build errors` fails with code 4010 |

So a correct triage reports `ledger`, `search`, `index`, `audit` and `alerts` as uninstrumented, `shipping` as built without debug info, and nothing wrong with the rest.

## Use it

`fixture.py` needs Docker that can build `linux/amd64` images, and for `check-run`, a snouty that is logged in and has `snouty runs modules`. Run it from this directory:

```sh
./fixture.py build          # build every image from scratch, with the latest SDKs
./fixture.py check-local    # each language's local check, against the table above
snouty validate config
snouty launch --launcher basic_test --config config --test-name shop \
  --description "shop services" --max-compute-hours 12
./fixture.py check-run <run_id>
./fixture.py export ~/src/shop   # the build files without this README, the script or comments
```

Each check prints one row per container, and exits 1 if any row differs from the table. `check-run` also compares the setup properties' counterexamples with the table, as one row per property. Modules appear a few minutes after the run is ready, so run `check-run` again if early rows are missing. The setup properties, such as `Every instrumented module has symbols`, are reported only near the end of the run, which takes about 22 minutes and bills about 13 compute hours at a 12-hour cap. Until they're reported, `check-run` marks their rows `wait`, and doesn't count them.

To add a language or a failure mode, add a directory with a Dockerfile, a row to `COMPONENTS` in `fixture.py`, a service to `config/docker-compose.yaml`, and a row to the table above. Keep its names neutral.
