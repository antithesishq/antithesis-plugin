# Write the driver

The driver is a hegel concurrent state machine run from `#[hegel::main]`. Each `#[rule]` is one action: it draws its inputs, sends a request, and records the outcome in the model. Hegel runs the rules on several worker threads, in rounds. The next round starts only when every worker is done, so one slow rule stalls them all.

Dependencies: `hegeltest` with `features = ["static-engine"]`, and `antithesis_sdk`.

## Starting up

`main` does this, in order:

1. **Call `antithesis_init()`.**
2. **Start the UDP receivers:** the log receiver on 7777 (`references/workload/system-logs.md`) and, with client containers, the completion-event receiver on 7778. Started first, they hear every line sent after the driver starts, and node states learned during setup are in the root snapshot. A node can log before the driver starts, so don't rely on its first lines.
3. **Wait until every node is up:** it answers requests, even if only to say the cluster isn't formed yet. An open port isn't enough. With client containers, also wait for every client program's health request, so a client that can't start fails setup loudly.
4. **Run admin setup, if any:** creating the cluster, a schema, users, buckets or topics, when that's easier here than in the system's containers. Use a direct connection to the servers (`references/workload/clients.md`). Retry each until it succeeds, and treat "already exists" as success, since a retried request may have taken effect.
5. **Wait until the system serves the workload's requests:** a read answers, the cluster has a leader, all members joined.
6. **Report setup complete** with `antithesis_sdk::lifecycle::setup_complete(&details)`. Antithesis takes the first setup complete from any process, so remove any other reporter, such as one in the system's containers.
7. **Wait for `/workload-active`,** polling every 100 ms; this wait is outside the state machine, so a sleep loop is fine. The driver container's `first_` command creates it (`references/workload/harness.md`). Then set the `active` flag, which turns on the exploration assertions in the log thread; guarantee checks there run from boot ("Parse the lines" in `references/workload/system-logs.md`).
8. **Mark the start** with `assert_reachable!("the workload starts", ...)`.
9. **Run the state machine** forever.

Steps 3 to 5 retry rather than sleep a fixed time, and print what they're waiting for, or why a request failed, whenever that changes, so a setup timeout shows where it stopped without flooding the log. They have no deadline of their own: `--setup-timeout` bounds them in Antithesis, and `snouty validate --timeout` locally. They count toward setup time.

Nothing before step 9 draws from hegel: every timeline branches from a snapshot taken during step 7, so all randomness comes after it. The example's `main` below does all of this.

### Shared volumes for out-of-band facts

When the driver can't tell over the network that a node is ready, or needs something a node generates (credentials, certificates, a node ID, a "migration done" marker), share a named volume between that node's container and the driver, and have the node write a file there (wiring in `references/workload/harness.md`). Never use it to observe what the workload tests: a volume isn't subject to network faults. A marker survives container restarts, so it can be stale after one; check a node's recovery over the network, never by its marker.

## Example: a replicated key-value store

This drives a replicated key-value store with no client library. It serves `PUT /k/<key>` and `GET /k/<key>` on any node, and promises linearizable reads.

Left out below: the HTTP client (`put`, `get`), reading the node list from `KV_URLS`, `draw_target` (a node and one of `KEYS` keys), `wait_until_up` and `wait_until_serving` (steps 3 and 5), `wait_for_nodes` ("Quiet periods"), and `KeyHistory`'s `sent`, `acked` and `overlaps` (a write was in flight during the read). `acked` finds its write by value, since pruning may have moved it. Each wait bounds its requests by `TIMEOUT`, with about 1 s between passes.

