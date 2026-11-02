# Property queries

Use `snouty runs properties` to retrieve properties and `snouty runs --json logs` to download a log of a specific history. The properties output gives you the moments you need to get the logs.

## Getting all properties

`snouty runs properties "${RUN_ID}" --detail` lists every property for a run, failing first. Narrow with `--failing`, `--name` or `--group`:

```text
Name      a query returns exactly the records that match it
ID        0116733fdcb05189119ccc536aad4044
Group     Always assertions
Category  Antithesis SDK
Status    failing
Examples  showing 1 out of 261 passing examples and 1 out of 16 failing examples
  STATUS   HASH                 VTIME
  failing  494832216310308818   139.0624840699602
  passing  3296738555862413105  117.73925844929181
```

- `Name` is the name of the property as it appears in the run's page in Antithesis and as it is known to the user.
- `Status` is `passing`, `failing`, or `undetermined` (not triggered yet).
- `Examples` gives the number of passing examples (times the property PASSED) and failing examples, or counterexamples (times it FAILED). These counts are from across all the histories in the run, not just the few example moments shown for the property.

Each row is a moment: its `HASH` is the input hash and its `VTIME` the vtime. These let you retrieve the log of the history leading up to the property's pass or failure.

> **Note:** Not every property has moments. Telemetry / meta properties — e.g. `Hypervisor utilization`, `Customer output volume`, `Fault injector total packets`, `Symbols were uploaded`, `Assertions are present in customer code`, `Fuzzing has branches`, `Unique Edges`, `The Test Composer was used` — report a result value — a scalar (number, boolean, string) or a summary object (e.g. `{session_id, total_output_mb, ...}`) — instead of moments. There is no per-history log to download for these; the counterexample value itself is the evidence. Skip the log-download step for these properties and report the value directly.

Each property may expose a few example rows, mixing failing and passing
examples. When triaging, start with the **first failing example** by default. Cross-referencing a passing example can help
narrow down root cause by showing what's different in a healthy execution. If you want more
examples, find more moments for the property with `snouty runs search` (see the triage
module's "Investigate failed properties") and download their logs.

### Using pass/fail ratios for triage prioritization

For a given property, you can examine the pass/fail counts to help investigate the property. (Remember these are the counts on the `Examples` line.)

- **All failing (0 passing)** — Likely a setup or workload bug. The property is being violated in every execution history.
- **Mostly failing with rare passes** — Most likely a setup or workload bug, or for some reason the system under test is not set up for
  Antithesis. Don't forget to read the Antithesis documentation when analyzing this.
- **Mostly passing with rare failures** — Strong candidate for a real SUT bug. Pay attention to rare event orderings or fault patterns in the logs.
- **Roughly even split** — The property may be sensitive to configuration or timing. Check whether passing vs failing correlates with fault intensity or a choice made at the beginning of the history (such as what test to run or parameters to use for a given history).

## Assertion types and what they mean for triage

Each property is backed by an assertion of a specific type. The type determines what a failure actually tells you:

- **`Always`**: Must be true every evaluation. Fails if the condition is false at least once.
- **`AlwaysOrUnreachable`**: Either never reached, or true every time reached. Fails if reached at least once AND false at least once. A rare or optional path was exercised and the invariant didn't hold. The path being reached is itself informative.
- **`Sometimes`**: Must be true at least once across the entire run. Fails if the condition is never true.
- **`Reachable`**: The assertion point must be reached at least once. Fails if never reached. Could be a test coverage gap, a workload that never triggers the state, or a SUT bug that prevents the path.
- **`Unreachable`**: The assertion point must never be reached. Fails if reached at least once. A forbidden or impossible path was entered.

On an `in_progress` run, only these results are final: `Always`, `AlwaysOrUnreachable` or `Unreachable` failing, and `Sometimes` or `Reachable` passing. The rest are settled when the run completes.

`Always` and `Sometimes` assertions imply `Reachable`. If any `Reachable` assertion fails but has no examples, this means that it was never reached. This might simply be due to the test not running long enough, or it may be that the workload is not triggering the state. It may also mean that a SUT bug is preventing the assertion from being reached, although ideally you can discern that via another property that catches the bug.

Numeric/boolean variants (e.g., `AlwaysGreaterThan`, `SometimesAll`) follow the same pass/fail semantics as their base type but attach the compared operands to assertion details automatically.

## Download a log

To further analyze a property failure, download the log leading up to the failure (or to a passing example, for comparison) and examine it.

To learn how to download and understand logs, refer to `references/triage/logs.md`.
