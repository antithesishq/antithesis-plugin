#!/usr/bin/env -S uv run --quiet --locked
"""Drive agent sessions in the eval sandbox, and bring their data back.

Run `evalctl.py --host HOST --data DIR --help` for the commands. `start` records each
session in DIR/notes/sessions.json, and `start` and `resume` keep each prompt they send
in DIR/notes/prompt-NAME.N.txt. `sync` copies the session logs to DIR/logs/ and the raw
Claude transcripts to DIR/transcripts/. `runlog` finds every run the sessions launched in
their transcripts, and records it in DIR/runs/runs.json, so runs that others launch on a
shared tenant never count. `watch` keeps the run log current and prints a line for each
new or changed run in it, and for each session that finishes, so it can feed a Monitor.
"""

import argparse
import json
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
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", host, f"{CREDENTIALS}; {cmd}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and r.returncode != 0:
        sys.exit(f"ssh {host}: {cmd!r} failed ({r.returncode}):\n{r.stderr.strip()}")
    return r.stdout


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
    checks = {
        # First, because the harness auth check below writes a session of its own.
        "prior agent memory": "ls ~/.claude/projects 2>/dev/null | head",
        "harness": "claude --version",
        "harness auth": "claude -p 'Reply with the single word ok.' --output-format json | jq -r .result",
        "snouty": "snouty --version",
        "snouty auth + tenant": "snouty doctor 2>&1 | tail -3",
        "docker": "docker info --format '{{.ServerVersion}}'",
        "jq": "jq --version",
        "plugin version": f"grep -m1 'Plugin version' {a.plugin_dir}/plugins/antithesis/skills/antithesis/SKILL.md",
        "plugin checkout": f"git -C {a.plugin_dir} log --oneline -1 && git -C {a.plugin_dir} status --short | head",
        "skill installed": "ls -la ~/.claude/skills/ 2>/dev/null; claude plugin list 2>/dev/null | grep -i antithesis",
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
    subprocess.run(["scp", "-q", str(HERE / "sandbox_session.py"), f"{a.host}:{REMOTE}/"], check=True)
    print(f"pushed sandbox_session.py to {a.host}:{REMOTE}/")


def invoke(a, mode: str, entry: dict) -> None:
    """Send the prompt and run invocation N of the session, where N counts its prompts."""
    n = len(list((a.data / "notes").glob(f"prompt-{a.name}.*.txt")))
    keep = a.data / "notes" / f"prompt-{a.name}.{n}.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text(Path(a.prompt_file).read_text())
    remote = f"{REMOTE}/prompt-{a.name}.{n}.txt"
    subprocess.run(["scp", "-q", str(keep), f"{a.host}:{remote}"], check=True)
    env = " ".join(f"--env {shlex.quote(kv)}" for kv in entry["env"])
    args = f"{mode} {a.name} {n} {shlex.quote(entry['cwd'])} {remote} {entry['id']} {env}"
    print(ssh(a.host, f"python3 {REMOTE}/sandbox_session.py {args}"))


def cmd_start(a) -> None:
    s = load_sessions(a.data)
    if a.name in s:
        sys.exit(f"session {a.name} already exists ({s[a.name]['id']}); use resume, or pick a new name")
    s[a.name] = {"id": str(uuid.uuid4()), "cwd": a.cwd, "env": a.env, "target": a.target}
    invoke(a, "start", s[a.name])
    save_sessions(a.data, s)


def cmd_resume(a) -> None:
    # Two harness processes on one session would write the same transcript.
    if ssh(a.host, f"test -f {REMOTE}/logs/{a.name}.done && echo done", check=False).strip() != "done":
        sys.exit(f"session {a.name} is still running; wait for it to finish before you resume it")
    invoke(a, "resume", load_sessions(a.data)[a.name])


def cmd_sync(a) -> None:
    for sub in ("logs", "transcripts"):
        (a.data / sub).mkdir(parents=True, exist_ok=True)
    jobs = [
        subprocess.Popen(["rsync", "-az", f"{a.host}:{REMOTE}/logs/", f"{a.data}/logs/"]),
        subprocess.Popen(["rsync", "-az", f"{a.host}:.claude/projects/", f"{a.data}/transcripts/"]),
    ]
    if any(j.wait() for j in jobs):
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
            results = [e for e in read_jsonl(lines) if e.get("type") == "result"]
        if results:
            last = results[-1]
            print(
                last.get("result") or f"(the last turn ended with {last.get('subtype')}, and no result text)"
            )
            return
    print("(no result yet)")


RUN_ID = re.compile(r"\b[0-9a-f]{32}-\d+-\d+\b")
LAUNCH = re.compile(r"\bsnouty\s+(?:launch|debug)\b(?![^\n]*--help)")


def runlog(data: Path) -> dict:
    """Add every run that a session launched to runs/runs.json, from the synced transcripts.

    A launch is a Bash call that runs `snouty launch` or `snouty debug`; its run ID is the
    one that first appears in the call's output. Existing entries keep any fields you added.
    """
    path = data / "runs" / "runs.json"
    log = json.loads(path.read_text()) if path.exists() else {}
    for name, s in load_sessions(data).items():
        files = list((data / "transcripts").glob(f"*/{s['id']}.jsonl"))
        files += list((data / "transcripts").glob(f"*/{s['id']}/subagents/*.jsonl"))
        for f in files:
            launches: dict[str, str] = {}
            with open(f) as lines:
                for e in read_jsonl(lines):
                    content = (e.get("message") or {}).get("content")
                    for c in content if isinstance(content, list) else []:
                        if c.get("type") == "tool_use" and LAUNCH.search(str(c["input"].get("command", ""))):
                            launches[c["id"]] = c["input"]["command"]
                        elif c.get("type") == "tool_result" and c.get("tool_use_id") in launches:
                            cmd = launches.pop(c["tool_use_id"])
                            ids = [i for i in RUN_ID.findall(json.dumps(c.get("content"))) if i not in cmd]
                            if not ids or ids[0] in log:
                                continue
                            cap = re.search(r"--max-compute-hours[ =](\d+)", cmd)
                            desc = re.search(r"--description[ =](?:\"([^\"]*)\"|'([^']*)')", cmd)
                            log[ids[0]] = {
                                "session": name,
                                "launched": e.get("timestamp"),
                                "purpose": next((g for g in desc.groups() if g), "")
                                if desc
                                else "debug run"
                                if "snouty debug" in cmd
                                else "",
                                "cap": int(cap.group(1)) if cap else 0,
                            }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, indent=2) + "\n")
    return log


