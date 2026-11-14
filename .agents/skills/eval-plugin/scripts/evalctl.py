#!/usr/bin/env -S uv run --quiet --locked
"""Drive agent sessions in the eval sandbox, and bring their data back.

Run `evalctl.py --host HOST --data DIR --help` for the commands. `--host local` drives
sessions on this machine, without ssh, for a sandbox that is the machine you run on. `start` records each
session in DIR/notes/sessions.json, and `start` and `resume` keep each prompt they send
in DIR/notes/prompt-NAME.N.txt. `sync` copies the session logs to DIR/logs/ and the raw
Claude transcripts to DIR/transcripts/, and the Codex rollouts to DIR/transcripts/codex/. `runlog` finds every run the sessions launched in
their transcripts, and records it in DIR/runs/runs.json, so runs that others launch on a
shared tenant never count. `watch` keeps the run log current and prints a line for each
new or changed run in it, and for each session that finishes, so it can feed a Monitor.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from collections import deque
from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent
REMOTE = "/opt/cc"  # where `push` puts sandbox_session.py; sessions log to REMOTE/logs
# exe.dev VMs keep the snouty credentials in ~/.localrc, which non-interactive ssh doesn't source.
CREDENTIALS = "[ -f ~/.localrc ] && . ~/.localrc"


def ssh(host: str, cmd: str, check: bool = True) -> str:
    """Run cmd on the sandbox, with the snouty credentials loaded."""
    argv = (
        ["bash", "-c", f"{CREDENTIALS}; {cmd}"]
        if host == "local"
        else ["ssh", "-o", "ConnectTimeout=15", host, f"{CREDENTIALS}; {cmd}"]
    )
    r = subprocess.run(argv, check=False, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"ssh {host}: {cmd!r} failed ({r.returncode}):\n{r.stderr.strip()}")
    return r.stdout


def remote(host: str, path: str) -> str:
    """An rsync or scp operand for path on the sandbox."""
    return os.path.expanduser(path) if host == "local" else f"{host}:{path}"


def read_jsonl(lines) -> Iterator[dict]:
    """The JSON objects in an iterable of lines, skipping lines that aren't JSON."""
    for line in lines:
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def sessions_file(data: Path) -> Path:
    return data / "notes" / "sessions.json"


def load_sessions(data: Path) -> dict:
    f = sessions_file(data)
    return json.loads(f.read_text()) if f.exists() else {}


def save_sessions(data: Path, s: dict) -> None:
    sessions_file(data).parent.mkdir(parents=True, exist_ok=True)
    sessions_file(data).write_text(json.dumps(s, indent=2) + "\n")


def log_files(data: Path, name: str) -> list[Path]:
    """A session's NAME.N.jsonl logs, in invocation order."""
    return sorted((data / "logs").glob(f"{name}.*.jsonl"), key=lambda p: int(p.name.split(".")[-2]))


def cmd_preflight(a) -> None:
    """Check, without changing anything, that the sandbox is ready for an eval."""
    harness = {
        "claude": {
            # First, because the harness auth check below writes a session of its own.
            "prior agent memory": "ls ~/.claude/projects 2>/dev/null | head",
            "harness": "claude --version",
            "harness auth": "claude -p 'Reply with the single word ok.' --output-format json | jq -r .result",
            "skill installed": "ls -la ~/.claude/skills/ 2>/dev/null; claude plugin list 2>/dev/null | grep -i antithesis",
        },
        "codex": {
            "prior agent memory": "ls -R ~/.codex/sessions 2>/dev/null | tail -5; ls ~/.codex/memories 2>/dev/null",
            "harness": "codex --version",
            "harness auth": "cd /tmp && codex exec --json --skip-git-repo-check 'Reply with the single word ok.' "
            "</dev/null | jq -r 'select(.item.type? == \"agent_message\") | .item.text'",
            "skill installed": "ls -la ~/.codex/skills/ ~/.agents/skills/ 2>/dev/null",
        },
    }[a.harness]
    checks = {
        **harness,
        "snouty": "snouty --version",
        "snouty auth + tenant": "snouty doctor 2>&1 | tail -3",
        "docker": "docker info --format '{{.ServerVersion}}'",
        "jq": "jq --version",
        "plugin version": f"grep -m1 'Plugin version' {a.plugin_dir}/plugins/antithesis/skills/antithesis/SKILL.md",
        "plugin checkout": f"git -C {a.plugin_dir} log --oneline -1 && git -C {a.plugin_dir} status --short | head",
        "hostname": "hostname",
    }
    # One connection for every check.
    print(ssh(a.host, "; ".join(f"echo '== {name}'; {c} 2>&1" for name, c in checks.items()), check=False))


