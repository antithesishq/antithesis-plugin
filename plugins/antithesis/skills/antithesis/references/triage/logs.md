# Logs

## Download a log

Read `snouty runs logs --help` first. Download the whole timeline, from the root to the end of its branch, keyed by its input hash:

```bash
mkdir -p /tmp/triage
LOG=/tmp/triage/log_${INPUT_HASH}.ndjson
PART=$(mktemp /tmp/triage/part.XXXXXX)
snouty runs logs "$RUN_ID" --json "$INPUT_HASH" > "$PART" && mv "$PART" "$LOG"
```

Pass `INPUT_HASH` verbatim, even when it is negative. Never use `--`, which makes every later option positional. Never start a file name with the hash: commands read a name like `-123.ndjson` as options.

Every moment on the branch is in the file, including the failure moment, so reuse `$LOG` for any moment with the same input hash. Other agents may be downloading the same timeline, so download to a `mktemp` file and rename it only when complete; `$LOG` exists only once a download has finished. Find a moment in it by its `moment.vtime`.

Snouty strips ANSI escape codes from `output_text` and adds an `active_faults` field to every event (see "Active faults" below).

Some logs are very large. A download can take 10 minutes or more, and you cannot know a log's size in advance. Run the download with a timeout. While waiting, start debugging the moment (`references/debug/MODULE.md`).

## Large logs

If the download does not complete before the timeout, decide:

- **You need the full log** — wait for it, with a longer timeout or by letting the command continue in the background. Only a full log gives the complete fault state.
- **The part around the failure is enough** — cancel the download and get a slice.

Do not try to estimate the log's size or the time that remains: log density varies widely across a run.

Keep the incomplete `$PART` file if you cancel; it never takes the final name, so no one mistakes it for a complete download. It holds the start of the run (`setup`, container lifecycle, the early workload), which a slice lacks, but probably not the failure moment. Its last line can be truncated, so read it with `jq -R 'fromjson? // empty | ...'`.

### Get a slice of the log

`--begin-vtime` starts the download at a vtime of your choice, such as a little before the failure moment:

```bash
SLICE=/tmp/triage/log_${INPUT_HASH}_from_${BEGIN_VTIME}.ndjson
PART=$(mktemp /tmp/triage/part.XXXXXX)
snouty runs logs "$RUN_ID" --json --begin-vtime "$BEGIN_VTIME" "$INPUT_HASH" \
  > "$PART" && mv "$PART" "$SLICE"
```

For more context, use a smaller `BEGIN_VTIME`.

> **The fault annotations in a slice are partial.** Snouty computes `active_faults` from the fault events in the stream, so a fault that started before `BEGIN_VTIME` does not appear. The faults you see are correct, but others can also be active; an empty `active_faults` is not proof that no fault was active. Download the full log if you need the complete fault state.

When you report results from a slice, give the vtime range you analyzed.

## JSON log format

Each event has `source` (`name`; `stream`, which is `"info"`, `"error"` or `"internal"`; and `container` on application events) and `moment` (`vtime`, `input_hash`). The other fields depend on the event type:

| Identifying field(s)             | `.source.name`             | What it is                                                              |
| -------------------------------- | -------------------------- | ----------------------------------------------------------------------- |
| `output_text`                    | container name             | Application log line (stdout/stderr)                                    |
| `fault`                          | `fault_injector`           | Fault injection event                                                   |
| `info`                           | `fault_injector`           | Fault injector status message                                           |
| `event`, `image`                 | `containers_meta`          | Container lifecycle (create/init/start/died)                            |
| `antithesis_setup`               | `*`                        | SDK setup-complete signal                                               |
| `antithesis_assert`              | `*`                        | SDK assertion evaluation (`.antithesis_assert.id` is the property name) |
| `command`, `started_task`        | `antithesis_test_composer` | Test command started                                                    |
| `command`, `command_return_code` | `antithesis_test_composer` | Test command finished                                                   |
| `probability`                    | `bug_probability`          | Bug probability snapshot (causal-analysis runs only — see below)        |

Assertion events with `hit: false` are the assertion catalog, not evaluations.

### Virtual time

Order and compare events by `moment.vtime`, a JSON number in the downloaded log. Do not order by timestamps printed by the application: faults like clock skew and thread pausing put them out of order.

### Application log lines

Some applications serialize configuration objects or JSON payloads into their log lines, which can be 1–4 KB long. Truncate long `output_text` when presenting logs to the user, and expect keyword searches to hit these dumps rather than meaningful messages.

### Fault events

Events with a `fault` field come from `fault_injector`. Its fields: `name`, `type`, `affected_nodes` (container names, or `["ALL"]`), `max_duration` (seconds), and an optional `details` object (`disruption_type`, `partitions`, `offset`, etc.).

