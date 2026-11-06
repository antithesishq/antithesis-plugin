# Target: rqlite

A distributed SQLite database on hashicorp/raft, in Go. Its HTTP API offers reads at several consistency levels and forwards writes from followers to the leader, which makes linearizability and durability easy to check.

- **Repository:** <https://github.com/rqlite/rqlite>. Agents in both evals wrote the driver in Rust, so the sandbox needs Go and Cargo.
- **Focus:** the core distributed behavior: a 3-node cluster, writes, reads at the different consistency levels, and surviving leader changes and node failures.
- **Catalog:** key-value property catalog.
- **Property to define:** "once faults stop, a node that reports itself ready on /readyz serves reads at level none that are no more than a few seconds behind the leader." Why: our recent runs suggest a node can look healthy while its Raft is stuck, and I want that caught as its own property. Eval 1 defined "every write that rqlite acknowledges is applied exactly once, including writes a follower forwards to the leader" instead, which caught the double-apply bug below 46 times in one short run.
- **Client library:** real applications don't speak rqlite's HTTP API by hand, they use a client library like gorqlite, which has its own leader discovery, peer handling and retry logic. Our driver bypasses all of that.
- **Cross-node checks:** at most one leader per term, or followers falling too far behind the leader.

## Setup and cost

- Images build in about 5 minutes. Setup in a run takes seconds, so a 12-compute-hour run fuzzes for almost all of its 15 minutes.
- Billing: about 14.5 compute hours for a 12-hour cap, and 26.5 for 24.

## Expected findings

Evals 1 and 2 (2026-11-04/05) found these bugs at commit `8d71a376`, with plugin 0.0.8–0.0.9. Score whether each task finds them again, and how strong its evidence is. On a newer commit, a miss may mean upstream fixed the bug: check before you count it against the plugin. Never mention these in a prompt.

| Bug | Where | First confirmed by |
| --- | --- | --- |
| A forwarded write is applied twice: `cluster.Client.retry` makes at least one retry (`max(1, maxRetries)`) on a new connection, and the leader also applies the late first copy, so an old value overwrites newer acknowledged writes | `cluster/client.go:860`, `cluster/service.go:571` | Eval 1: Raft log dump in a debugging session. Eval 2: re-run with server-side logging, and a failing unit test |
| The leader stays stuck in leadership transfer: a stale `followerReplication` blocks on `triggerDeferErrorCh`, and the transfer flag survives into the next term. Upstream hashicorp/raft#696 | hashicorp/raft v1.8.0 `raft.go:1003` | Eval 1: goroutine dumps across vtimes in a debugging session |
| A follower livelocks after `POST /snapshot?trailing_logs=1` compacts below entries it wrote as an isolated leader, which never committed. The leader pins `nextIndex` at 1 and never sends a snapshot | hashicorp/raft v1.8.0 follower `appendEntries` (`raft.go:1494-1536`) | Eval 2: live Raft state, decoded `raft.db`, and a forced snapshot that resolved it, in a debugging session |
| A follower's Raft loop blocks in `installSnapshot` when the sender dies mid-transfer, because there is no read deadline. Heartbeats keep it looking healthy | hashicorp/raft v1.8.0 `raft.go:1909` | Eval 2: goroutine dump from the workload's own diagnostics |
| `rqlited` exits 1 (`clustering failure: boot canceled`) when stopped during boot. Harmless, but it fails "no unexpected container exits" | `cmd/rqlited/main.go:251` | Evals 1 and 2: log correlation, with a clean stop as the control case |
| The leader resends its snapshot forever: the follower's consistency check ignores its own snapshot index, so it rejects every append after installing (26,530 installs in one timeline) | hashicorp/raft v1.8.0 `appendEntries`, `installSnapshot` → `compactLogs` | Eval 2: logs and code, from plain-language triage and the patterns session |
| rqlite's snapshot store wedges: snapshot names (`term-index-msec`) collide (`rename … file exists`), leaving an unfinished reap that blocks every later restore | `snapshot/store.go` | Eval 2: logs and code, patterns session |
| A restarted node that already has state still runs the bootstrapper and exits on `clustering failure: boot timeout` | `cmd/rqlited/main.go:252` | Eval 2: logs, patterns session's "never exits unless told" property |
| `POST /snapshot?trailing_logs=N` panics while the store is still opening (`s.raft` is nil); net/http recovers it | `store.Snapshot` | Eval 2: logs, patterns session |
| Not confirmed: on `/db/request`, `level=auto` skips the leader check (`eqr.Level` instead of the resolved level) | `http/service.go` | Eval 2: reading the code only |

## Quirks

- `rqlited` serves pprof and `/status` on its HTTP port, 4001. A debugging session can read goroutines and Raft state from the guest with `podman exec`.
- `-bootstrap-expect 3` with `-join` makes every restart go through the boot step, which is where the exit-1 bug lives.
- The repo has its own `CLAUDE.md`.