def cmd_push(a) -> None:
    # Set aside an earlier eval's logs, so `sync` and `watch` see only this eval's.
    old = f"{REMOTE}/logs.$(date +%Y%m%d-%H%M%S)"
    ssh(
        a.host,
        f"sudo mkdir -p {REMOTE} && sudo chown -R $(id -un) {REMOTE} && "
        f'{{ [ -z "$(ls -A {REMOTE}/logs 2>/dev/null)" ] || mv {REMOTE}/logs {old}; }} && mkdir -p {REMOTE}/logs',
    )
    subprocess.run(["scp", "-q", str(HERE / "sandbox_session.py"), remote(a.host, f"{REMOTE}/")], check=True)
    print(f"pushed sandbox_session.py to {a.host}:{REMOTE}/")


def invoke(a, mode: str, entry: dict) -> None:
    """Send the prompt and run invocation N of the session, where N counts its prompts."""
    n = len(list((a.data / "notes").glob(f"prompt-{a.name}.*.txt")))
    keep = a.data / "notes" / f"prompt-{a.name}.{n}.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text(Path(a.prompt_file).read_text())
    prompt = f"{REMOTE}/prompt-{a.name}.{n}.txt"
    subprocess.run(["scp", "-q", str(keep), remote(a.host, prompt)], check=True)
    env = " ".join(f"--env {shlex.quote(kv)}" for kv in entry["env"])
    harness = entry.get("harness", "claude")
    args = f"{mode} {a.name} {n} {shlex.quote(entry['cwd'])} {prompt} {entry['id']} --harness {harness} {env}"
    print(ssh(a.host, f"python3 {REMOTE}/sandbox_session.py {args}"))


def cmd_start(a) -> None:
    s = load_sessions(a.data)
    if a.name in s:
        sys.exit(f"session {a.name} already exists ({s[a.name]['id']}); use resume, or pick a new name")
    # For codex, id is only a placeholder: the session's thread ID lands in logs/NAME.thread.
    s[a.name] = {
        "id": str(uuid.uuid4()),
        "cwd": a.cwd,
        "env": a.env,
        "target": a.target,
        "harness": a.harness,
    }
    invoke(a, "start", s[a.name])
    save_sessions(a.data, s)


def cmd_resume(a) -> None:
    # Two harness processes on one session would write the same transcript.
    if ssh(a.host, f"test -f {REMOTE}/logs/{a.name}.done && echo done", check=False).strip() != "done":
        sys.exit(f"session {a.name} is still running; wait for it to finish before you resume it")
    invoke(a, "resume", load_sessions(a.data)[a.name])


def sync(a) -> bool:
    """Copy the session logs and transcripts to DATA; whether both copies succeeded."""
    for sub in ("logs", "transcripts"):
        (a.data / sub).mkdir(parents=True, exist_ok=True)
    jobs = [subprocess.Popen(["rsync", "-az", remote(a.host, f"{REMOTE}/logs/"), f"{a.data}/logs/"])]
    harnesses = {s.get("harness", "claude") for s in load_sessions(a.data).values()}
    # Copy only the transcripts of harnesses in use: a missing directory fails rsync.
    if "claude" in harnesses:
        jobs.append(
            subprocess.Popen(
                [
                    "rsync",
                    "-az",
                    "--exclude",
                    "codex/",
                    remote(a.host, "~/.claude/projects/"),
                    f"{a.data}/transcripts/",
                ]
            )
        )
    if "codex" in harnesses:
        jobs.append(
            subprocess.Popen(
                ["rsync", "-az", remote(a.host, "~/.codex/sessions/"), f"{a.data}/transcripts/codex/"]
            )
        )
    # Wait for both, even when the first fails.
    codes = [j.wait() for j in jobs]
    return not any(codes)


