# Patterns

A pattern adds a piece to a workload that only some systems need. By default a workload uses none. The driver sends requests to the servers itself, and exploration assertions in the driver and in the SUT's own code show Antithesis which states to reach. Each pattern adds build work, moving parts and run time, so adopt one only when its "Use when" holds for this system. Read only the pages of the patterns you adopt.

## Stateful clients

Read `references/patterns/stateful-clients.md`.

- **Use when** the system's client library holds part of the protocol: numbered retries, sessions, leases, transactions, multi-step commits, cached routing, batching. The library's recovery code, and the servers' code for clients that fail partway, run only when the real library runs in a faulted container.
- **Don't use when** the system has no client library, or its client keeps nothing between requests. The driver speaks the protocol itself.

## Log forwarding

Read `references/patterns/log-forwarding.md`.

- **Use when** an assertion or a rule needs a node's internal state together with other nodes' state or the driver's model. Examples: nodes disagreeing on the term, a follower lagging the leader, at most one leader per term, sending reads to a lagging follower. Also use it when the state lives in code that can't take assertions: a third-party binary, or code you can't change.
- **Don't use when** one node's own state is enough. Put the assertion in that node's code instead ("Exploration assertions" in `references/properties/assertions.md`). It fires at the moment the state occurs, needs no extra log level, and can't break when the log format changes.

## Retroactive logging

Read `references/patterns/retroactive-logging.md`.

- **Use when** the system's verbose logs, such as trace level, would help debug a failure, but logging them in every run would slow the system or fail the `Logging output was limited` property.
- **Don't use when** the normal log level is enough, or the system can turn on verbose logging while it runs. Then a command at the moment can turn it on (`references/debug/MODULE.md`).

## Adopting one

Read the pattern's page. It says what the pattern adds to each workload step: the driver, the harness, the local loop and short runs. Do those as part of the steps in `references/workload/MODULE.md`. In the report, tell the user which patterns you adopted and why.

To add a pattern to an existing workload, make its changes, then build and validate (`references/workload/MODULE.md`), and iterate locally (`references/workload/local-loop.md`) and on short runs (`references/workload/run-loop.md`) again.
