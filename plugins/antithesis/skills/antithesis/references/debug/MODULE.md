# Debugging with Antithesis

Antithesis can run scripts at any Moment in the Multiverse. Start by choosing the moment(s) and run(s) to investigate.

Running commands shows the system's real state, so always do it when investigating any kind of failure. Use an existing ready run if one exists, even from an unrelated source. Otherwise, start a debugging session.

A run that has ended can't execute commands, but its moments can: pull them into another ready run with `--source-run-id`, or start a debugging session on them. If `snouty runs exec` fails because the run has ended, pick another run with the policy below, and keep running commands.

## Finding moments

For a property failure, find its passing and failing moments with `snouty runs search`. On a live run, `snouty runs stream` reports counterexample moments as they happen. `snouty runs logs` shows the moments along a timeline.

## Choosing a run to execute commands in

Any ready run can execute commands, but a run that already has the moment warm saves rewarming time:

1. Prefer a ready run that has already rewarmed the moment. Check with `snouty runs search <run_id> --count 'filter(ev => ev.moment.input_hash == "<hash>")'`; non-zero means every moment of that branch is warm.
2. Prefer reusing a ready run over starting a new one.
3. If no run is ready, start a debugging session with `snouty debug`. Always pass a `--duration` that fits the investigation, such as `1h`.

When an example or counterexample appears in a run still in progress, the moment is warm there, so run commands in that run. Once the run ends, pick a run with the policy above. A new debugging session takes minutes to get ready, so don't block on it: wait with `snouty runs wait --until ready` in the background, and meanwhile read the timeline's logs with `snouty runs logs` and start on a reproducer.

Executing commands doesn't keep a run alive. If the run exits while you debug, pick a new one with this policy and continue.

## Executing commands

Run a bash command at a moment with `snouty runs exec`. Pass a negative input hash as it is. Never use `--`: everything after it is positional, so a later `--container client1` fails with `unexpected argument 'client1'`.

```bash
snouty runs exec "$RUN_ID" --container client1 --timeout 5m -1469731053185852001 38.52 'ps aux'
```

- **With `--container <name>`,** the command runs in that container and can use the tools available in its image. You cannot install additional tools, as access to the internet is blocked in the Antithesis environment.
- **Without `--container`,** it runs in the guest: the virtual machine in Antithesis's deterministic hypervisor that runs every container or Kubernetes manifest. You can't change its tools, but it has the basics, such as bash and the usual shell commands, `podman` and `kubectl`. Use it for Kubernetes pods, which `--container` doesn't support.
- If a tool is missing in either place, process the output on your machine.
- Rewarming a deep moment takes longer: a moment at vtime 10 rewarms faster than one at vtime 100.
- If the moment comes from a run that filtered logs, which shows in that run's `parameters` in `snouty runs show --json`, add `--events --include-filtered-logs` to get the dropped lines logged while the command runs, the command's own included. The filter goes with the moment, not with the run that executes the command, so check the run each moment comes from.
- To see how the system reacts to an action, such as killing a container, run `sleep 30` with `--events` from the action's end moment.

## Extracting files

To copy out a file, such as a database, compress and split it in one exec, then download the parts in parallel from its end moment:

```bash
snouty runs exec "$RUN_ID" --container db1 --json -1469731053185852001 38.52 \
  'mkdir -p /tmp/x && cd /tmp/x && gzip -c /var/lib/db/data.db | split -b 10000000 -a 3 - part. && sha256sum part.*' \
  > prep.json
jq -r 'select(.source.stream == "info") | .output_text' prep.json > parts.sha256
export RUN_ID; read -r HASH VTIME < <(jq -r '.end_moment // empty | "\(.input_hash) \(.vtime)"' prep.json); export HASH VTIME
get() { xargs -P 20 -I{} sh -c 'snouty runs exec "$RUN_ID" --container db1 "$HASH" "$VTIME" "base64 -w 1000000 /tmp/x/{}" | base64 -d > {}'; }
awk '{print $2}' parts.sha256 | get
sha256sum -c --quiet parts.sha256 | cut -d: -f1 | get   # downloads any damaged part again
sha256sum -c --quiet parts.sha256 && cat part.* | gunzip > data.db
```

- **Encode with base64 in 1 MB lines.** Raw binary arrives corrupted, a line over about 9 MB is dropped, and short lines are slow.
- **Check every part.** An exec can drop output lines and still exit 0.
- **Download parts of about 10 MB, 20 at a time.** That was fastest: 200 MB in under a minute, where one exec streams only a few hundred KB/s. The parts exist only on the first exec's branch.
- **Freeze writers first,** so the file doesn't change under you: `kill -STOP <pid>` in the first exec, or run it in the guest, without `--container`, starting with `podman pause db1 && podman cp db1:/var/lib/db/data.db /tmp/f`. The guest has `gzip` and `split` even when the image lacks them. Execs run on throwaway branches, so this changes nothing else.
- The file must exist at the moment you run at. Run any command that writes it in the first exec.

## When you're done

A debugging session started with `snouty debug` bills compute for as long as it stays available, up to its `--duration`. As soon as you have what you need, cancel each debugging session you started with `snouty runs cancel <run_id>`. A subagent reports the debugging sessions it started and leaves them running, because another subagent may be using them. The agent that launched the subagents cancels those sessions once they have all finished. Never cancel a run that you or your subagents didn't start.