def cmd_sync(a) -> None:
    if not sync(a):
        sys.exit("rsync failed")


def cmd_tail(a) -> None:
    """Print the last N actions of a session: tool calls, text, and turn results."""
    out: deque[str] = deque(maxlen=a.n)
    for f in log_files(a.data, a.name):
        with open(f) as lines:
            for e in read_jsonl(lines):
                if e.get("type") == "assistant":
                    for c in e["message"].get("content", []):
                        if c.get("type") == "text":
                            out.append("TXT " + c["text"][:400].replace("\n", " | "))
                        elif c.get("type") == "tool_use":
                            i = c["input"]
                            s = (
                                i.get("command")
                                or i.get("file_path")
                                or i.get("description")
                                or json.dumps(i)
                            )
                            out.append(f"{c['name']}: {str(s)[:300]}".replace("\n", " \\ "))
                elif e.get("type") == "item.completed":
                    i = e["item"]
                    if i.get("type") == "agent_message":
                        out.append("TXT " + i["text"][:400].replace("\n", " | "))
                    elif i.get("type") == "command_execution":
                        out.append(f"exec[{i.get('exit_code')}]: {i['command'][:300]}".replace("\n", " \\ "))
                    elif i.get("type") not in ("reasoning",):
                        out.append(f"{i.get('type')}: {json.dumps(i)[:300]}")
                elif e.get("type") in ("turn.completed", "turn.failed"):
                    u = e.get("usage") or {}
                    out.append(
                        f"TURN {e['type'].split('.')[1]} {e.get('_ts', '')} in={u.get('input_tokens')} "
                        f"cached={u.get('cached_input_tokens')} out={u.get('output_tokens')} {e.get('error') or ''}"
                    )
                elif e.get("type") == "result":
                    out.append(
                        f"RESULT {e.get('subtype')} turns={e.get('num_turns')} "
                        f"cost={e.get('total_cost_usd')} dur={e.get('duration_ms', 0) / 60000:.1f}m"
                    )
    print("\n".join(out))


def cmd_result(a) -> None:
    """Print the final result text of the session's last invocation."""
    for f in reversed(log_files(a.data, a.name)):
        with open(f) as lines:
            events = list(read_jsonl(lines))
        # codex: the invocation's last agent message is its answer, unless its turn failed.
        turns = [e for e in events if e.get("type") in ("turn.completed", "turn.failed")]
        if turns and turns[-1]["type"] == "turn.failed":
            print(f"(the last turn failed: {(turns[-1].get('error') or {}).get('message', '')})")
            return
        messages = [
            e["item"]["text"]
            for e in events
            if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"
        ]
        if turns and messages:
            print(messages[-1])
            return
        results = [e for e in events if e.get("type") == "result"]
        if results:
            last = results[-1]
            print(
                last.get("result") or f"(the last turn ended with {last.get('subtype')}, and no result text)"
            )
            return
    print("(no result yet)")


RUN_ID = re.compile(r"\b[0-9a-f]{32}-\d+-\d+\b")
LAUNCH = re.compile(r"\bsnouty\s+(?:launch|debug)\b(?![^\n]*--help)")
# A launch wrapper script, such as scripts/launch.sh or launch.py, whose output may be filtered down
# to the bare run ID.
WRAPPER = re.compile(r"\blaunch[\w-]*\.(?:sh|py)\b(?!\s*<<)")
# snouty's own lines for a new run, or `launch --json`'s runId, which also catch launches through a wrapper script,
# even when the output is cut short with `tail`.
STARTED = re.compile(
    r"(?:Test run started: run_id |Wait for the run to finish with:\s+snouty runs wait |\"runId\":\s*\")"
    r"([0-9a-f]{32}-\d+-\d+)"
)


