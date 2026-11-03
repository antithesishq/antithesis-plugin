# Assertions

An assertion is an Antithesis SDK call in the driver or the SUT's code. Each assertion, identified by its message, becomes one property in the run, judged by the default property for its type (`references/antithesis/explainer.md`). A failing assertion doesn't stop the program. For the full API in each language, see `snouty docs tree sdk`.

## Types

| Assertion                       | Use it for                                                 | Fails when                                       |
| ------------------------------- | ---------------------------------------------------------- | ------------------------------------------------ |
| `assert_always!`                | a condition that must hold every time it's checked         | false at least once, or never reached            |
| `assert_sometimes!`             | a situation that must happen at least once per run         | never true, including never reached              |
| `assert_reachable!`             | code that must run at least once per run                   | never reached                                    |
| `assert_unreachable!`           | code that must never run                                   | reached at least once                            |
| `assert_always_or_unreachable!` | avoid it: it passes silently when never reached            | reached and false at least once                  |

Every type except `assert_unreachable!` and `assert_always_or_unreachable!` fails if it's never reached, so its passing already proves it ran. Never add a reachable or sometimes assertion next to another assertion just to show the check ran: it adds nothing. Rather than `assert_always_or_unreachable!`, improve the workload so it reaches the check, or fuzz for longer.

## Rich assertions

The numeric and boolean forms (`assert_always_greater_than!`, `assert_sometimes_greater_than!`, `assert_sometimes_all!`, `assert_always_some!`, and so on) follow their base type, and attach the compared values to the details. They are an advanced way to steer Antithesis toward a particular state. A plain assertion only tells Antithesis whether its condition held. A rich assertion also shows how close each moment came to flipping it, and Antithesis prefers to explore from the moments that came closest:

- **`assert_sometimes_greater_than!(lag, 10, ...)`**: while `lag` stays at or below 10, Antithesis prefers moments with a higher `lag`, working toward the first moment the condition is true.
- **`assert_always_greater_than!(a, b, ...)`**: Antithesis prefers moments with a smaller `a`, working toward a counterexample.
- **`assert_sometimes_all!`** and **`assert_always_some!`** take named booleans, and Antithesis works toward the moment when all of them are true, or none of them.

Use one wherever a situation or a condition has a distance to it, such as a lag, a queue depth, a count of failed nodes or a balance.

## Messages and details

Each message is one assertion in Antithesis, and assertions that share a message merge into it. Keep each message fixed and unique, and put changing values, and what you'd need to debug a failure, in the details.

## Guarantee assertions

A guarantee assertion checks something the SUT promises: an `assert_always!`, `assert_unreachable!` or rich always form. Its failure is a bug, or a check stricter than the guarantee. Write them with the properties module (`references/properties/MODULE.md`), which says where each check goes (`references/properties/checks.md`).

## Exploration assertions

An exploration assertion marks a state worth reaching: an `assert_sometimes!`, `assert_reachable!` or rich sometimes form. Antithesis explores from the moments that reach it, and a run's results show which states and code it reached. Its failure means the run never reached that state, not that the system broke a guarantee. Put them on situations, never next to a check.

**In the driver:**

- **On the rare outcome of every action** in the surface you mapped (`references/workload/surface.md`), and on both sides of every option. If a situation and its opposite are both possible, add one for each.
- **On situations that need faults,** as clients see them: a request that times out, then succeeds on retry; a read served by a new leader.
- **On combinations no single request shows,** from the model or from the nodes' state in the logs (`references/workload/system-logs.md`).
- **On the situations that lead up to a guarantee being tested.** For example, `assert_sometimes_less_than_or_equal_to!(balance, 0, "an account balance reaches zero", ...)` steers Antithesis toward drained accounts, where a transfer can overdraw one or must be rejected, and shows that the workload gets there. Mark only states the system allows: a sometimes assertion on a state it forbids fails every run.

**In the SUT's code,** for what no response or log line shows:

- **`assert_reachable!` on each branch that matters and that only faults or rare timing reach:** error handling, retries, timeouts, recovery, rollback, a snapshot install, a node rejoining with a stale term.
- **`assert_sometimes!` on internal states,** such as a queue filling up, a lease expiring while held, or a write racing a compaction.
- **Not on every line.** One per branch that matters is enough.

## Assertions in the SUT's code

Add them with the Antithesis SDK for the SUT's language, in the code that runs in its containers, including the client library. They change the user's code, so tell the user, and keep them in a change of their own that the Antithesis build applies. The SDK must register them in the assertion catalog, so that one that's never reached still fails: follow the language's page in the SDK docs and `snouty docs show /docs/reference/sdk/assertion_cataloging/`.

## Reading them

- **Locally,** the SDK writes each assertion to the file in `ANTITHESIS_SDK_LOCAL_OUTPUT`, and the local loop lists the ones that would fail in a run ("Check the behavior" in `references/workload/local-loop.md`).
- **In a run,** each assertion is a property: read them with the triage module. An assertion with no examples and no counterexamples was never reached. Expect a short run to miss rare situations, but not common ones.
- **On an `in_progress` run,** only these results are final: `Always`, `AlwaysOrUnreachable` or `Unreachable` failing, and `Sometimes` or `Reachable` passing. The rest settle when the run completes.
