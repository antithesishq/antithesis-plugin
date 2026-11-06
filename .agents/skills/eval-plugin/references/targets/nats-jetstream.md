# Target: NATS JetStream

The persistence layer of the NATS server, in Go. JetStream replicates each stream across servers with its own Raft implementation, and offers acknowledged publishing, message deduplication, and durable consumers. It's the durable-queue target, for the message-queue property catalog.

- **Repository:** <https://github.com/nats-io/nats-server>. The sandbox needs Go.
- **Focus:** durable, replicated streams: a 3-server JetStream cluster with streams replicated to all three servers, publishing with acknowledgements, durable consumers, and surviving leader changes and server failures.
- **Catalog:** message queue property catalog.
- **Property to define:** "a message published twice with the same Nats-Msg-Id inside the stream's duplicate window is stored only once, even when the publisher retries across a stream leader change." Why: our publishers retry on timeout and rely on message IDs to keep orders from being processed twice.
- **Client library:** our services use the official nats.go client with its reconnect handling, server discovery and publish retries turned on, and the workload doesn't run that code the way they do.
- **Cross-node checks:** every replica of a stream holding the same messages in the same order, or a replica falling too far behind the stream leader.

## Setup and cost

Not measured yet. `nats-server` is one static binary that builds in a minute or two and starts in well under a second, so setup should cost less than rqlite's. Record the build time, setup time, and billed compute hours per cap in the first eval.

## Expected findings

None recorded yet. After the first eval, add a table of confirmed bugs, as for rqlite. Jepsen's 2025 analysis of NATS 2.12 reported lost acknowledged messages and corrupted files under some faults. Check which of those the release you test fixes before you score a task that reports one.

## Quirks

- By default, JetStream syncs its files to disk every couple of minutes (`sync_interval`), not on every write. Whether a killed container can lose acknowledged messages depends on whether the guest's page cache survives the kill. A task that reports lost messages should say which setting it ran with; one that sets `sync_interval: always` has made a deliberate choice worth noting.
- Each server needs a unique `server_name`, cluster routes to the others, and a persistent `store_dir`.
- The monitoring port (8222) serves `/healthz`, `/jsz` and `/routez`, which a debugging session can read from the guest. The `nats` CLI shows stream and consumer state, including each replica's lag.
- A stream with fewer replicas than servers, or a consumer that isn't replicated, survives fewer failures by design. Check the workload's stream config before you call a loss a bug.
