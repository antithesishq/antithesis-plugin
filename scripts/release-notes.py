#!/usr/bin/env -S uv run --quiet --locked
"""Have Claude pick the next version and write its notes, in the Release PR workflow.

    scripts/release-notes.py

Runs Claude Code, pinned by `claude@VERSION` in CLAUDE_CODE, on the release skill's "Pick
and check the version" and "Write the notes" sections. It answers with the version, its
reason and the notes, which this writes to GITHUB_OUTPUT for the job that opens the PR.

Claude reads text that others wrote, so it gets no shell and can only read. This runs the
commands those sections name first, and saves their output in a context directory. Claude
Code then runs `--restricted`: with only Read, Glob and Grep, confined to the checkout and
that directory. So it can't reach the job's credentials, such as the OIDC request token in
this process's environment, or the identity token file.

Claude Code authenticates with workload identity federation, from the
ANTHROPIC_FEDERATION_RULE_ID, ANTHROPIC_ORGANIZATION_ID, ANTHROPIC_SERVICE_ACCOUNT_ID and
ANTHROPIC_WORKSPACE_ID in the environment. This fetches the job's GitHub OIDC token into
ANTHROPIC_IDENTITY_TOKEN_FILE, and fetches a fresh one every minute: each lives about five
minutes, and Anthropic accepts each only once.
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
TOOLS = "Read,Glob,Grep"
# What users get from the plugin, as "Write the notes" diffs it.
SKILLS = ["plugins/antithesis/skills/"]
INSTALL = [
    "plugins/antithesis/*.json",
    "plugins/antithesis/.*-plugin/",
    ".claude-plugin/",
    ".agents/plugins/",
    "README.md",
    "docs/",
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
"Write the notes" sections say. {version}
The workflow already checked that no release PR is open, and that the checkout is clean.

You can't run commands. The workflow ran the ones those sections name, and saved their
output in {context}: its `README.md` says which file holds which command's output. Read
those files wherever the skill says to run a command.

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


def version_instruction() -> str:
    requested = os.environ.get("REQUESTED_VERSION", "")
    if requested:
        return f"The user asked to release version {requested}: use exactly that version."
    return "Pick the version yourself, and never a release candidate."


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def write_context(directory: Path) -> None:
    """Save the output of each command the skill's sections name, for Claude to read."""
    tags = git("tag", "-l", "v[0-9]*", "--sort=-v:refname")
    previous = next((t for t in tags.split() if "-rc" not in t), None)
    files = {
        "tags.txt": ("git tag -l 'v[0-9]*' --sort=-v:refname", tags),
        "releases.txt": (
            "gh release list --limit 100",
            subprocess.run(
                ["gh", "release", "list", "--limit", "100"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout,
        ),
        "repo-url.txt": ("gh repo view --json url -q .url", os.environ["REPO_URL"] + "\n"),
    }
    if previous:
        span = f"{previous}..HEAD"
        files |= {
            "previous.txt": ("the first tag in tags.txt that isn't a candidate", previous + "\n"),
            "skills.diff": (f"git diff {span} -- {' '.join(SKILLS)}", git("diff", span, "--", *SKILLS)),
            "install.diff": (f"git diff {span} -- {' '.join(INSTALL)}", git("diff", span, "--", *INSTALL)),
            "log.txt": (f"git log --oneline {span}", git("log", "--oneline", span)),
            "commits.patch": (
                f"git log --stat -p {span}",
                git("log", "--stat", "-p", span),
            ),
        }
    readme = [
        "# Command output for the release skill",
        "",
        "`commits.patch` holds every commit as `git show` prints it.",
        "",
    ]
    if not previous:
        readme += ["There is no previous release, so there are no diffs.", ""]
    for name, (command, text) in files.items():
        (directory / name).write_text(text)
        readme.append(f"- `{name}`: {command}")
    (directory / "README.md").write_text("\n".join(readme) + "\n")


def output(**values: str) -> None:
    """Write values to GITHUB_OUTPUT, each with a delimiter Claude's text can't contain."""
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for key, value in values.items():
            delimiter = f"EOF_{secrets.token_hex(16)}"
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main() -> int:
    context = Path(tempfile.mkdtemp(prefix="release-context-"))
    write_context(context)
    # Claude can't reach these anyway: this keeps them out of its process too.
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
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
                # No shell, and file tools only in the checkout and the context directory.
                *("--restricted", "--tools", TOOLS, "--allowedTools", TOOLS),
                *("--add-dir", str(context)),
                # --restricted ignores project settings: this keeps the repo's Stop hook.
                *("--settings", str(ROOT / ".claude" / "settings.json")),
                *("--json-schema", json.dumps(SCHEMA)),
                PROMPT.format(context=context, version=version_instruction()),
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