```rust
/// Short, so a request to an unreachable node costs a moment, not a stalled round.
const TIMEOUT: Duration = Duration::from_millis(1000);
/// How long a write with an unknown outcome stays possible. Systems apply such writes
/// soon or never, and keeping them forever would let the check accept almost anything.
const AMBIGUITY_WINDOW: Duration = Duration::from_secs(60);
/// Created by the driver container's `first_` command (harness.md).
const WORKLOAD_ACTIVE: &str = "/workload-active";

/// One write to a key. `acked` is when the system acknowledged it, or `None` if we never
/// learned the outcome, in which case it may still take effect.
struct Write { value: u32, sent: Instant, acked: Option<Instant> }

/// Every write sent to one key.
#[derive(Default)]
struct KeyHistory { writes: Vec<Write> }

impl KeyHistory {
    /// A write is overwritten before time `t` if another write was sent after it was
    /// acknowledged, and was itself acknowledged before `t`.
    fn overwritten_before(&self, w: &Write, t: Instant) -> bool {
        let Some(w_acked) = w.acked else { return false }; // it could still land later
        self.writes.iter().any(|o| o.sent > w_acked && o.acked.is_some_and(|a| a < t))
    }

    /// Forgets writes no read can return any more, so checks stay cheap in long runs: writes
    /// overwritten more than two timeouts ago (no read still in flight started before that),
    /// and unacknowledged writes older than `AMBIGUITY_WINDOW`.
    fn prune(&mut self) {
        let now = Instant::now();
        let Some(horizon) = now.checked_sub(2 * TIMEOUT) else { return };
        let keep: Vec<bool> = self.writes.iter().map(|w| match w.acked {
            None => now.duration_since(w.sent) < AMBIGUITY_WINDOW,
            Some(_) => !self.overwritten_before(w, horizon),
        }).collect();
        let mut keep = keep.into_iter();
        self.writes.retain(|_| keep.next().unwrap());
    }
}

struct Driver {
    nodes: Vec<String>,
    http: ureq::Agent,
    keys: Vec<Mutex<KeyHistory>>,
    next_value: AtomicU32,
}

// Locks are held only to update or check a key's history, never during a request, so
// requests to the same key overlap.
#[hegel::concurrent_state_machine]
impl Driver {
    #[rule(group = "ops", weight = 2.0)]
    fn put_value(&self, tc: TestCase) {
        let (node, key) = self.draw_target(&tc);
        // Unique values make every read attributable to exactly one write.
        let value = self.next_value.fetch_add(1, Ordering::Relaxed);
        self.keys[key].lock().unwrap().sent(value, Instant::now());
        let ok = self.put(node, key, value).is_ok();
        let acked_at = Instant::now();
        let mut history = self.keys[key].lock().unwrap();
        if ok {
            history.acked(value, acked_at);
        } // A failed write may still land, so it stays unacknowledged.
        history.prune();
    }

    #[rule(group = "ops", weight = 3.0)]
    fn get_value(&self, tc: TestCase) {
        let (node, key) = self.draw_target(&tc);
        let start = Instant::now();
        // `get` turns a 404 into `None`, and an unparsable body into a value no write produced.
        let Ok(got) = self.get(node, key) else { return }; // a failed read tells us nothing
        let end = Instant::now();
        let history = self.keys[key].lock().unwrap();
        assert_sometimes!(got.is_some(), "read finds a written key", &json!({"key": key}));
        assert_sometimes!(history.overlaps(start, end), "a read overlaps a write to the same key", &json!({"key": key}));
    }
}

#[hegel::main(phases = [hegel::Phase::Generate])]
fn main(tc: TestCase) {
    antithesis_init();
    let active = Arc::new(AtomicBool::new(false));
    let driver = Driver { /* ..., node states built with NodeStates::new(active.clone()) */ };
    // Start the log receiver here, before waiting, sharing the driver's node states
    // (references/workload/system-logs.md).

    driver.wait_until_up();
    // driver.admin_setup(); // optional: create the cluster, a schema, users, ... (retried, idempotent)
    driver.wait_until_serving();
    antithesis_sdk::lifecycle::setup_complete(&json!({"nodes": driver.nodes}));

    while !std::path::Path::new(WORKLOAD_ACTIVE).exists() {
        std::thread::sleep(Duration::from_millis(100));
    }
    active.store(true, Ordering::Relaxed);
    assert_reachable!("the workload starts", &json!({}));

    hegel::stateful::machine(driver)
        .steps(i64::MAX)
        .max_concurrency(4)
        .run_concurrent(tc);
}
```

## Rules

- **Run forever.** Call `.steps(i64::MAX)`. The default stops after 50 rounds, and the binary exits. Don't use `tc.repeat`.
- **Use Antithesis SDK assertions, never panics.** Put the values you'd need to debug in the details.
- **Generate only.** Keep `phases = [hegel::Phase::Generate]` on `#[hegel::main]`.
- **Cover the surface you mapped.** Draw options; don't hard-code the common case.
- **Let requests contend.** Don't serialize requests per key to keep the model simple. Record when each request was sent and when its outcome arrived, so an assertion can allow every outcome consistent with what overlapped it. If the system orders operations itself (log positions, sequence numbers), record that order too.
- **Record unknown outcomes as unknown.** A request that timed out or lost its connection may or may not have taken effect, now or later.

## Driving client containers

With client containers (`references/workload/clients.md`), also:

