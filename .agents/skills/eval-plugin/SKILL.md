---
name: eval-plugin
description: Run a full cleanroom evaluation of the Antithesis plugin in a prepared sandbox, and report what works, what doesn't, and what to change. Use when the user asks to "eval the plugin", "run a plugin eval", "evaluate the skill end to end", or to test a plugin version against a real project.
---

# Evaluate the plugin

You run agents that use the plugin in a sandbox, as a user would, on a real open source project. You watch them through their raw transcripts and the Antithesis runs they launch, collect the data locally, and publish a report with proposed plugin changes.

You don't set up the sandbox. The user hands you one that is ready, and you check it before you start.

## What the user provides

Ask for anything missing before you start:

- **The sandbox host**, reachable with `ssh HOST`, where you have sudo. When the sandbox is the machine you run on, pass `--host local`, and the scripts run commands there without ssh.
- **The harness under test**, installed and logged in on the sandbox, such as Claude Code. `scripts/sandbox_session.py` drives `claude`, or `codex exec` when you pass `--harness codex` to `preflight` and `start`. Codex has no `/antithesis` command, so its prompts start with `$antithesis` instead, and `start --env CODEX_MODEL=M` picks its model. For another harness, add a branch to `harness_cmd`.
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

`references/prompts.md` holds the template for each task and the budget split. Test each target's latest release unless the user names a commit, and record the commit you test. Write each prompt to a file, and start its session with `scripts/evalctl.py ... start NAME CWD FILE --target NAME`. Answer a question, or nudge a session that stopped early, with `resume`.

**Run one session at a time,** and start the next only when the last has finished. Sessions at the same time clash on one machine: they share Docker's image store and container names, so one can launch another's images, and Claude Code sessions can find each other with `ListAgents` and talk with `SendMessage`. An agent that notices works around it, which pollutes the eval. For each target, in this order:

1. **Workload:** build a workload for the target end to end with the workload module, validated and with smoke runs, from a fresh clone.
2. **Triage summary:** `summary` on a completed run from (1).
3. **Triage root-cause:** `root-cause` on one failing property from (1).
4. **Debug:** the debug module on a failing moment from (1), asked to prove or disprove a specific theory.
5. **Triage monitor:** `monitor` needs a run in progress, and no session is running one now. Launch one yourself from the workload's last commit, with the launch command the workload session last used (find it in its transcript) and the monitor budget in `references/prompts.md`. Add it to the run log with `"session": "evaluator"`, and start the monitor session as soon as it launches.
6. **Triage, plain language:** "how's the latest run?" with no mode, while the run from (5) is still going if you can, in the workload's checkout.
7. **Properties:** import properties from a catalog and define a new one, then launch runs to validate them, in the workload's checkout.
8. **Iterate with patterns:** improve the workload with the patterns module, in a new clone at the latest commit of the workload branch, including one run of at least 2 hours of fuzzing.
9. **Triage summary, round 2:** `summary` on the long run from (8), in the patterns clone.
10. **Triage root-cause, round 2:** `root-cause` on a failing property that (7) or (8) added, or one that fails differently since then.

The second round of triage tests whether properties and patterns lead to more and better findings than the first workload did. Compare the two rounds in the report.

With several targets, run each target's tasks as one track, one track after another, in its own clones, and split the budget between tracks. Separate sandboxes, one per target, can run tracks at the same time.

**Keep a run log.** The tenant is almost always shared, so other people's runs show up in `snouty runs list`, sometimes on the same project. Never decide which runs belong to the eval by their name. `scripts/evalctl.py ... runlog` finds every `snouty launch` and `snouty debug` in the sessions' transcripts, subagents included, and records each run's ID, session, launch time, purpose and cap in `DATA/runs/runs.json`. Fill in each run's `task` there for the cost report. Run `scripts/evalctl.py ... watch` in the background and feed it to a Monitor: it keeps the run log current, and prints a line for each new or changed run in it, and for each session that finishes. When a session's answer mentions a run that isn't in the run log, note it: the agent has looked at someone else's run.

**Budget.** Billing runs over the `--max-compute-hours` cap, by about 2.5 compute hours per run, and `snouty runs usage` lists a run an hour or more after it ends. Track your spend from `runs usage` plus the caps of runs not yet listed, and leave slack. If the eval would go over the budget, stop launching sessions and tell the user.

## 4. Watch, and read the raw transcripts

Every 20 to 30 minutes, and whenever an event lands, run `evalctl.py ... sync` and `evalctl.py ... tail NAME`. When a session finishes, save its final answer with `evalctl.py ... result NAME > DATA/notes/final-NAME.md`, and read its transcript, including its subagents. Don't judge a session by its final summary alone: check its claims against the runs and the tool results.

`references/observe.md` lists what to look for, and the failure modes that earlier evals found. Write each observation in `observations.md` with its time, session, and the evidence that supports it.

## 5. Collect the data

Bring everything back to `DATA`:

- `logs/` and `transcripts/` from `evalctl.py ... sync`, which holds the raw Claude transcripts, subagents included, and the Codex rollouts in `transcripts/codex/`. For Codex, `runlog` reads only the parent session's commands, so check the subagents' rollouts for launches by hand;
- `notes/`: the prompts and `sessions.json` that `evalctl.py` keeps, `observations.md`, each session's final answer, and `tasks.json`;
- `runs/`: the run log `runs.json`, `usage.json` (from `evalctl.py ... usage --since START`, once every run is listed), and each run's `snouty runs show` and `snouty runs properties --failing` output;
- `repos/`: the branches, diffs and reproducers that the agents produced, such as `git format-patch` of each workload branch and any memory files they wrote.

## 6. Report cost

Split each session into tasks in `DATA/notes/tasks.json`, with a time window per task, such as "build the workload to the first launch" or "wait for and triage smoke run 2". Then run `scripts/cost_report.py DATA`. It writes `report/cost.md` and `report/cost.json`, with token usage and cost per session, per task and per target, and compute hours and cost per run and in total, at $2.50 per compute hour by default. Check the token prices in its `PRICES` table against the current ones first. Compare each session's token cost with the `total_cost_usd` its harness reported.

## 7. Write the report

Build a single HTML page, and publish it where the user asked, at a new path that doesn't replace an earlier report. It covers:

- **Setup:** plugin and snouty versions, the sandbox, the project, the budget, and any confounds.
- **Per target and task:** what the agent did, how well it followed the plugin's guidance, what it found, wall time, runs and cost, with evidence from the transcripts.
- **Findings about each system under test**, and whether each was confirmed (a reproducer, a debugging session, a log trail) or inferred. Compare the two triage rounds: what the properties and patterns work found that the first workload didn't, and whether the evidence got stronger. Score them against the expected findings in the target's profile: which known bugs each task found again, which it missed, and what's new.
- **Plugin issues**, each with the evidence and a concrete proposed change: the file to edit and what to say.
- **Cost**, from `report/cost.md`.
- **Across targets**, when there are several: which plugin issues show up on every project, and which are project-specific.
- **Comparison with the previous eval**, when there is one: what improved, what regressed, what's still open.

Then update each target's profile: add new confirmed bugs to its expected findings, with how they were confirmed, and fill in its setup and cost notes.

Tell the user the link, the total compute and token spend, and the top proposed changes.
