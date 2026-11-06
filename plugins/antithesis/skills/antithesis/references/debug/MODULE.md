# Debugging with Antithesis

Antithesis can run scripts at any Moment in the Multiverse. Start by choosing the moment(s) and run(s) to investigate.

## Finding moments

For a property failure, find its passing and failing moments with `snouty runs search`. On a live run, `snouty runs stream` reports counterexample moments as they happen. `snouty runs logs` shows the moments along a timeline.

## Choosing a run to execute commands in

Any ready run can execute commands, but a run that already has the moment warm saves rewarming time:

1. Prefer a ready run that has already rewarmed the moment. Check with `snouty runs search --count <run_id> 'filter(ev => ev.moment.input_hash == "<hash>")'`; non-zero means every moment of that branch is warm.
2. Prefer reusing a ready run over starting a new one.
3. If no run is ready, start a debug run with `snouty debug`.

Executing commands doesn't keep a run alive. If the run exits while you debug, pick a new one with this policy and continue.

## Executing commands

Run a bash command at a moment with `snouty runs exec`. Put every option before `RUN_ID`, and pass a negative input hash as it is. Never use `--`: everything after it is positional, so a later `--container client1` fails with `unexpected argument 'client1'`.

```bash
snouty runs exec --container client1 --timeout 5m "$RUN_ID" -1469731053185852001 38.52 'ps aux'
```

- **With `--container <name>`,** the command runs in that container and can use the tools in its image. The workload's images are under your control, so add any tool you need there.
- **Without `--container`,** it runs in the guest: the virtual machine in Antithesis's deterministic hypervisor that runs every container or Kubernetes manifest. You can't change its tools, but it has the basics, such as bash and the usual shell commands, `podman` and `kubectl`. Use it for Kubernetes pods, which `--container` doesn't support.
- If a tool is missing in either place, process the output on your machine.
- Rewarming a deep moment takes longer: a moment at vtime 10 rewarms faster than one at vtime 100.
- To see how the system reacts to an action, such as killing a container, run `sleep 30` with `--events` from the action's end moment.

## When you're done

A debug run started with `snouty debug` bills compute for as long as it stays available, up to its `--duration`. As soon as you have what you need, cancel each debug run you started with `snouty runs cancel <run_id>`. A subagent reports the debug runs it started and leaves them running, because another subagent may be using them. The agent that launched the subagents cancels those runs once they have all finished. Never cancel a run that you or your subagents didn't start.
