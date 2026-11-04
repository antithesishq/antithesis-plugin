# Write the driver

The driver is a hegel concurrent state machine run from `#[hegel::main]`. Each `#[rule]` is one action: it draws its inputs, sends a request, and records the outcome in the model. Hegel runs the rules on several worker threads, in rounds. The next round starts only when every worker is done, so one slow rule stalls them all.

Dependencies: `hegeltest` with `features = ["static-engine"]`, and the latest `antithesis_sdk`. Read its API following `references/workload/sdk.md`.

## Starting up

`main` does this, in order:

1. **Call `antithesis_init()`.**
2. **Wait until every node is up:** it answers requests, even if only to say the cluster isn't formed yet. An open port isn't enough.
3. **Run admin setup, if any:** creating the cluster, a schema, users, buckets or topics, when that's easier here than in the system's containers. Retry each until it succeeds, and treat "already exists" as success, since a retried request may have taken effect.
4. **Wait until the system serves the workload's requests:** a read answers, the cluster has a leader, all members joined.
5. **Report setup complete** with `antithesis_sdk::lifecycle::setup_complete(&details)`. Antithesis takes the first setup complete from any process, so remove any other reporter, such as one in the system's containers.
6. **Wait for `/workload-active`,** polling every 100 ms; this wait is outside the state machine, so a sleep loop is fine. The driver container's `first_` command creates it (`references/workload/harness.md`).
7. **Mark the start** with `assert_reachable!("the workload starts", ...)`.
8. **Run the state machine** forever.

A pattern you adopted (`references/patterns/MODULE.md`) may add to these steps.

Steps 2 to 4 retry rather than sleep a fixed time, and print what they're waiting for, or why a request failed, whenever that changes, so a setup timeout shows where it stopped without flooding the log. They have no deadline of their own: `--setup-timeout` bounds them in Antithesis, and `snouty validate --timeout` locally. They count toward setup time.

Nothing before step 8 draws from hegel: every timeline branches from a snapshot taken during step 6, so all randomness comes after it.

### Shared volumes for out-of-band facts

When the driver can't tell over the network that a node is ready, or needs something a node generates (credentials, certificates, a node ID, a "migration done" marker), share a named volume between that node's container and the driver, and have the node write a file there (wiring in `references/workload/harness.md`). Never use it to observe what the workload tests: a volume isn't subject to network faults. A marker survives container restarts, so it can be stale after one; check a node's recovery over the network, never by its marker.

You can also use a shared volume to help setup the system. A oneshot service that writes configuration files, credentials, etc to a shared volume, which all the other services depend on can replace the need to do everything statically in Dockerfiles.

## Example: a replicated key-value store

Take a replicated key-value store with no client library. It serves `PUT /k/<key>` and `GET /k/<key>` on any node, and promises linearizable reads. Its driver has two rules, a put and a get, each aimed at a drawn node and one of a few keys, so requests to the same key overlap often.

The model is a `KeyHistory` per key: every write sent to it, with when it was sent and, if the system acknowledged it, when.

- **Every put writes a unique value**, drawn from a counter, `next_value`, so every read is attributable to exactly one write.
- **A put records its write as sent before sending it,** then records the acknowledgement. A put that fails or times out stays unacknowledged: it may still land.
- **A get records when it started and ended,** and judges what it read against the writes that overlapped it ("Responses, against the model" in `references/properties/checks.md`). A failed get tells you nothing.
- **Locks are held only to update or read a key's history,** never during a request, so requests to the same key overlap.
- **The history is pruned** after each put, so checks stay cheap in a long run:

  ```text
  overwritten_before(w, t) = w was acknowledged, and some write sent after w's acknowledgement was itself acknowledged before t
  prune:
    drop each acknowledged write overwritten before now - 2 * TIMEOUT
      (no read still in flight started earlier)
    drop each unacknowledged write sent more than AMBIGUITY_WINDOW ago
  ```

  `TIMEOUT` is short, about 1 s, so a request to an unreachable node costs a moment, not a stalled round. `AMBIGUITY_WINDOW`, about 60 s, is how long a write with an unknown outcome stays possible: systems apply such writes soon or never, and keeping them forever would let the check accept almost anything.

Exploration assertions on the rules mark what's worth reaching, such as a read that finds a written key, and a read that overlaps a write to the same key.

## Rules

- **Run forever.** Call `.steps(i64::MAX)`. The default stops after 50 rounds, and the binary exits. Don't use `tc.repeat`.
- **Use Antithesis SDK assertions, never panics.** Put the values you'd need to debug in the details.
- **Generate only.** Keep `phases = [hegel::Phase::Generate]` on `#[hegel::main]`.
- **Let requests contend.** Don't serialize requests per key to keep the model simple. Record when each request was sent and when its outcome arrived, so an assertion can allow every outcome consistent with what overlapped it. If the system orders operations itself (log positions, sequence numbers), record that order too.
- **Record unknown outcomes as unknown.** A request that timed out or lost its connection may or may not have taken effect, now or later.
- **Keep memory bounded.** Keep only what the checks need, and prune it as `KeyHistory` does, so long runs don't grow without limit.

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

Run the whole quiet period inside one call of an `#[invariant(always_run)]`. No rule runs until it returns, so the checks see a quiet system, and it can wait for recovery. Each round, a `weighted_booleans` draw starts one at a rate you choose: measure rounds per second locally, and aim for about one every few minutes of a timeline. Then:

1. Pause faults by running `$ANTITHESIS_STOP_FAULTS <seconds>`, for longer than the whole check takes. Faults resume on their own afterwards.
2. Wait, up to a deadline, until every node serves requests again. Restarted containers take a while to come back. Step 2 of "Starting up" can share this per-node check.
3. Check what must hold once faults stop. At least, assert that the system recovered.

Clock faults continue during a pause, so allow for clock jumps. To test a quiet period locally, set its probability to 1.

For the rest of hegel's API, see <https://hegel.dev/> (Rust: <https://docs.rs/hegeltest/latest/hegel/>).
