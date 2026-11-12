# Target: NATS JetStream

The persistence layer of the NATS server, in Go. JetStream replicates each stream across servers with its own Raft implementation, and offers acknowledged publishing, message deduplication, and durable consumers. It's the durable-queue target, for the message-queue property catalog.

- **Repository:** <https://github.com/nats-io/nats-server>. The sandbox needs Go.
- **Focus:** durable, replicated streams: a 3-server JetStream cluster with streams replicated to all three servers, publishing with acknowledgements, durable consumers, and surviving leader changes and server failures.
- **Catalog:** message queue property catalog.
- **Property to define:** "a message published twice with the same Nats-Msg-Id inside the stream's duplicate window is stored only once, even when the publisher retries across a stream leader change." Why: our publishers retry on timeout and rely on message IDs to keep orders from being processed twice.
- **Client library:** our services use the official nats.go client with its reconnect handling, server discovery and publish retries turned on, and the workload doesn't run that code the way they do.
- **Cross-node checks:** every replica of a stream holding the same messages in the same order, or a replica falling too far behind the stream leader.

## Setup and cost

Measured in eval 3 (2026-11-12, v2.15.3):

- `go build .` takes about 24 s on 8 cores once modules are cached. The images, with a toolexec build of the server and the `nats` CLI, build in a few minutes. Runs reach `ready` in about 5 minutes.
- Billed compute hours ran 0.9 to 1.2 over each cap: 12 billed 12.9–13.1, 24 billed 25.1–25.2, and 104 billed 104.9. A 24-hour cap runs about 31–37 minutes of wall time on the standard tier, and a 104 cap about 2h18m.
- Debugging sessions bill about 48 compute hours per hour of wall time: 1.8 for 2.2 minutes, and 14.5 for 18 minutes.
- Eval 3 spent 235.7 compute hours and $55.83 in tokens on one track: workload 63.4, monitor run 25.2, properties 13.1, patterns 117.8, debug 14.5 and root-cause 1.8.
- The workload agent took 61 minutes to its first launch, most of it a thorough local loop.

## Expected findings

| Finding | Where | Confirmed by | First found |
| --- | --- | --- | --- |
| The first pull to a just-created consumer on another server returns `503 no responders`: the create reply arrives before the consumer's pull interest reaches the client's server. nats.go's ordered consumer recreates its consumer on every `Fetch`, so a full read through it keeps restarting. A transient error that a retry clears; low severity; no upstream issue found. | nats-server consumer create versus route interest; nats.go `jetstream/ordered.go:456` | Eval 3 debug: commands at the failing moment (104 of 261 cross-server first pulls got 503, none of 139 same-server), and a raw-protocol reproducer on a local cluster with no faults (17 of 500) | eval 3 |

Expected behaviour, not bugs. Score a task down if it reports these as bugs:

- **Stale stream info from a partitioned member:** a member that has lost its leader answers `STREAM.INFO` from its own state (`jetstream_api.go`, `isGroupLeaderless`). Eval 3's root-cause proved this live.

Jepsen's analysis of 2.12.1 lists four issues still open on 2026-11-11: #7549 (`.blk` bit flips), #7556 (`$SYS` snapshot corruption), #7564 (lazy fsync by default) and #7567 (a power failure plus pauses or partitions). Eval 3's workload set `sync_interval: always` and had no file-corruption faults, so it couldn't reach any of them. Don't count them as misses unless a workload runs with the default `sync_interval`.

## Quirks

- **Check the server's instrumentation.** nats-server's `go.mod` requires `antithesis-sdk-go …-default-no-op`, so it needs the `enable_antithesis_sdk` build tag. Pass it as `GOFLAGS=-tags=enable_antithesis_sdk`. With `-tags` on the `go build` command line, `antithesis-go-toolexec`'s nested build of the SDK's `instrumentation` package misses the tag and links a no-op `RegisterModule`. The catalogs are still written and the assertions still fire, but no coverage registers and threads aren't paused. Every eval 3 run had this. Check it with `go tool nm nats-server | grep -c instrumentation.registerModuleLocked`, or in a run: `n1`–`n3` should appear under `Thread pausing was enabled`. Score a workload task on whether it checks for this, and treat a clean run without server coverage as weak evidence.

- By default, JetStream syncs its files to disk every couple of minutes (`sync_interval`), not on every write. Whether a killed container can lose acknowledged messages depends on whether the guest's page cache survives the kill. A task that reports lost messages should say which setting it ran with; one that sets `sync_interval: always` has made a deliberate choice worth noting.
- Each server needs a unique `server_name`, cluster routes to the others, and a persistent `store_dir`.
- The monitoring port (8222) serves `/healthz`, `/jsz` and `/routez`, which a debugging session can read from the guest. The `nats` CLI shows stream and consumer state, including each replica's lag.
- A stream with fewer replicas than servers, or a consumer that isn't replicated, survives fewer failures by design. Check the workload's stream config before you call a loss a bug.
