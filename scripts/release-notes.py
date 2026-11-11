#!/usr/bin/env -S uv run --quiet --locked
"""Have Claude pick the next version and write its notes, in the Release PR workflow.

    scripts/release-notes.py

Runs Claude Code, pinned by `claude@VERSION` in CLAUDE_CODE, on the release skill's "Pick
and check the version" and "Write the notes" sections. Claude can only read: its tools
are read-only, and the job's token can't write. It answers with the version, its reason
and the notes, which this writes to GITHUB_OUTPUT for the job that opens the PR.

Claude Code authenticates with workload identity federation, from the
ANTHROPIC_FEDERATION_RULE_ID, ANTHROPIC_ORGANIZATION_ID, ANTHROPIC_SERVICE_ACCOUNT_ID and
ANTHROPIC_WORKSPACE_ID in the environment. This fetches the job's GitHub OIDC token into
ANTHROPIC_IDENTITY_TOKEN_FILE, and fetches a fresh one every minute: each lives about five
minutes, and Anthropic accepts each only once. Claude doesn't get the request token that
fetches them.
"""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from report import ROOT

AUDIENCE = "https://api.anthropic.com"
REFRESH_SECONDS = 60
MODEL = "claude-opus-5-5"
TOOLS = [
    "Read",
    "Glob",
    "Grep",
    *(f"Bash(git {c}:*)" for c in ("diff", "log", "show", "status", "tag -l", "rev-parse")),
    "Bash(grep:*)",
    "Bash(head:*)",
    "Bash(gh release view:*)",
    "Bash(gh repo view:*)",
]
SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "reason": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["version", "reason", "notes"],
}
PROMPT = """\
You're preparing a release of the Antithesis plugin, unattended, in GitHub Actions.
Read `.claude/skills/release/SKILL.md`, and do what its "Pick and check the version" and
"Write the notes" sections say. Pick the version yourself, and never a release candidate.
The workflow already checked that no release PR is open.

Don't change any file: you can't, and the workflow writes `CHANGELOG.md` and sets the
version. Instead, answer with:

- version: the version you picked
- reason: one or two sentences, for the PR body, on why you picked it
- notes: the body of the version's `CHANGELOG.md` section, without its `# Version` heading

If a check fails, answer with an empty version, and the failure as the reason.
"""


def fetch_identity_token(url: str, bearer: str, path: Path) -> None:
    request = urllib.request.Request(
        f"{url}&audience={AUDIENCE}", headers={"Authorization": f"Bearer {bearer}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.load(response)["value"]
    # Replace the file in one step, so Claude Code never reads half a token.
    partial = path.with_suffix(".partial")
    partial.write_text(token)
    partial.replace(path)


def refresh(url: str, bearer: str, path: Path, stop: threading.Event) -> None:
    while not stop.wait(REFRESH_SECONDS):
        try:
            fetch_identity_token(url, bearer, path)
        except OSError as e:
            print(f"::warning title=OIDC token::refresh failed: {e}", flush=True)


def output(**values: str) -> None:
    """Write values to GITHUB_OUTPUT, each with a delimiter Claude's text can't contain."""
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for key, value in values.items():
            delimiter = f"EOF_{secrets.token_hex(16)}"
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main() -> int:
    env = dict(os.environ)
    url = env.pop("ACTIONS_ID_TOKEN_REQUEST_URL")
    bearer = env.pop("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    token_file = Path(tempfile.mkdtemp()) / "oidc-token"
    fetch_identity_token(url, bearer, token_file)
    env["ANTHROPIC_IDENTITY_TOKEN_FILE"] = str(token_file)
    stop = threading.Event()
    threading.Thread(target=refresh, args=(url, bearer, token_file, stop), daemon=True).start()

    try:
        result = subprocess.run(
            [
                *("mise", "exec", os.environ["CLAUDE_CODE"], "--", "claude", "--print"),
                *("--model", MODEL, "--output-format", "json"),
                *("--allowedTools", ",".join(TOOLS)),
                *("--json-schema", json.dumps(SCHEMA)),
                PROMPT,
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        stop.set()
    print(result.stderr, file=sys.stderr)
    try:
        message = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"::error title=Claude::no JSON result, exit {result.returncode}")
        print(result.stdout)
        return 1
    answer = message.get("structured_output")
    print(
        f"Claude: {message.get('subtype')}, {message.get('num_turns')} turns, "
        f"${message.get('total_cost_usd', 0):.2f}"
    )
    if message.get("is_error") or not isinstance(answer, dict):
        print(f"::error title=Claude::no answer: {message.get('subtype')}")
        print(message.get("result", ""))
        return 1
    output(**{key: str(answer.get(key, "")) for key in SCHEMA["properties"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
