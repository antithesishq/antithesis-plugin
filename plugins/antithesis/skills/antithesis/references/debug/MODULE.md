# Debugging with Antithesis

Antithesis can run scripts at any Moment in the Multiverse. Start by choosing the moment(s) and run(s) to investigate.

Running commands shows the system's real state, so always do it when investigating any kind of failure. Use an existing ready run if one exists, even from an unrelated source. Otherwise, start a debugging session.

If the run you are using to run commands finishes, you can continue debugging by pulling the moments you need into another run.

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
- To see how the system reacts to an action, such as killing a container, run `sleep 30` with `--events` from the action's end moment.

## Extracting files

To copy a file out, such as a database or a core dump, compress it and split it into parts in one exec, then download the parts in parallel from that exec's end moment:

```bash
snouty runs exec "$RUN_ID" --container db1 -1469731053185852001 38.52 \
  'mkdir -p /tmp/x && cd /tmp/x && gzip -c /var/lib/db/data.db | split -b 10000000 -d -a 3 - part. && sha256sum part.*' \
  > parts.sha256 2> prep.err
read -r HASH VTIME < <(sed -n 's/^end moment: //p' prep.err)
get() { snouty runs exec "$RUN_ID" --container db1 "$HASH" "$VTIME" "base64 -w 1000000 /tmp/x/$1" | base64 -d > "$1"; }
for p in $(awk '{print $2}' parts.sha256); do get "$p" & done; wait
sha256sum -c --quiet parts.sha256   # names any part to download again with get
cat part.* | gunzip > data.db
```

- **Encode with base64.** The output is carried as text, so raw binary bytes arrive corrupted.
- **Wrap at 1 MB with `base64 -w 1000000`.** An output line over about 9 MB is dropped. Each line is a separate event, so the default 76-column wrapping is many times slower.
- **Check every part.** An exec can drop output lines and still exit 0, so only the checksums show a damaged part.
- **Compress** if the image has `gzip` or `zstd`. Source and logs shrink 3x or more.
- **Download parts of about 10 MB in parallel.** One exec streams at a few hundred KB/s, and a proxy can cut a request after 10 minutes. 200 MB in 10 MB parts downloaded in 30 to 60 seconds. Smaller parts were slower, from the overhead of more execs, and larger parts were slower, as each exec streams more. The parts exist only on the first exec's branch, so download them from its end moment.
- The file must exist at the moment you run at. To extract what a command writes, run the command in the first exec.

## When you're done

A debugging session started with `snouty debug` bills compute for as long as it stays available, up to its `--duration`. As soon as you have what you need, cancel each debugging session you started with `snouty runs cancel <run_id>`. A subagent reports the debugging sessions it started and leaves them running, because another subagent may be using them. The agent that launched the subagents cancels those sessions once they have all finished. Never cancel a run that you or your subagents didn't start.
