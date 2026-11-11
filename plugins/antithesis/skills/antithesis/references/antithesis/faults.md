# Faults

Antithesis injects faults throughout every timeline, interleaved with the workload. This page says what each fault does to the system, how it ends, and how it interacts with a pause. For more, read these pages with `snouty docs show <path>`:

- `/docs/product/writing_tests/controlling_faults/`
- `/docs/product/writing_tests/controlling_faults/fault_types/`
- `/docs/product/writing_tests/controlling_faults/pause_faults/`

## Scope

Faults act on nodes: containers in Docker Compose, pods in Kubernetes. Everything in a node shares its fate, so two services in one container never see a network fault between them. Put services in separate containers to fault them independently. Three faults act on the whole machine instead: clock skips, CPU modulation and thread pausing.

## Fault tolerance levels

`--fault-tolerance` picks which faults run:

| Level               | Faults                                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `none`              | None.                                                                                                                     |
| `resilient`         | Baseline latency, `Slowed` and `Jammed` clogs, node pauses, node throttling, CPU modulation, thread pausing, clock skips. |
| `high_availability` | Everything in `resilient`, plus partitions, `Stopped` clogs, and node termination.                                        |
| `legacy`            | All network faults and thread pausing, nothing else.                                                                      |

`legacy` is the server's default for `basic_test`, so always pass `--fault-tolerance`.

## Network faults

Incoming and outgoing packets are faulted independently, so any network fault may be asymmetric: one direction fails while the other works.

- **Baseline latency.** On in every level but `none`: normal variation in delivery time, and a low rate of dropped packets.
- **Partitions.** Nodes split into groups that can't reach each other. Within a group, traffic is normal.
- **Clogs.** One or more nodes lose inbound traffic, outbound traffic, or both.
- **Restore.** Ends every network fault on every link.

A partition or clog disrupts packets in one of three ways: `Stopped` drops them, `Slowed` delays them, and `Jammed` holds them and delivers them later, all at once. Network faults on the same link can overlap: the more aggressive one wins while both are active.

## Node faults

- **Pause.** The node freezes, still on the network, so other nodes see timeouts. It resumes after a set time.
- **Throttle.** The node's CPU is limited, so it runs as if under heavy load.
- **Termination.** The node stops gracefully (`stop`) or crashes (`kill`), and Antithesis restarts it after a set time. It may come back with a new IP address, and with or without the changes it hadn't durably synced. Give containers no `restart:` policy: Compose would restart them at once and cancel the fault. Antithesis can't restart a Kubernetes pod, so Kubernetes manages that.

Only one node fault runs on a node at a time. Another one aimed at it while one runs is skipped.

## Other faults

- **Clock skips.** The clock jumps forward or back, on every node at once. A jump is temporary, reversed after a set time, or permanent, and jumps add up. Intrinsics such as `__rdtsc()` aren't affected.
- **Thread pausing.** Single threads pause briefly, so threads interleave in unexpected orders. It needs Antithesis instrumentation, and no container can be excluded from it.
- **CPU modulation.** The simulated processor's speed, and the relative speed of its instructions, change. That reorders concurrent threads, without needing instrumentation.
- **Custom faults.** A script of yours that the fault injector runs at random times, such as a call to an admin API. Talk to Antithesis to add one.

The log records no event for thread pausing or CPU modulation.

## Excluding containers

`--fault-exclusions` is a regex over container or pod names. An excluded container gets no faults of its own, but thread pausing, CPU modulation and clock skips still reach it, and the nodes it talks to are still faulted. Unix sockets in a volume that containers share are never faulted.

## Pausing faults

`$ANTITHESIS_STOP_FAULTS <seconds>` pauses faults on every node for that long:

- Network faults end, and Antithesis restarts killed and stopped containers, which take a while to become ready.
- No new faults start, except clock skips, which carry on during the pause.
- Faults resume on their own when the time is up. A pause can't end early, and overlapping pauses merge into the longest.

An `eventually_` or `finally_` test command also pauses faults, and ends its timeline after it runs.
