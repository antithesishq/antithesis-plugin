# Debugging with Antithesis

## Run and Timeline selection

Antithesis provides a time travelling debug environment, which allows scripts to be run at arbitrary Moments in the Multiverse. When starting the debug process, first figure out which moment(s) and run(s) you want to investigate.

If you are trying to debug a property failure, you can search Antithesis for passing and failing moments associated with the property using `snouty runs search`. On a live run, `snouty runs stream` gives counterexample moments as they happen. You can pull interesting moments from a timeline via `snouty runs logs`.

## Choosing a run to execute commands in

Antithesis can execute a command in any run that is ready, however there is value in picking a run that already has the moment warm. Follow this policy when picking a run to execute commands in:

1. The run must have status `in_progress` and sub-status `ready`. You can either use `snouty runs show` or `snouty runs wait --until ready` to check.
2. Prefer runs that already have rewarmed the desired moment. Use `snouty runs search <run_id> 'filter(ev => ev.moment.input_hash == "<hash>")' --count` to check. If that returns non-zero, all moments from the branch are warm.
3. Prefer reusing a ready run over starting a new run.
4. If there is no in_progress & ready run available, spin up a dedicated debug run using `snouty debug`.

Running commands does not prevent runs from exiting. If the run exits while you are debugging, follow the policy above to pick a new run and continue debugging.

## Executing commands

You can execute an arbitrary bash command at a given moment using `snouty runs exec`. This is a powerful tool for exploration and debugging.

The command runs in the workload's containers inside the run, not on your machine. It can use only the tools installed in those images, which may not match what you have locally. Process its output on your machine instead, if the tool you need isn't there.

As part of its output, `snouty runs exec` prints an "end moment", which is the moment where the command finished executing. You can use this moment to execute follow-up commands in the same timeline.

Additional moments from any run (source run or otherwise) may be loaded into an existing run via the `--source-run-id` parameter to `snouty runs exec`. Rewarming a moment takes time relative to the deepness of a moment - hence a moment at vtime 10 will be faster to rewarm than a moment at vtime 100.

- Use `--container <name>` to execute the command inside that container. This does not currently support `k8s` pods, use `kubectl` for that.
- Use `--events` to print out all events that happen in the simulation while the command executes (rather than just stdout/stderr of the command).

You can combine `--events` with eg `sleep 30`, to see what the system does in those 30 seconds. A nice trick is to do this after performing some action, like killing a container, to see the result of that action on the system.

Read `references/nope.md`.
