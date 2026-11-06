# Target: ZooKeeper

Apache ZooKeeper, a coordination service in Java. It replicates with ZAB, not Raft, and documents a precise contract: linearizable writes, FIFO order per client, sequentially consistent reads, one-shot ordered watches, and sessions with ephemeral nodes. It's the JVM target, and its consensus protocol keeps triage from leaning on Raft knowledge.

- **Repository:** <https://github.com/apache/zookeeper>. The sandbox needs a JDK and Maven.
- **Focus:** the core coordination guarantees: a 3-server ensemble, creating, updating and conditionally setting znodes, reads with and without sync, watches, sessions and ephemeral nodes, and surviving leader elections and server failures.
- **Catalog:** key-value property catalog.
- **Property to define:** "an ephemeral znode disappears only when its owner's session ends, and once that session has expired, no server still serves the znode." Why: we use ephemeral nodes for leader election and service discovery, so a znode that outlives its session means two leaders.
- **Client library:** real applications don't use ZooKeeper's client API by hand, they use Apache Curator on top of it, which has its own connection handling, session management and retry policies. Our workload doesn't run that code the way they do.
- **Cross-node checks:** every server applying transactions in the same zxid order, at most one leader per epoch, or a follower falling too far behind the leader.

## Setup and cost

Not measured yet. A Maven build takes a few minutes, and a JVM server takes several seconds to start, so expect more setup per run than rqlite. Record the build time, setup time, and billed compute hours per cap in the first eval. Check that the agent sizes the JVM heap for the guest.

## Expected findings

None recorded yet. After the first eval, add a table of confirmed bugs, as for rqlite. ZooKeeper is mature, so a run with no real failures is a plausible result. Then score the workload on its coverage and on false positives.

## Quirks

- Reads are served by whichever server the client is connected to, and can be stale unless the client calls `sync` first. A task that reports a stale read without `sync` has misread the contract.
- Session expiry is decided by the leader, against timeouts negotiated from `tickTime`. A client can keep acting on an expired session until it hears of the expiry, which is documented, and subtle to check correctly.
- Each server needs a `myid` file and the full server list in `zoo.cfg`. Dynamic reconfiguration is off by default.
- The four-letter-word commands (`srvr`, `mntr`, `stat`, `dump`) need `4lw.commands.whitelist`. With it, a debugging session can read each server's role, zxid and sessions from the guest. The AdminServer on port 8080 serves the same over HTTP.
- Java instrumentation differs from Go's. Check what the plugin's instrumentation page says for the JVM, and whether the agent followed it.
