# Forward the system's logs

The system's logs show what each node believes: who is leader, which term it's in, how far it has applied. A forwarder in each system container sends them to the driver, where a background thread parses them into each node's state. Forward client containers' logs (`references/workload/clients.md`) the same way.

## 1. Find the log lines

Find the log lines, at any level, that show each node's state: what the assertions need, and the situations worth reaching. Turn on that level through the system's own configuration in `docker-compose.yaml`.

Prefer lines that state current values over lines that announce a change. Some lines go missing (sent before the driver's port is bound, or dropped by the forwarder): a current-value line repairs the state on its next appearance, but a missed change announcement is lost for good.

## 2. Forward the logs

Add a forwarder, `driver/log-forward/`, to the harness: a small Rust binary that

- copies stdin to stdout, flushing each line;
- sends each line to `LOG_FORWARD_ADDR` over UDP, as `{"node": <$HOSTNAME>, "boot": <id>, "seq": <n>, "line": <text>}`;
- takes `boot` from the clock at startup, since the PID is the same on every container restart;
- counts `seq` from 0;
- never blocks or exits on network errors. It resolves the address once, retrying at most once a second until it does, and drops lines it can't send.

Run the system's command through it with `driver/forward-logs`, executable:

```bash
#!/usr/bin/env bash
# Run the system with its stderr through log-forward, and pass signals on to it. Once it
# exits, let log-forward drain for up to 5 s, so the last lines, often a crash message,
# aren't lost, but a leftover child holding stderr can't keep the container up.
set -m  # job control, so the system starts with SIGINT and SIGQUIT not ignored
fifo=$(mktemp -u) && mkfifo "$fifo"
log-forward < "$fifo" >&2 &
forwarder=$!
"$@" 2> "$fifo" &
system=$!
set +m
for signal in TERM INT QUIT HUP USR1 USR2; do
  trap "kill -$signal $system 2>/dev/null" "$signal"
done
while wait "$system"; status=$?; kill -0 "$system" 2>/dev/null; do :; done
(sleep 5; kill "$forwarder" 2>/dev/null) &
wait "$forwarder"
rm -f "$fifo"
exit "$status"
```

The wrapper passes stop and reload signals on to the system unchanged, and exits with its status. If the system logs to stdout, send its stdout to the fifo (`> "$fifo"`) and the forwarder's output to stdout.

In each system service's Antithesis Dockerfile, build the forwarder statically, so it runs on any base image, and put the wrapper, which needs bash, in front of the system's command:

```dockerfile
FROM rust:1-bookworm AS log-forward
RUN rustup target add x86_64-unknown-linux-musl
COPY driver/log-forward/ /src/
RUN cd /src && cargo build --release --target x86_64-unknown-linux-musl

# In the runtime stage:
COPY --from=log-forward /src/target/x86_64-unknown-linux-musl/release/log-forward /usr/local/bin/
COPY driver/forward-logs /usr/local/bin/
ENTRYPOINT ["forward-logs", "kv-server"]
```

Put the wrapper in front of whatever the image ran before. If the base image has its own `ENTRYPOINT`, keep it after `forward-logs`, and restate the base image's `CMD`, which setting `ENTRYPOINT` drops. For a base with `ENTRYPOINT ["docker-entrypoint.sh"]` and `CMD ["postgres"]`, use `ENTRYPOINT ["forward-logs", "docker-entrypoint.sh"]` and `CMD ["postgres"]`. Set `LOG_FORWARD_ADDR=driver:7777` on each system service.

## 3. Parse the lines

The receiving thread listens on UDP port 7777 and starts first in `main` ("Starting up" in `references/workload/driver.md`). Build the node states with `NodeStates::new`, passing a clone of `main`'s `active` flag, and keep them behind an `Arc<Mutex<…>>` shared with the state machine.

For the key-value store in `references/workload/driver.md`, if its nodes log `msg=raft-state term=3 role=leader commit=42`:

```rust
/// A node's state from one `raft-state` line, with the line's `boot` and `seq`.
struct NodeState { boot: u64, seq: u64, term: u64, role: String, commit: u64 }

struct NodeStates {
    latest: HashMap<String, NodeState>, // by node
    active: Arc<AtomicBool>,            // set by `main` once it sees `/workload-active`
}

impl NodeStates {
    fn new(active: Arc<AtomicBool>) -> Self {
        NodeStates { latest: HashMap::new(), active }
    }

    fn record(&mut self, node: String, s: NodeState) {
        assert_reachable!("the driver reads a node's state from its logs", &json!({}));
        if let Some(prev) = self.latest.get(&node).filter(|p| p.boot == s.boot) {
            if s.seq <= prev.seq {
                return; // arrived out of order
            }
        }
        self.latest.insert(node, s);
        if !self.active.load(Ordering::Relaxed) {
            return; // still in setup: record, don't assert
        }

        // `latest` mixes lines sent at different times: fine for guiding exploration,
        // not for checking guarantees.
        let nodes: Vec<&NodeState> = self.latest.values().collect();
        assert_sometimes!(nodes.iter().any(|n| n.role == "candidate"), "a node stands for election", &json!({}));
        assert_sometimes!(nodes.iter().any(|n| n.term != nodes[0].term), "nodes disagree on the term", &json!({}));
        if let Some(l) = nodes.iter().filter(|n| n.role == "leader").max_by_key(|n| n.term) {
            let lag = nodes.iter().map(|n| l.commit.saturating_sub(n.commit)).max().unwrap_or(0);
            assert_sometimes_greater_than!(lag, 10, "a follower falls far behind the leader", &json!({}));
        }
    }
}
```

The assertions wait for `active`, or the first election would meet them in every run.

## 4. Rules

- **Handle lines as they arrive,** in the receiving thread, not in rules. A rule runs late and misses short-lived states.
- **Share state both ways.** Rules read the node states, for example to send reads to a lagging follower. Give the receiving thread the model too (behind an `Arc`), so assertions that combine the logs with the model are checked when the line arrives. Never hold a model lock and the node-state lock at once: copy what you need from one, release it, then take the other.
- **Don't depend on arrival order across nodes.** Keep each node's lines in `seq` order. The latest state of several nodes is a mix of times: use it only for sometimes assertions.
- **Mark states worth exploring from** with exploration assertions (`references/properties/assertions.md`), especially combinations across nodes: a leader change while a follower lags, a node rejoining with a stale term. Use rich assertions when there's a distance to the state ("Rich assertions" in `references/properties/assertions.md`).
- **Assert that every kind of line you parse arrives,** with a reachable assertion per kind. Otherwise a changed format or a disabled log level looks like a quiet system.
