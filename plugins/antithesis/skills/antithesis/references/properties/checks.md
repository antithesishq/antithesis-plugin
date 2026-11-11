# Writing the check

Choose each assertion, and write its message and details, following `references/properties/assertions.md`.

## Responses, against the model

Check each response against every outcome consistent with what overlapped it, not only the latest write. A request with an unknown outcome may still take effect, now or later. If the system orders operations itself (log positions, sequence numbers), check against that order. With the stateful-clients pattern, check in the model's `complete`, with the time the outcome arrived as the operation's end.

For the key-value store in `references/workload/driver.md`, which promises linearizable reads, a read that ran from `start` to `end` may return:

```text
a value v  if v's write was sent before end, and wasn't overwritten before start
nothing    if no write had been acknowledged before start
```

Add that to `KeyHistory` as `may_return(got, start, end)`, and assert it in the get rule: `assert_always(may_return(...), "a read returns the latest acknowledged write or one that overlapped it", ...)`, with the node, key and value read in the details.

## Node state, from forwarded logs

With the log-forwarding pattern (`references/patterns/log-forwarding.md`), check each line as it arrives, in `NodeStates::record`. One container's lines arrive in order, but lines from different containers don't, so check over everything seen, or over one container's lines, never over the latest state of several nodes. Check during setup too, ahead of the `active` guard. Some examples, for nodes that log `msg=raft-state term=3 role=leader commit=42`:

- **At most one leader per term:** remember the first container seen as leader of each term, and assert every later leader of that term is the same one. Never forget a term: a node can claim an old term late, which is exactly the bug.
- **A node's commit index never goes backwards:** compare each line with the same container's previous line in this boot. It needs only one node, so put a check like it in the node's own code instead, if you can change that code.
- **Nodes apply only values the workload wrote:** if nodes also log `msg=apply key=3 value=17`, add `msg=apply` to `LOG_FORWARD_MATCH`, and assert each applied value is below the driver's `next_value`. Values are drawn in order before they're sent, so every value the workload wrote is below it. Don't check against the key histories, which forget old writes that a lagging node may still apply. Parse a malformed value as one the workload never wrote, so the check reports it.

## After faults stop

Guarantees that hold only once faults stop fail falsely during faults. Check them in an eventually (`references/workload/driver.md`), after it waits for the nodes:

- **Recovery:** assert `assert_always` that the system recovered, such as every node serving requests again. This is the eventually's recovery assertion: when it passes, the system recovered at least once. If it fails, skip the rest.
- **Durability:** with every node serving and no rule running, read every key and assert `assert_always` that `may_return` holds: "acknowledged writes survive once faults stop".
