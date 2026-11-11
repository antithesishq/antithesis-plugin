# Log forwarding

A system's logs show what each node believes: who is leader, which term it's in, how far it has applied. With this pattern, a forwarder in each system container sends the lines that state this to the driver. A background thread there parses them into each node's state, where assertions can combine several nodes' state with the driver's model, and rules can read it to pick their targets.

Assertions that need only one node's state belong in that node's code, not here, if you can change that code ("Exploration assertions" in `references/properties/assertions.md`).

## 1. Find the log lines

Find the log lines, at any level, that show the state the assertions and rules need. Turn on that level through the system's own configuration in `docker-compose.yaml`, only for the module or logger that writes those lines, never globally. Every line costs the system CPU in Antithesis.

The forwarder sends lines over a Unix socket in a shared volume. Antithesis never faults it, and it delivers one container's lines in order. Within one boot of a container, the driver sees every line, except:

- **lines written before the driver bound its socket.** A node can log before the driver starts, so don't rely on its first lines;
- **the last lines before a kill,** which die with the container. The next line has a new `boot`;
- **lines the forwarder or the driver dropped,** because a queue was full or the line was too long, which leave a gap in `seq`.

A pause delays a container's lines rather than losing them. The forwarder pauses with the system, and the lines arrive late, all at once. So lines that announce a change work as well as lines that state current values, as long as the driver resets a container's state on each new boot.

## 2. Forward the logs

Add a forwarder, `driver/log-forward/`, to the harness: a small Rust binary that

- copies stdin to stdout, flushing each line;
- sends each line that contains one of the substrings in `LOG_FORWARD_MATCH` (comma-separated), such as `msg=raft-state`, to the Unix datagram socket at `LOG_FORWARD_SOCKET`, as `{"container": <$HOSTNAME>, "boot": <id>, "seq": <n>, "line": <text>}`. It skips other lines;
- takes `container` from `$HOSTNAME`, which the harness sets to the container name;
- takes `boot` from the clock at startup, since the PID is the same on every container restart;
- counts `seq` from 0, over every matching line, sent or not, so a dropped line leaves a gap;
- sends each line once, with a non-blocking `send_to`, and drops it on any error, such as a full queue or a socket the driver hasn't bound yet. It never queues, retries, blocks or exits on a send error, so a slow driver can't slow the system;
- keeps each datagram within 16 KiB: it truncates the line to 15 KiB, at a character boundary, to leave room for the JSON wrapper, and drops a line that escaping still pushes past 16 KiB.

Run the system's command through a wrapper, `driver/forward-logs`, which:

- pipes the system's stderr (or stdout, if it logs there) through the forwarder;
- starts the system with SIGINT and SIGQUIT not ignored. A non-interactive shell ignores them in background jobs unless job control is on (`set -m` in bash);
- passes TERM, INT, QUIT, HUP, USR1 and USR2 on to the system, so it still gets them as the container's main process should (`references/workload/surface.md`);
- once the system exits, lets the forwarder drain for up to 5 s, so the last lines, often a crash message, aren't lost, but a leftover child holding the pipe can't keep the container up;
- exits with the system's status.

In each system service's Antithesis Dockerfile, build the forwarder statically, on the "Rust build image" row in `references/workload/images.md`, so it runs on any base image, and put the wrapper, which needs bash, in front of the system's command:

```dockerfile
FROM <Rust build image> AS log-forward
RUN rustup target add x86_64-unknown-linux-musl
COPY driver/log-forward/ /src/
RUN cd /src && cargo build --release --target x86_64-unknown-linux-musl

# In the runtime stage:
COPY --from=log-forward /src/target/x86_64-unknown-linux-musl/release/log-forward /usr/local/bin/
COPY driver/forward-logs /usr/local/bin/
ENTRYPOINT ["forward-logs", "kv-server"]
```

