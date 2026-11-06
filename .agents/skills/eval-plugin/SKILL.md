---
name: eval-plugin
description: Run a full cleanroom evaluation of the Antithesis plugin in a prepared sandbox, and report what works, what doesn't, and what to change. Use when the user asks to "eval the plugin", "run a plugin eval", "evaluate the skill end to end", or to test a plugin version against a real project.
---

# Evaluate the plugin

You run agents that use the plugin in a sandbox, as a user would, on a real open source project. You watch them through their raw transcripts and the Antithesis runs they launch, collect the data locally, and publish a report with proposed plugin changes.

You don't set up the sandbox. The user hands you one that is ready, and you check it before you start.

## What the user provides

Ask for anything missing before you start:

- **The sandbox host**, reachable with `ssh HOST`, where you have sudo.
- **The harness under test**, installed and logged in on the sandbox, such as Claude Code. `scripts/sandbox_session.py` drives `claude`. For another harness, change its `harness_cmd`.
- **snouty**, installed and logged in to a tenant on the sandbox, with the credentials in the login environment (for example `~/.localrc`).
- **The plugin**, installed into the harness from a checkout on the sandbox, such as a skill symlink into `~/.claude/skills`.
- **Docker**, jq and the toolchains the target project needs.
- **The compute budget** for the whole eval, in compute hours.
- **The target projects:** one or more profiles in `references/targets/`: `references/targets/rqlite.md`, `references/targets/nats-jetstream.md` or `references/targets/zookeeper.md`. Each profile says what to test and what to put in the prompts, and holds cost notes, quirks, and the bugs that earlier evals found. To add a project, copy a profile and fill it in.
- **Where the final report should be written.**

## 1. Preflight: check, don't set up

Run `scripts/evalctl.py --host HOST --data DATA preflight --plugin-dir PATH`. `DATA` is a new local directory for this eval, such as `~/plugin-eval-N-data`. Never reuse an earlier eval's directory.

Then:

1. Check that the toolchains each target's profile names are installed.
2. Update the plugin checkout to the version under test (`git pull --ff-only` on its default branch, or check out the given ref), and confirm that the `Plugin version` line in `SKILL.md` matches the plugin manifest.
3. Run `snouty update`, and record the snouty version.
4. If a check fails, such as the harness not being logged in, snouty failing `snouty doctor`, or no tenant access, stop and tell the user what is missing. Don't fix it yourself.
5. Run `scripts/evalctl.py ... push`, which copies the session runner to `/opt/cc/` on the sandbox.

Write everything you learn in `DATA/notes/observations.md` as you go, starting with this setup: versions, commits, and any confound in the sandbox, such as a global `CLAUDE.md` that mentions Antithesis.

## 2. Keep the agents blind

The agents must not know that they're being evaluated, and must attempt each task as well as they can:

- **Prompts read like a user's.** Fill in the templates in `references/prompts.md`, and change nothing else. Never mention evals, graders, or the plugin's internals, and never hint at bugs you know about, including those in the target's profile.
- **Nothing in the sandbox says "eval".** Check `hostname`, paths, repo names and environment variables. A hostname that gives it away can be changed with `sudo hostname NAME` plus an `/etc/hosts` line. Note that artifact links the agents build from `$(hostname)` will then be wrong.
- **No coaching.** When an agent stops and asks a question, answer as a user would, with `evalctl.py resume`. Don't steer it towards the docs.
- **Carryover is acceptable.** A later session may find an earlier session's memory or files, as a real user's sessions would. Record it whenever it happens.

## 3. Run the experiments

`references/prompts.md` holds the template for each task and the budget split. Test each target's latest release unless the user names a commit, and record the commit you test. Write each prompt to a file, and start its session with `scripts/evalctl.py ... start NAME CWD FILE --target NAME`. Answer a question, or nudge a session that stopped early, with `resume`. For each target, at minimum:

1. **Workload:** build a workload for the target project end to end with the workload module, validated and with smoke runs, from a fresh clone.
2. **Triage:** each entry point on runs from (1): `summary` on a completed run, `root-cause` on one failing property, `monitor` on a run in progress, and a plain-language "how's the latest run?" with no mode, during a long run.
3. **Debug:** the debug module on a failing moment from (1), asked to prove or disprove a specific theory.
4. **Properties:** import properties from a catalog and define a new one, then launch runs to validate them.
5. **Iterate with patterns:** improve the workload from (1) with the patterns module, in a separate clone at the workload's last commit, including one run of at least 2 hours of fuzzing.

