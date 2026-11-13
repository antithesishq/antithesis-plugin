# Patterns

A pattern adds a piece to a workload that only some systems need. By default a workload uses none. The driver sends requests to the servers itself, and exploration assertions in the driver and in the SUT's own code show Antithesis which states to reach. Each pattern adds build work, moving parts and run time, so adopt one only when its "Use when" holds for this system. Read only the pages of the patterns you adopt.

## Stateful clients

Read `references/patterns/stateful-clients.md`.

- **Use when** the system's client library holds part of the protocol: numbered retries, sessions, leases, transactions, multi-step commits, cached routing, batching. The library's recovery code, and the servers' code for clients that fail partway, run only when the real library runs in a faulted container.
- **Don't use when** the system has no client library, or its client keeps nothing between requests. The driver speaks the protocol itself.

## Log forwarding

Read `references/patterns/log-forwarding.md`.

- **Use when** a check needs the internal state of several nodes at once, or a node's state together with the driver's model, and no one node can see it. Examples: at most one leader per term, nodes applying only values the workload wrote. Also use it when a driver rule must pick its target by node state, such as sending reads to a lagging follower, or when the state lives in code that can't take assertions: a third-party binary, or code you can't change.
- **Don't use when** a SUT-side assertion would do: one node's own state is enough, or one node learns the rest from the messages it handles. A follower that gets entries conflicting with its own log sees the divergence, and a leader that steps down on seeing a higher term knows it was deposed. Put the assertion in that node's code instead ("Exploration assertions" in `references/properties/assertions.md`). It fires at the moment the state occurs, needs no extra log level, and can't break when the log format changes.

## Adopting one

Read the pattern's page. It says what the pattern adds to each workload step: the driver, the harness, the local loop and short runs. Do those as part of the steps in `references/workload/MODULE.md`. In the report, tell the user which patterns you adopted and why.

To add a pattern to an existing workload, make its changes, then build and validate (`references/workload/MODULE.md`), and iterate locally (`references/workload/local-loop.md`) and on short runs (`references/workload/run-loop.md`) again.