Put the wrapper in front of whatever the image ran before. If the base image has its own `ENTRYPOINT`, keep it after `forward-logs`, and restate the base image's `CMD`, which setting `ENTRYPOINT` drops. For a base with `ENTRYPOINT ["docker-entrypoint.sh"]` and `CMD ["postgres"]`, use `ENTRYPOINT ["forward-logs", "docker-entrypoint.sh"]` and `CMD ["postgres"]`. Forward a client container's logs (`references/patterns/stateful-clients.md`) the same way.

In `docker-compose.yaml`, mount a `logs` volume in the driver and in every container that forwards, and set the forwarder's variables on each forwarding service. Give each one a `hostname` equal to its `container_name`, as the harness does for the driver:

```yaml
kv1:
  container_name: kv1
  hostname: kv1
  environment:
    LOG_FORWARD_SOCKET: /logs/driver.sock
    LOG_FORWARD_MATCH: msg=raft-state
  volumes: [logs:/logs]
driver:
  volumes: [logs:/logs]
volumes:
  logs:
```

## 3. Parse the lines

Start the receiver in `main` before the "Report setup complete" step in `references/workload/driver.md`, so node states learned during setup are in the root snapshot. It binds `/logs/driver.sock`, after removing a stale one, and makes it writable by any user, since forwarders may run as any user. The kernel queues only a few datagrams, so one thread does nothing but receive, and hands each datagram over a bounded channel, of about 1000, to a thread that parses and records it. A full channel drops the datagram, which shows up as a `seq` gap.

The node states, `NodeStates`, hold each container's last `boot` and `seq`, and its current boot's latest state. For the key-value store in `references/workload/driver.md`, if its nodes log `msg=raft-state term=3 role=leader commit=42`:

```text
record(line):
  if same boot as this container's last line:
    assert_always seq == last seq + 1   "the driver receives every forwarded log line"
  else:
    forget this container's state               # a new process
  if the line parses as a raft-state:
    assert_reachable                    "the driver reads a node's state from its logs"
    guarantee checks on node state go here      # see section 4
    store it as the container's latest state
    once active, exploration assertions over every container's latest state:
      assert_sometimes two nodes disagree on the term
      assert_sometimes_greater_than the leader's commit minus the furthest-behind node's, 10
```

The exploration assertions wait for the `active` flag, set once `main` sees `/workload-active`, or the first election would satisfy them in every run.

`the driver receives every forwarded log line` fails when a queue overflowed, or the forwarder dropped a line too long for a datagram. That is a problem in the workload, not the system: forward fewer lines, or make `record` cheaper.

## 4. Check guarantees on node state

Guarantee checks on node state, such as at most one leader per term, go in `record` as each line arrives: see "Node state, from forwarded logs" in `references/properties/checks.md`.

## 5. Rules

- **Handle lines as they arrive,** in the receiving thread, not in rules. A rule runs late and misses short-lived states.
- **Keep only current state.** Keep each node's latest state and what the checks need, never the lines or a history of states, so memory stays bounded however long the run. To assert on a transition, keep the previous value.
- **Parse cheaply,** and before taking the node-state lock.
- **Share state both ways.** Rules read the node states, for example to send reads to a lagging follower. Give the receiving thread the model too, so assertions that combine the logs with the model are checked when the line arrives. Never hold a model lock and the node-state lock at once: copy what you need from one, release it, then take the other.
- **Don't depend on arrival order across containers.** One container's lines arrive in `seq` order, but a paused container's arrive late. The latest state of several nodes is a mix of times: use it only for `assert_sometimes` assertions.
- **Mark combinations worth exploring from,** with exploration assertions (`references/properties/assertions.md`): a leader change while a follower lags, a node rejoining with a stale term. Use rich assertions when there's a distance to the state ("Rich assertions" in `references/properties/assertions.md`).
- **Assert that every kind of line you parse arrives,** with an `assert_reachable` per kind. Otherwise a changed format or a disabled log level looks like a quiet system.

## Checking it

- **Locally,** every kind of line you parse arrives, its `assert_reachable` is met in the local loop (`references/workload/local-loop.md`), and `the driver receives every forwarded log line` holds. Check it under a burst: restart every system container at once while the workload runs.
- **In a short run,** the exploration assertions on node state are reached.
