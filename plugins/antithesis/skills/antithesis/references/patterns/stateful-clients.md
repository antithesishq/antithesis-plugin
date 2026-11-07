# Stateful clients

Client libraries often hold part of the protocol: retry numbering, sessions, leases, transactions, multi-step commits, cached routing, batching. The servers' recovery code for these runs only when a client fails partway through. A driver that speaks the protocol itself never runs the library's own retry and recovery code. So this pattern runs the real library in client containers, faulted like the servers, and has the driver tell them what to do.

## How it fits together

- **A client program in each client container.** It is a small, long-running program in the library's language. It holds one client and runs the operations the driver sends it.
- **A Unix socket in a shared volume.** The driver and every client container mount one volume, `/clients`. Each client program listens on `/clients/<hostname>.sock`, and the driver connects to each.
- **The socket is never faulted.** Antithesis doesn't fault Unix sockets in shared volumes, so the driver can always reach a running client, however heavily the client is faulted. A paused client answers late. The driver never closes a connection, so a connection closes only when the client's process exits. The faults still land where they should: on the client's connections to the servers, and on its process.

## The protocol

The driver and the client exchange [JSON-RPC 2.0](https://www.jsonrpc.org/specification) messages over the socket, one JSON object per line. Every language has JSON and Unix sockets, so no library is needed.

The driver sends one request per operation. The client answers each request on the same connection when its operation completes, in the order operations complete, not the order they arrived:

```json
{"jsonrpc": "2.0", "id": 17, "method": "put", "params": {"key": 3, "value": 42}}
{"jsonrpc": "2.0", "id": 18, "method": "get", "params": {"key": 3}}
{"jsonrpc": "2.0", "id": 18, "result": {"outcome": "ok", "value": 42}}
{"jsonrpc": "2.0", "id": 17, "result": {"outcome": "unknown", "error": "request timed out"}}
```

Every `result` has an `outcome`:

- **`ok`:** the library reported success. Any returned value goes in `value`, as plain JSON.
- **`failed`:** the library reported an error that, by its documentation, means the operation didn't take effect, such as a rejected precondition.
- **`unknown`:** any other error, such as a timeout, a lost connection, or an error whose effect the documentation doesn't settle. When unsure, use `unknown`.

A JSON-RPC `error`, instead of a `result`, means the client couldn't run the request at all: an unknown method (code -32601), missing params (-32602), or a value JSON can't hold (-32603). That is a bug in the workload, so the driver checks for it with `assert_unreachable!`.

**Methods.** Add one method per library operation in the surface you mapped, named after it, with the inputs the driver drew as its params. Add `health`, which answers `ok` without touching the servers. For long-lived library objects such as sessions, transactions, locks and cursors, have the method that creates one return a handle, such as `{"outcome": "ok", "value": {"txn": 5}}`. Later methods take the handle as a param. The client keeps the objects per connection, and answers a handle it doesn't know as `failed`.

**Events.** The library may also report things the driver didn't just ask for: a watch firing, a subscription message, a lease lost. The client sends each one as a JSON-RPC notification, which has no `id`: `{"jsonrpc": "2.0", "method": "event", "params": {"kind": "watch", "key": 3}}`.

## The client program

A small program in the library's language:

- **Bind the socket first,** removing any stale socket file a killed process left behind, then accept connections in a loop. Build the library's client on first use, so `health` answers before the servers are ready: the driver waits for `health` before admin setup creates what an eager client may need.
- **Run each request concurrently** on one shared client, so batching and pipelining happen, and write each response when its operation completes, one whole line at a time.
- **Turn every library result into an outcome.** Read the params before calling the library, so a missing param is a protocol error and an error the library raises is an outcome. Convert returned values to plain JSON, and if one still can't be encoded, answer with a protocol error rather than not at all. Every request gets an answer, however late.
- **Configure the library as production users would,** including its own timeouts. Randomness and checks belong in the driver.
- **Exit on SIGTERM.** As the container's main process, PID 1, the program ignores SIGTERM unless it handles it, so a graceful stop would end in a kill.
- **Run it with no restart policy,** like every container: Antithesis restarts killed and stopped containers itself, and a policy would bring them back early, cancelling the fault. Run several client containers, since many bugs sit between clients.
- **Add exploration assertions to the library's code,** for states inside a single library call ("Exploration assertions" in `references/properties/assertions.md`).
- **Instrument the program** (`references/workload/instrumentation.md`). Client containers count as system services for local coverage (`references/workload/local-loop.md`).
- **Add `socat` or another JSON-RPC tool to the image,** so a debug session (`references/debug/MODULE.md`) can drive the client from a shell. Its connection is new and can't use the driver's handles, so create any handle it needs first.

## The driver

Antithesis searches for the timings that break a workload, so it will find a client that hangs for longer than any fixed timeout: paused for minutes, or stuck inside one library call indefinitely. So the driver treats every client as flaky, and follows one rule: **a fixed timeout may make the driver check less, but never stall it or cause a false failure.**

- **A rule never blocks on a client.** It waits for an answer only up to `TIMEOUT`, to pace itself. Requests go out through a writer thread per connection, so a paused client blocks only its own writer.
- **The driver never closes a connection.** The socket is never faulted, so a connection closes only when the client's process exits. A closed connection is how the driver learns a client restarted, and the only time it gives up on that client's operations.
- **Each client has at most `MAX_IN_FLIGHT` operations outstanding,** for example 16. A full client, whether paused, slow or hung, gets no more work until it answers. Rules keep driving the other clients.

The driver keeps one connection to each client in `CLIENTS` (`client1,client2`), made on first use, and gives each connection a new generation number. A rule records an operation in the model as sent, then calls:

```text
call(client, generation?, op):
  conn = the client's connection, connecting if there is none
  if no conn, or generation given and conn's differs, or conn has MAX_IN_FLIGHT outstanding:
    model.not_sent(op); return NotSent
  add op to conn's outstanding; queue its request line on conn's writer
  wait up to TIMEOUT for its outcome:
    arrived -> Done(outcome)
    conn closed first -> Lost
    otherwise -> Pending

reader thread, per connection:
  for each line:
    notification -> model.event(client, params)
    response -> assert_unreachable! if it's a JSON-RPC error
                model.complete(op, outcome)        # records and checks it, however late
                remove op from outstanding, and wake its rule if it's still waiting
  at close: forget the connection, then model.lost(client, generation, its outstanding ops)
```

Never hold a model lock while sending or waiting.

### The model

- **Each rule draws which client acts.** Bugs between clients need several of them acting on the same keys, locks or transactions. A full or unreachable client returns `NotSent` at once, so drawing one costs nothing.
- **Keep a handle with its generation,** and pass the generation to `call` for every operation on it, so it can only reach the process that issued it. `NotSent` or `Lost` means the handle is gone.
- **Check outcomes in `complete`, not in the rule,** with the outcome's arrival time as the operation's end. A guarantee check in the rule would miss exactly the outcomes that faults delay.
- **An outstanding write stays possible until its outcome arrives or its client restarts,** however long that takes: the library may still be retrying it. `MAX_IN_FLIGHT` bounds how many there are.
- **An outstanding read stops pinning the model after `ABANDON`,** for example 30 s. Pruning must not forget what an outstanding read may still return, so a hung read would keep the whole history forever. Once a read is older than `ABANDON`, prune past it, and when its answer arrives, skip the checks that need the pruned history.
- **A closed connection means the client restarted.** In `lost`, everything outstanding on it gets an unknown outcome, and the model forgets that client's sessions, locks, open transactions and handles. A write lost this way may still land soon, from a request already on the wire, so start its `AMBIGUITY_WINDOW` at the restart. A paused client, not restarted, may still think it holds a lock that has since expired.
- **Under `high_availability`, mark restarts:** `assert_reachable!("a client restarts", ...)` in `lost`, once the workload is active, so restarts during setup don't count. Under `resilient`, nothing kills a client, so leave it out.
- **Actions always go through the clients.** A direct connection to the servers is a client that never fails. Use one only for the startup waits, admin setup, and read-only checks in an eventually.

**Startup.** In step 2 of "Starting up" in `references/workload/driver.md`, also wait until every client answers `health`, so a client that can't start fails setup loudly.

**Eventually.** A hang that outlasts the faults is a bug, in the library or the system. Once faults stop and the servers recover, wait, up to the eventually's deadline, until every client has nothing outstanding and answers a real request. Assert it: `every client answers once faults stop`, with each client's outstanding operations and their ages in the details.

## The harness

Add one service per client container to `docker-compose.yaml` (`references/workload/harness.md`), and mount the `clients` volume in each and in the driver:

```yaml
client1:
  container_name: client1
  hostname: client1
  platform: linux/amd64
  build:
    context: .
    dockerfile: client/Dockerfile
  image: client:latest
  environment:
    KV_URLS: http://kv1:8000,http://kv2:8000
  volumes: [clients:/clients]
driver:
  environment:
    CLIENTS: client1,client2
  volumes: [clients:/clients]
volumes:
  clients:
```

The driver keeps `KV_URLS` for its readiness checks, admin setup and eventually reads. If a client program runs as a non-root user, create `/clients` owned by that user in its Dockerfile, as for any shared volume. Exclude only the driver from faults: the client containers are there to be faulted.

## Checking it

- **Locally,** every client answers `health`, both from the driver and from its own shell with the JSON-RPC tool, `a client can't run a request` is never hit, and every method reaches `ok` sometimes. `failed` and `unknown` mostly need faults. After `docker compose restart client1` while the workload is active, `a client restarts` is reached. After `docker compose pause client1` for longer than `ABANDON`, then `unpause`, the workload carries on through the other clients, and client1 drains.
- **In a short run** under `high_availability`, clients restart and get partitioned from the servers, `a client restarts` passes, and `every client answers once faults stop` passes.
