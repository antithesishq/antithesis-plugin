#!/usr/bin/env python3
"""Start or resume one agent session in the eval sandbox, detached from the caller.

Runs on the sandbox, not locally: `evalctl.py push` copies it there, and `evalctl.py
start` and `evalctl.py resume` call it over ssh, from a shell that has sourced the
snouty credentials. It needs only the standard library, because the sandbox may
have no uv.

    sandbox_session.py start|resume NAME N CWD PROMPT_FILE SESSION_ID [--env K=V ...]

Invocation N of session NAME writes, in the logs/ directory next to this script:
    NAME.N.jsonl   the harness's stream-json output
    NAME.N.err     its stderr
    NAME.done      "<exit code> <time>" once it exits (removed at start)
"""

import argparse
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOGS = Path(__file__).resolve().parent / "logs"


def harness_cmd(mode: str, session_id: str, prompt: str) -> str:
    """The command that runs one turn. Change it to eval the plugin in another harness."""
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
    cmd = f"cd {shlex.quote(a.cwd)} && {exports}{harness_cmd(a.mode, a.session_id, Path(a.prompt_file).read_text())}"
    with open(LOGS / f"{a.name}.{a.n}.jsonl", "w") as out, open(LOGS / f"{a.name}.{a.n}.err", "w") as err:
        # A login shell, so the session sees the same environment a user's terminal does.
        shell = "zsh" if Path("/bin/zsh").exists() or Path("/usr/bin/zsh").exists() else "bash"
        rc = subprocess.call([shell, "-lc", cmd], stdout=out, stderr=err)
    done.write_text(f"{rc} {datetime.now().astimezone().isoformat()}\n")


if __name__ == "__main__":
    main()