- **Network Partition** (`partition`/`network`): Containers are split into partition groups. Links between groups experience the `disruption_type`. Links within a group are unaffected by this event but may be faulted by an overlapping one.
- **Network Clog** (`clog`/`network`): Links of containers in `affected_nodes` experience the `disruption_type` for `max_duration` seconds.
- **Network Restore** (`restore`/`network`): Restores all faulted network links.
- `disruption_type` values: `Stopped` (packets dropped), `Slowed` (packets delayed), `Jammed` (packets queued until a future delivery time).
- **Container Kill / Stop** (`kill`|`stop`/`node`): The container is killed or stopped for `max_duration` seconds, then restarted by Antithesis. `max_duration` is `"0"` (a string) for a Kubernetes pod, which Kubernetes restarts, not Antithesis. A restart policy may restart the container sooner.
- **Container Pause** (`pause`/`node`): The container is frozen for `max_duration` seconds. It stays on the network but processes nothing, so other containers see timeouts.
- **CPU Throttle** (`throttle`/`node`): The container's CPU is slowed for `max_duration` seconds.
- **Clock Skew** (`skip`/`clock`): The system clock jumps forward or backward by `details.offset` seconds. With `max_duration`, the offset is temporary (jitter) and reversed afterwards; without it, permanent. Offsets are cumulative.
- Only one node fault can be active on a container at a time. A second node fault on a container with an active one is silently dropped.

### Active faults

Snouty adds `active_faults` to every event, a dictionary of the fault windows open at that event. `references/antithesis/faults.md` describes what each fault does:

```json
{
  "active_faults": {
    "network_partition": { "vtime": 5.0 },
    "network_clog": { "vtime": 10.0 },
    "node_pause": { "container_a": 12.0, "container_b": 13.0 },
    "node_throttle": { "container_c": 14.0 },
    "clock_skip": { "cumulative_offset": 30.0, "vtime": 12.0 }
  }
}
```

- **`network_partition`** / **`network_clog`** — the start vtime of the outer window. Overlapping faults of one type merge into one window, from the earliest start to the latest end. Faults with empty or missing `affected_nodes` are ignored. Without `max_duration`, the window stays open until a `restore` or a fault injector pause.
- **`node_pause`** / **`node_throttle`** — container name to the vtime its fault started.
- **`clock_skip`** — `cumulative_offset` is the sum of active offsets (permanent plus jitter); `vtime` is the latest clock fault. Removed when the net offset reaches zero. Only `skip` faults with a nonzero offset are tracked.

Windows with `max_duration` expire at `start + max_duration`. A `restore` clears all network windows. A fault injector `paused: true` status event clears all network and node windows; clock windows survive it.

Not tracked: `kill` and `stop` (the container goes down and comes back, and a Kubernetes pod's restart has no set end), and thread pausing (it produces no fault injector events).

### Bug probability events (causal-analysis runs only)

Only logs from a causal-analysis experiment have `bug_probability` events; most logs you triage won't. Causal analysis re-runs a failing history forward from a series of points under different randomness. Each event's string `probability` (e.g. `"94.44"`, meaning 94.44%) is the fraction of replays from that vtime that still hit the failure.

The vtime where the probability ramps from low to high is the **moment of no return**: before it the system could have avoided the failure, after it the failure is locked in. This points to the root cause more precisely than the assertion, which often fires long after the damaging events. Extract the trajectory; no output means a normal run:

```bash
jq 'select(.source.name == "bug_probability") | {vt: .moment.vtime, p: .probability}' "$LOG"
```

## Analyzing logs with jq

The log is in `moment.vtime` order, so `jq 'select(…)'` output is chronological. Many fields are optional and can be `null`, including `source.name`; coalesce with `//` before string functions: `.output_text // "" | test("pattern")`.

### First look

List the sources in the log:

```bash
jq -c '{name: .source.name, container: .source.container}' "$LOG" | sort -u
```

Find test commands that exited non-zero:

```bash
jq 'select(.command_return_code != null and .command_return_code != "0") | {vtime: .moment.vtime, command, command_return_code}' "$LOG"
```

Search application logs for errors:

```bash
jq 'select(.output_text // "" | test("error|panic|fatal|crash"; "i")) | {vtime: .moment.vtime, source: .source.name, text: .output_text[:200]}' "$LOG"
```

### Faults

Partitions affecting a specific container (`affected_nodes` can be `["ALL"]`):

```bash
jq -c 'select(.fault.name == "partition" and (.fault.affected_nodes | index("mycontainer") or index("ALL"))) | {vtime: .moment.vtime, fault}' "$LOG"
```

Events during any node fault, and during any fault:

```bash
jq -c 'select(.active_faults | any(keys[]; startswith("node_"))) | {vtime: .moment.vtime, source: .source.name, text: .output_text[:200], active_faults}' "$LOG"
jq -c 'select(.active_faults != {}) | {vtime: .moment.vtime, source: .source.name, text: .output_text[:200], active_faults}' "$LOG"
```
