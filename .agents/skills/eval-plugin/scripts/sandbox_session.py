#!/usr/bin/env python3
"""Start or resume one agent session in the eval sandbox, detached from the caller.

Runs on the sandbox, not locally: `evalctl.py push` copies it there, and `evalctl.py
start` and `evalctl.py resume` call it over ssh, from a shell that has sourced the
snouty credentials. It needs only the standard library, because the sandbox may
have no uv.

    sandbox_session.py start|resume NAME N CWD PROMPT_FILE SESSION_ID [--harness H] [--env K=V ...]

Invocation N of session NAME writes, in the logs/ directory next to this script:
    NAME.N.jsonl   the harness's JSON event stream, each line stamped with "_ts"
    NAME.N.err     its stderr
    NAME.thread    codex only: the thread ID that `codex exec` chose, which resume needs
    NAME.done      "<exit code> <time>" once it exits (removed at start)
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

LOGS = Path(__file__).resolve().parent / "logs"


def harness_cmd(harness: str, mode: str, session_id: str, prompt: str) -> str:
    """The command that runs one turn. Add a branch to eval the plugin in another harness."""
    if harness == "codex":
        # codex picks its own thread ID, which start records in NAME.thread. A session
        # started with --env CODEX_MODEL=M runs on model M instead of the configured one.
        resume = f"resume {shlex.quote(session_id)} " if mode == "resume" else ""
        return (
            f"codex exec {resume}${{CODEX_MODEL:+--model=$CODEX_MODEL}} --json --skip-git-repo-check "
            f"--dangerously-bypass-approvals-and-sandbox {shlex.quote(prompt)}"
        )
    session = f"--session-id {session_id}" if mode == "start" else f"--resume {session_id}"
    return (
        f"claude -p {shlex.quote(prompt)} {session} "
        "--output-format stream-json --verbose --permission-mode bypassPermissions"
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["start", "resume"])
    p.add_argument("name")
    p.add_argument("n", type=int)
    p.add_argument("cwd")
    p.add_argument("prompt_file")
    p.add_argument("session_id")
    p.add_argument("--harness", default="claude", choices=["claude", "codex"])
    p.add_argument("--env", action="append", default=[], help="K=V to export for this session")
    p.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args()

    if not a.foreground:
        # Re-exec detached, so the session survives the ssh connection that started it.
        subprocess.Popen(
            [sys.executable, __file__, *sys.argv[1:], "--foreground"],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"{a.name}: {a.mode}ed session {a.session_id}")
        return

    LOGS.mkdir(parents=True, exist_ok=True)
    done = LOGS / f"{a.name}.done"
    done.unlink(missing_ok=True)
    exports = "".join(f"export {shlex.quote(kv)}; " for kv in a.env)
    cwd = shlex.quote(os.path.expanduser(a.cwd))
    thread = LOGS / f"{a.name}.thread"
    sid = thread.read_text().strip() if a.harness == "codex" and a.mode == "resume" else a.session_id
    cmd = f"cd {cwd} && {exports}{harness_cmd(a.harness, a.mode, sid, Path(a.prompt_file).read_text())}"
    with open(LOGS / f"{a.name}.{a.n}.jsonl", "w") as out, open(LOGS / f"{a.name}.{a.n}.err", "w") as err:
        # A login shell, so the session sees the same environment a user's terminal does.
        shell = "zsh" if Path("/bin/zsh").exists() or Path("/usr/bin/zsh").exists() else "bash"
        proc = subprocess.Popen(
            [shell, "-lc", cmd], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, text=True
        )
        assert proc.stdout
        # Stamp each event with its time, because codex's events carry none.
        for line in proc.stdout:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                out.write(line)
            else:
                if isinstance(e, dict):
                    e["_ts"] = datetime.now(UTC).isoformat()
                    if e.get("type") == "thread.started" and a.mode == "start":
                        thread.write_text(e["thread_id"] + "\n")
                out.write(json.dumps(e) + "\n")
            out.flush()
        rc = proc.wait()
    done.write_text(f"{rc} {datetime.now().astimezone().isoformat()}\n")


if __name__ == "__main__":
    main()