def text_of(content) -> str:
    """A tool result's text, with its newlines, whether it's a string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def record(log: dict, name: str, cmd: str, out: str, when: str | None) -> None:
    """Add the run that one shell call of session name launched, if any, to the run log."""
    launch = bool(LAUNCH.search(cmd) or WRAPPER.search(cmd))
    ids = [i for i in RUN_ID.findall(out) if i not in cmd] if launch else STARTED.findall(out)
    if not ids:
        return
    old = log.get(ids[0])
    if old and not (launch and old.get("source") == "output"):
        return
    cap = re.search(r"--max-compute-hours[ =](\d+)", cmd)
    desc = re.search(r"--description[ =](?:\"([^\"]*)\"|'([^']*)')", cmd)
    log[ids[0]] = (old or {}) | {
        "session": name,
        "launched": when,
        "purpose": next((g for g in desc.groups() if g), "")
        if desc
        else "debugging session"
        if "snouty debug" in cmd
        else "",
        "cap": int(cap.group(1)) if cap else 0,
    }
    if not launch:
        log[ids[0]]["source"] = "output"
    else:
        log[ids[0]].pop("source", None)


def runlog(data: Path) -> dict:
    """Add every run that a session launched to runs/runs.json, from the synced transcripts.

    A launch is a Bash call that runs `snouty launch`, `snouty debug` or a `launch*.sh`
    wrapper, whose run ID is the first new one in the call's output. Any other Bash call
    whose output has snouty's own lines for a new run counts too, marked "source": "output",
    and a launch call found later replaces it, so a call that only re-reads a launch log
    can't claim the run. A wrapper's cap isn't on its command line, so it starts at 0 and
    `fill_caps` sets it from snouty. Existing entries keep any fields you added.
    """
    path = data / "runs" / "runs.json"
    log = json.loads(path.read_text()) if path.exists() else {}
    for name, s in load_sessions(data).items():
        if s.get("harness") == "codex":
            for f in log_files(data, name):
                with open(f) as lines:
                    for e in read_jsonl(lines):
                        i = e.get("item") or {}
                        if e.get("type") == "item.completed" and i.get("type") == "command_execution":
                            record(log, name, i["command"], i.get("aggregated_output") or "", e.get("_ts"))
            continue
        files = list((data / "transcripts").glob(f"*/{s['id']}.jsonl"))
        files += list((data / "transcripts").glob(f"*/{s['id']}/subagents/*.jsonl"))
        for f in files:
            launches: dict[str, str] = {}
            with open(f) as lines:
                for e in read_jsonl(lines):
                    content = (e.get("message") or {}).get("content")
                    for c in content if isinstance(content, list) else []:
                        if c.get("type") == "tool_use" and c.get("name") == "Bash":
                            launches[c["id"]] = str(c["input"].get("command", ""))
                        elif c.get("type") == "tool_result" and c.get("tool_use_id") in launches:
                            cmd = launches.pop(c["tool_use_id"])
                            record(log, name, cmd, text_of(c.get("content")), e.get("timestamp"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, indent=2) + "\n")
    return log


def list_runs(a) -> list[dict]:
    """The tenant's recent runs, from `snouty runs list`."""
    return list(
        read_jsonl(ssh(a.host, "snouty runs list -n 200 --json 2>/dev/null", check=False).splitlines())
    )


def fill_caps(data: Path, runs: list[dict]) -> None:
    """Set the cap of each logged run that has none, such as a wrapper's, from snouty."""
    path = data / "runs" / "runs.json"
    log = json.loads(path.read_text()) if path.exists() else {}
    changed = False
    for r in runs:
        cap = (r.get("parameters") or {}).get("antithesis.max_compute_hours")
        entry = log.get(r.get("run_id"))
        if entry is not None and not entry.get("cap") and cap:
            entry["cap"] = int(float(cap))
            changed = True
    if changed:
        path.write_text(json.dumps(log, indent=2) + "\n")


def cmd_runlog(a) -> None:
    cmd_sync(a)
    runlog(a.data)
    fill_caps(a.data, list_runs(a))
    for rid, r in json.loads((a.data / "runs" / "runs.json").read_text()).items():
        print(f"{rid}  {r.get('session', '')}  cap={r.get('cap', '?')}  {r.get('purpose', '')}")