def cmd_runlog(a) -> None:
    cmd_sync(a)
    for rid, r in runlog(a.data).items():
        print(f"{rid}  {r.get('session', '')}  cap={r.get('cap', '?')}  {r.get('purpose', '')}")


def poll(a) -> tuple[set[str], set[str]]:
    """The eval's runs, from its run log, and the finished sessions."""
    cmd_sync(a)
    ids = set(runlog(a.data))
    raw = ssh(
        a.host,
        f"snouty runs list -n 200 --json 2>/dev/null; echo '--DONE--'; "
        f"cd {REMOTE}/logs && for f in *.done; do [ -f $f ] && echo $f $(cat $f); done",
        check=False,
    )
    runs_part, _, done_part = raw.partition("--DONE--\n")
    runs = set()
    for r in read_jsonl(runs_part.splitlines()):
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
    """Save billed compute hours per run, for runs that ended after --since."""
    raw = ssh(a.host, f"snouty runs usage --json --after {shlex.quote(a.since)} -n 1000")
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
    pf.set_defaults(func=cmd_preflight)
    sub.add_parser("push", help="copy sandbox_session.py to the sandbox").set_defaults(func=cmd_push)
    st = sub.add_parser("start", help="start a session")
    st.add_argument("name")
    st.add_argument("cwd")
    st.add_argument("prompt_file")
    st.add_argument("--env", action="append", default=[], help="K=V to export for the session")
    st.add_argument("--target", default="", help="the target profile the session tests")
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
