# Iterate locally

## 1. Build the system for coverage

Antithesis instrumentation records nothing locally, so measure local coverage with the language's own tool. Add a `docker-compose.coverage.yaml` that overrides each system service with a coverage Dockerfile and a shared `coverage` volume, one directory per service. Client containers, if a pattern adds them, count as system services: the client library is code under test.

Build each service as "Local coverage" in `references/workload/languages/<language>.md` says, for its language. Check that the data survives `docker compose stop` and a container restart before trusting it.

## 2. Run the workload

In `docker-compose.coverage.yaml`, also set `ANTITHESIS_SDK_LOCAL_OUTPUT` on the driver:

```yaml
  driver:
    environment:
      ANTITHESIS_SDK_LOCAL_OUTPUT: /tmp/sdk.jsonl
```

Also set the driver's variable that turns the eventually off there ("Eventually" in `references/workload/driver.md`), so the driver doesn't exit partway through the run. The driver's SDK then writes its assertions and its setup-complete event, `{"antithesis_setup": {"status": "complete", ...}}`, to that file. If the SUT's code has assertions (`references/properties/assertions.md`), set it on each of those services too, as `/coverage/<service>/sdk.jsonl`, and copy each file out as `sdk-<service>.jsonl` next to the driver's.

Nothing runs test commands locally, so run the driver's first command yourself right after `up`, which also checks it. Running it before setup complete is fine.

Start the coverage build from scratch, wait for setup complete, let the workload run for a few minutes, then stop the system. Run it as one command, since `COMPOSE_FILE` applies only within it:

```bash
export COMPOSE_FILE=docker-compose.yaml:docker-compose.coverage.yaml
docker compose down -v && docker compose up -d --build &&
docker compose exec -T driver /opt/antithesis/test/v1/main/first_start_workload &&
timeout 600 sh -c 'until docker compose exec -T driver grep -qs antithesis_setup /tmp/sdk.jsonl; do sleep 5; done' &&
sleep 300
docker compose cp driver:/tmp/sdk.jsonl .
# For each SUT service with assertions:
docker compose cp <service>:/coverage/<service>/sdk.jsonl sdk-<service>.jsonl
docker compose stop
```

Copy each run's logs and `sdk.jsonl` files into a fresh directory, outside the config directory, so a run never overwrites the last one's evidence or ends up in the config image.

If setup complete never arrives, the driver stopped in its startup. `docker compose logs driver`, with the same `COMPOSE_FILE`, shows what it was waiting for or which request failed.

## 3. Check the behavior

- **Startup.** `the workload starts` was reached.
- **Actions.** Every action reaches its intended outcome sometimes, and none is routinely slow.
- **Assertions.** Only `assert_sometimes` and `assert_reachable` assertions on situations or code that need faults are unmet, which is expected without faults. This lists every assertion that would fail in a run:

  ```bash
  jq -rs '[.[].antithesis_assert // empty] | group_by(.message)[]
    | select(if .[0].assert_type == "sometimes" then any(.hit and .condition) | not
             else any(.hit and (.condition | not)) or (.[0].must_hit and (any(.hit) | not)) end)
    | "\(.[0].display_type)\t\(.[0].message)"' sdk*.jsonl
  ```

  Any other unmet `assert_sometimes` or `assert_reachable` means the workload doesn't reach that situation or code: change the actions or their mix.
- **Eventually.** Run once more with the eventually on and its direct call set to a minute or two of workload. The driver logs that its assertions start and that it's ending the timeline, then exits with status 0 (`docker compose ps -a`), and the eventually's assertions pass. `docker compose cp` still copies `sdk.jsonl` from the stopped container.
- **Shutdown.** `docker stop` on a system container shuts its process down cleanly, without a kill.
- **Debug tools.** Each debug tool ("Debug tools" in `references/workload/harness.md`) runs in its container. Check them in the session above, before `docker compose stop`, such as `docker compose exec -T <service> jq --version`.
- **Patterns.** Each pattern you adopted passes its own local checks.

## 4. Read the coverage

After the system stops, run the language's coverage tool on the `coverage` volume, and list the functions in the system's own source that never ran.

Error-handling and recovery code looks unreached without faults. Don't chase it locally: put exploration assertions on it ("Exploration assertions" in `references/properties/assertions.md`), and check them in the Antithesis runs (`references/workload/run-loop.md`).

## 5. Close the gaps

- **A request the workload never sends:** add it to the driver.
- **A rare condition** (an error path or race): act only if a different action mix would make it common.

Repeat until the remaining gaps are rare conditions or out of scope.