- **Each rule draws which client acts.** Bugs between clients need several of them acting on the same keys, locks or transactions.
- **Outcomes arrive as events.** Tag each operation with an ID, and wait for the response only up to the usual short timeout. A background thread receives the completion events on UDP port 7778 and resolves each operation in the model as its event arrives. An operation without an event stays unknown until its client's boot changes or the ambiguity window passes.
- **Bursts are cheap.** A rule can send several operations to one client without waiting for their responses, which gets the library batching beyond what the worker count allows.
- **A changed boot identifier means the client restarted.** Everything outstanding on its old boot gets an unknown outcome, and the model forgets that client's sessions, locks and open transactions. Unknown includes what the client believed: a client that was paused, not restarted, may still think it holds a lock that has since expired. Put a reachable assertion where the driver notices a new boot, once `active` is set, so a restart during setup doesn't count.
- **An unreachable client is normal.** It may be paused or mid-restart. Treat commands to it as unknown, and keep driving the other clients.
- **Actions always go through the clients.** The few uses of a direct server connection are in `references/workload/clients.md`.

## Keep rules fast

- Use short timeouts. Give operations that are slow by design their own.
- Don't sleep or poll in a rule. Record what you expect, and check it in a later rule. The one exception is a quiet period, which waits for recovery on purpose.
- Keep long-lived interactions (streams, sessions, transactions) in the driver's state, across rules.
- Run blocking operations (watches, long-polls, blocking pops) on a background thread. Record the result in the driver's state, and check it in a later rule. Bounded retries that mirror a real client's are fine inside a rule.

**Weight actions toward what's hard to reach,** so options and rare interactions happen many times in every timeline.

**Use `#[invariant(always_run)]`.** With `.steps(i64::MAX)`, a plain `#[invariant]` effectively never runs. An `always_run` invariant runs after every round, while no rules run, and every round waits for it.

## Guiding exploration

Add exploration assertions to the driver, following "Exploration assertions" in `references/properties/assertions.md`.

## Choosing how often things happen

- **Groups control overlap, not frequency.** Each round hegel picks one group, and every worker runs only its rules. Use separate groups only for rules that must never overlap. Groups can't be weighted.
- **Weights are a hint** for the mix within a group, not a guarantee.
- **Explicit draws set exact probabilities.** Use `tc.draw(gs::weighted_booleans(p))`, or a phase in the driver's state, when a rate matters.

Put a rare action in the main group behind a rare draw. A group of its own would get as many rounds as any other. If it must not overlap other operations, run it from an `always_run` invariant behind a rare draw, as the quiet period does.

## Quiet periods

A quiet period pauses faults so the system can recover. Guarantees that hold only once faults stop, like every node serving again or acknowledged writes being readable, are checked there.

Run the whole quiet period inside one call of an `#[invariant(always_run)]`. No rule runs until it returns, so the checks see a quiet system, and it can wait for recovery. A per-round `weighted_booleans` draw starts quiet periods at a rate you choose. Pause faults with `ANTITHESIS_STOP_FAULTS <seconds>` for longer than the whole check takes; faults resume on their own afterwards. For the example above:

```rust
/// Chance per round of starting a quiet period. Measure rounds per second locally,
/// then pick this for roughly one quiet period every few minutes of a timeline.
const P_QUIET: f64 = 1.0 / 3000.0;
const QUIET: Duration = Duration::from_secs(60);    // how long faults stay paused
const DEADLINE: Duration = Duration::from_secs(45); // every node must serve by then

#[invariant(always_run)]
fn quiet_period(&self, tc: TestCase) {
    if !tc.draw(gs::weighted_booleans(P_QUIET)) {
        return;
    }
    if let Some(bin) = std::env::var_os("ANTITHESIS_STOP_FAULTS") {
        let _ = std::process::Command::new(bin).arg(QUIET.as_secs().to_string()).status();
    }
    // Restarted containers take a while to come back. Retry each node until it serves,
    // or until DEADLINE. With client containers, also send a real request through each,
    // so a client wedged after faults doesn't count as recovered.
    let healthy: Vec<bool> = self.wait_for_nodes(DEADLINE);
    assert_sometimes!(!healthy.contains(&false), "the system recovered after faults stopped", &json!({"healthy": healthy}));
}
```

`wait_for_nodes` and `wait_until_serving` can share one per-node check; the quiet period stops at `DEADLINE`.

Clock faults continue during a pause, so allow for clock jumps. To test a quiet period locally, set its probability to 1.

For the rest of hegel's API, see <https://hegel.dev/> (Rust: <https://docs.rs/hegeltest/latest/hegel/>).