Schedule them so the wall time stays reasonable:

- **Triage and debug** can run while the workload session is still going, as soon as it has launched a run. `monitor` needs a run in progress: start it right after a smoke run launches.
- **Run every task that uses Docker one at a time:** the workload, properties and patterns all build images and run the local loop. On one machine they share the image store and the container names, so two at once can launch each other's images or tear down each other's containers. An agent that notices works around it, which pollutes the eval. To save wall time, start the next Docker task while the current one only waits on a long Antithesis run, or use a second sandbox.
- **With several targets,** run each target's tasks as one track, in its own clones, and split the budget between tracks. Tracks share the Docker rule above, so on one sandbox, interleave them only where a task is waiting on Antithesis. Separate sandboxes, one per target, avoid the problem entirely.
- Sessions in parallel share the tenant, so an agent may notice another's runs in `snouty runs list`. Claude Code sessions on one machine can also find each other with `ListAgents` and talk with `SendMessage`. Record it when it happens.

Run `scripts/evalctl.py ... watch --since START --match 'PROJECT|debugging'` in the background and feed it to a Monitor. It prints a line for each new or changed run, and for each session that finishes. Track every run in `DATA/runs/runs.json`, with its session, task, purpose and cap.

**Budget.** Billing runs over the `--max-compute-hours` cap, by about 2.5 compute hours per run, and `snouty runs usage` lists a run an hour or more after it ends. Track your spend from `runs usage` plus the caps of runs not yet listed, and leave slack. If the eval would go over the budget, stop launching sessions and tell the user.

## 4. Watch, and read the raw transcripts

Every 20 to 30 minutes, and whenever an event lands, run `evalctl.py ... sync` and `evalctl.py ... tail NAME`. When a session finishes, save its final answer with `evalctl.py ... result NAME > DATA/notes/final-NAME.md`, and read its transcript, including its subagents. Don't judge a session by its final summary alone: check its claims against the runs and the tool results.

`references/observe.md` lists what to look for, and the failure modes that earlier evals found. Write each observation in `observations.md` with its time, session, and the evidence that supports it.

## 5. Collect the data

Bring everything back to `DATA`:

- `logs/` and `transcripts/` from `evalctl.py ... sync`, which holds the raw Claude transcripts, subagents included;
- `notes/`: the prompts and `sessions.json` that `evalctl.py` keeps, `observations.md`, each session's final answer, and `tasks.json`;
- `runs/`: `runs.json`, `usage.json` (from `evalctl.py ... usage --since START`, once every run is listed), and each run's `snouty runs show` and `snouty runs properties --failing` output;
- `repos/`: the branches, diffs and reproducers that the agents produced, such as `git format-patch` of each workload branch and any memory files they wrote.

## 6. Report cost

Split each session into tasks in `DATA/notes/tasks.json`, with a time window per task, such as "build the workload to the first launch" or "wait for and triage smoke run 2". Then run `scripts/cost_report.py DATA`. It writes `report/cost.md` and `report/cost.json`, with token usage and cost per session, per task and per target, and compute hours and cost per run and in total, at $2.50 per compute hour by default. Check the token prices in its `PRICES` table against the current ones first. Compare each session's token cost with the `total_cost_usd` its harness reported.

## 7. Write the report

Build a single HTML page, and publish it where the user asked, at a new path that doesn't replace an earlier report. It covers:

- **Setup:** plugin and snouty versions, the sandbox, the project, the budget, and any confounds.
- **Per target and task:** what the agent did, how well it followed the plugin's guidance, what it found, wall time, runs and cost, with evidence from the transcripts.
- **Findings about each system under test**, and whether each was confirmed (a reproducer, a debugging session, a log trail) or inferred. Score them against the expected findings in the target's profile: which known bugs each task found again, which it missed, and what's new.
- **Plugin issues**, each with the evidence and a concrete proposed change: the file to edit and what to say.
- **Cost**, from `report/cost.md`.
- **Across targets**, when there are several: which plugin issues show up on every project, and which are project-specific.
- **Comparison with the previous eval**, when there is one: what improved, what regressed, what's still open.

Then update each target's profile: add new confirmed bugs to its expected findings, with how they were confirmed, and fill in its setup and cost notes.

Tell the user the link, the total compute and token spend, and the top proposed changes.
