# Iterating locally

## 1. Build the system for coverage

Antithesis instrumentation records nothing outside Antithesis, so use the language's own coverage. Add a `docker-compose.coverage.yaml` that overrides each system service with a coverage Dockerfile and a shared `coverage` volume, one directory per service. Client containers count as system services: the client library is code under test.

**Rust**

- In the build stage, run `rustup component add llvm-tools-preview` and build with `RUSTFLAGS="-Cinstrument-coverage -Cllvm-args=-runtime-counter-relocation"`. This overrides the Antithesis flags in `.cargo/config.toml`.
- Set `LLVM_PROFILE_FILE=/coverage/<service>/%c%m.profraw`. `%c` writes counters as they change, so the data survives a killed process. `%m` merges restarts into one file. Don't use `%p`: every container's process is PID 1, so a restart overwrites the data.

**Go**

- Build with `go build -cover -covermode=atomic -coverpkg=./...`. Set `GOCOVERDIR=/coverage/<service>`.
- Go writes counters only when `main` returns or the program calls `os.Exit`.

**Other languages**

- Use the standard tool: clang's `-fprofile-instr-generate -fcoverage-mapping` for C and C++ (same `LLVM_PROFILE_FILE` rules as Rust), JaCoCo for Java, `c8` for Node, `coverage.py` for Python.
- Check that the data survives `docker compose stop` and a container restart before trusting it.

## 2. Run the workload

In `docker-compose.coverage.yaml`, also set `ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/sdk.jsonl` on the driver, so it writes its assertions to a file.

Locally, nothing runs `first_open_gate`, so the snapshot gate would never open. Have it open on `setup_complete` instead, which is what precedes it in Antithesis. In the same override, give the container that reports setup and the gate a shared `sdk` volume, point the reporter's output into it, and replace the gate's command:

```yaml
  setup:  # the container that reports setup_complete
    environment:
      ANTITHESIS_SDK_LOCAL_OUTPUT: /sdk/setup.jsonl  # with an SDK; without one, ANTITHESIS_OUTPUT_DIR: /sdk
    volumes: [sdk:/sdk]
  snapshot-gate:
    command: ["sh", "-c", "until grep -qs antithesis_setup /sdk/*.jsonl; do sleep 1; done"]
    volumes: [sdk:/sdk]
volumes:
  sdk:
```

`up` returns once the driver has started. Start the coverage build from scratch, let the driver run for a few minutes, then stop the system:

```bash
C="docker compose -f docker-compose.yaml -f docker-compose.coverage.yaml"
$C down -v && $C up -d --build
sleep 300
$C cp driver:/tmp/sdk.jsonl .
$C stop
```

## 3. Check the behavior

- **Actions.** Every action reaches its intended outcome sometimes, and none is routinely slow.
- **Assertions.** Only sometimes assertions for situations that need faults should be unmet. This lists every assertion that would fail in a run:

  ```bash
  jq -rs '[.[].antithesis_assert // empty] | group_by(.message)[]
    | select(if .[0].assert_type == "sometimes" then any(.hit and .condition) | not
             else any(.hit and (.condition | not)) or (.[0].must_hit and (any(.hit) | not)) end)
    | "\(.[0].display_type)\t\(.[0].message)"' sdk.jsonl
  ```

  An unmet sometimes assertion means the workload doesn't reach that situation: change the actions or their mix.
- **Quiet periods.** One forced on finds the healthy system recovered.
- **System logs.** All the logs that we expect to see, arrive.
- **Shutdown.** `docker stop` on a system container shuts its process down rather than killing it.

## 4. Read the coverage

After the system stops, use the language's coverage tool on the `coverage` volume to list the functions in the system's own source that never ran. E.g., `llvm-cov` for Rust, C and C++, and `go tool cover` for Go.

Error-handling and recovery code will look unreached without faults; leave it to the Antithesis runs.

## 5. Close the gaps

- **A request the workload never sends:** add it to the driver.
- **A rare condition** (an error path or race): act only if a different action mix would make it common.

Repeat until the remaining gaps are rare conditions or out of scope.