def poll(a) -> tuple[set[str], set[str]]:
    """The eval's runs, from its run log, and the finished sessions; nothing if the sync fails."""
    # Transcripts change while sessions run, so a sync can fail now and then. Skip this
    # poll rather than exit, so the watch keeps going.
    if not sync(a):
        return set(), set()
    ids = set(runlog(a.data))
    raw = ssh(
        a.host,
        f"snouty runs list -n 200 --json 2>/dev/null; echo '--DONE--'; "
        f"cd {REMOTE}/logs && for f in *.done; do [ -f $f ] && echo $f $(cat $f); done",
        check=False,
    )
    runs_part, _, done_part = raw.partition("--DONE--\n")
    listed = list(read_jsonl(runs_part.splitlines()))
    fill_caps(a.data, listed)
    runs = set()
    for r in listed:
        if r.get("run_id") not in ids:
            continue
        p = r.get("parameters", {})
        desc = (r.get("description") or p.get("antithesis.test_name") or "").splitlines()
        cap = p.get("antithesis.max_compute_hours", "?")
        runs.add(f"{r['run_id']} {r['status']} {r.get('launcher')} mch={cap} {desc[0] if desc else ''}")
    return runs, set(done_part.splitlines()) - {""}


def cmd_watch(a) -> None:
    seen_runs, seen_done = poll(a)
    while True:
        time.sleep(60)
        runs, done = poll(a)
        for r in sorted(runs - seen_runs):
            print("RUN:", r, flush=True)
        for d in sorted(done - seen_done):
            print("SESSION DONE:", d, flush=True)
        # Keep the last good view when a poll fails.
        seen_runs, seen_done = runs or seen_runs, done or seen_done


def cmd_usage(a) -> None:
    """Save billed compute hours for the runs in the run log.

    snouty 0.10 dropped -n and takes run IDs instead, which --after can't be combined
    with, so --since is ignored. A run that hasn't been billed yet is left out. It syncs
    first, so runs launched since the last sync are in the run log.
    """
    sync(a)
    ids = " ".join(shlex.quote(i) for i in runlog(a.data))
    raw = ssh(a.host, f"snouty runs usage --json {ids}") if ids else ""
    rows = list(read_jsonl(raw.splitlines()))
    out = a.data / "runs" / "usage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"{len(rows)} runs -> {out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", required=True, help="ssh host of the sandbox")
    p.add_argument("--data", required=True, type=Path, help="local data directory for this eval")
    sub = p.add_subparsers(required=True)
    pf = sub.add_parser("preflight", help="check the sandbox, changing nothing")
    pf.add_argument("--plugin-dir", default="~/antithesis-plugin")
    pf.add_argument("--harness", default="claude", choices=["claude", "codex"])
    pf.set_defaults(func=cmd_preflight)
    sub.add_parser("push", help="copy sandbox_session.py to the sandbox").set_defaults(func=cmd_push)
    st = sub.add_parser("start", help="start a session")
    st.add_argument("name")
    st.add_argument("cwd")
    st.add_argument("prompt_file")
    st.add_argument("--env", action="append", default=[], help="K=V to export for the session")
    st.add_argument("--target", default="", help="the target profile the session tests")
    st.add_argument("--harness", default="claude", choices=["claude", "codex"], help="the harness under test")
    st.set_defaults(func=cmd_start)
    rs = sub.add_parser("resume", help="send a session its next prompt")
    rs.add_argument("name")
    rs.add_argument("prompt_file")
    rs.set_defaults(func=cmd_resume)
    sub.add_parser("sync", help="copy logs and transcripts to DATA").set_defaults(func=cmd_sync)
    t = sub.add_parser("tail", help="print a session's last actions")
    t.add_argument("name")
    t.add_argument("-n", type=int, default=30)
    t.set_defaults(func=cmd_tail)
    r = sub.add_parser("result", help="print a session's final answer")
    r.add_argument("name")
    r.set_defaults(func=cmd_result)
    sub.add_parser("runlog", help="record the runs the sessions launched").set_defaults(func=cmd_runlog)
    sub.add_parser("watch", help="print the eval's run changes and finished sessions").set_defaults(
        func=cmd_watch
    )
    u = sub.add_parser("usage", help="save billed compute hours per run")
    u.add_argument("--since", required=True)
    u.set_defaults(func=cmd_usage)
    a = p.parse_args()
    a.data = a.data.expanduser().resolve()
    a.func(a)


if __name__ == "__main__":
    main()
