# Writing the check

Choose each assertion, and write its message and details, following `references/properties/assertions.md`.

## Responses, against the model

Check each response against every outcome consistent with what overlapped it, not only the latest write. A request with an unknown outcome may still take effect, now or later. If the system orders operations itself (log positions, sequence numbers), check against that order.

For the key-value store in `references/workload/driver.md`, which promises linearizable reads, add to `KeyHistory`:

```rust
/// A read that ran from `start` to `end` may return:
/// - a value, if its write was sent before the read ended and wasn't overwritten before
///   the read started;
/// - nothing, if no write had been acknowledged before the read started.
fn may_return(&self, got: Option<u32>, start: Instant, end: Instant) -> bool {
    match got {
        None => !self.writes.iter().any(|w| w.acked.is_some_and(|a| a < start)),
        Some(v) => self.writes.iter().any(|w| w.value == v && w.sent < end && !self.overwritten_before(w, start)),
    }
}
```

and to `get_value`, once it has the history:

```rust
assert_always!(
    history.may_return(got, start, end),
    "a read returns the latest acknowledged write or one that overlapped it",
    &json!({"node": node, "key": key, "got": got})
);
```

## Node state, from the logs

Check as each line arrives, in `NodeStates::record` (`references/workload/system-logs.md`). Lines from different nodes arrive in any order, so check over everything seen, or over one node's lines in `seq` order, never over the latest state of several nodes. Add a `leaders: HashMap<u64, String>` field, the first leader seen in each term, and initialize it to `HashMap::new()` in `NodeStates::new`. Put the leader check at the top of `record`, and the commit check inside its out-of-order check. Both run before the `active` guard, so they check boot too:

```rust
if s.role == "leader" {
    let first = self.leaders.entry(s.term).or_insert_with(|| node.clone());
    assert_always!(*first == node, "at most one leader per term",
        &json!({"term": s.term, "leaders": [first, &node]}));
}
if let Some(prev) = self.latest.get(&node).filter(|p| p.boot == s.boot) {
    if s.seq <= prev.seq {
        return; // arrived out of order
    }
    assert_always!(s.commit >= prev.commit, "a node's commit index never goes backwards",
        &json!({"node": node, "from": prev.commit, "to": s.commit}));
}
```

If nodes also log `msg=apply key=3 value=17`, check each applied value as the line arrives. Share the driver's `next_value` with the thread as an `Arc<AtomicU32>`. Values are drawn in order before they're sent, so every value the workload wrote is below it:

```rust
assert_always!(value < next_value.load(Ordering::Relaxed), "nodes apply only values the workload wrote",
    &json!({"node": node, "value": value}));
```

Check against `next_value`, not the key histories, which forget old writes that a lagging node may still apply. Parse a malformed value as one the workload never wrote, so the check reports it.

## After faults stop

Guarantees that hold only once faults stop fail falsely during faults. Check them in the quiet period (`references/workload/driver.md`), after it waits for the nodes. The recovery check below replaces the quiet period's `assert_sometimes!` on recovery: when it passes, the system recovered at least once.

```rust
let recovered = !healthy.contains(&false);
assert_always!(recovered, "every node serves requests again once faults stop", &json!({"healthy": healthy}));
if !recovered {
    return;
}
// Every node serves and no rule is running: check the model.
for key in 0..KEYS {
    let start = Instant::now();
    let Ok(got) = self.get(0, key) else { return }; // a failed read tells us nothing
    let end = Instant::now();
    assert_always!(
        self.keys[key].lock().unwrap().may_return(got, start, end),
        "acknowledged writes survive once faults stop",
        &json!({"key": key, "got": got})
    );
}
```
