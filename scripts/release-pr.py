#!/usr/bin/env -S uv run --quiet --locked
"""The deterministic half of the Release PR workflow (.github/workflows/release-pr.yml).

    scripts/release-pr.py gate
    scripts/release-pr.py open VERSION    (VERSION may be empty: Claude stopped)

`gate` decides whether to release the default branch's head, HEAD. It releases only when:

- no release PR, from a `release/` branch, is open
- the latest CI run on HEAD completed and passed
- something users get changed since the last release reachable from HEAD, skipping
  release candidates

It writes `release=true` or `false`, and the last tag as `previous`, to GITHUB_OUTPUT, and
exits 0 either way: a day with nothing to release isn't a failure.

`open` runs in a clean checkout, in a job apart from Claude's, after Claude picked VERSION
and wrote its NOTES following the release skill. It checks them, adds the notes to
`CHANGELOG.md`, sets the version with scripts/set-version.py, commits to `release/vVERSION`,
pushes, and opens a PR assigned to RELEASE_REVIEWER, with REASON (why Claude picked the
version) and PREVIOUS (the last tag) in its body. A PR that GITHUB_TOKEN
opens runs no CI on its own, so it then dispatches CI on the branch, which gives the PR's
head commit the `check` status that the default branch requires.
"""

import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import release
from report import ROOT, run

# What users get from the plugin, as the release skill's "Write the notes" reads it.
USER_FACING = [
    "plugins/antithesis/",
    ".claude-plugin/",
    ".agents/plugins/",
    "README.md",
    "docs/",
]
# The workflow runs at 17:00 in this zone, so a release is dated with its day there.
RELEASE_TZ = timezone(timedelta(hours=-7))
# Credentials that Claude's job could read: GitHub tokens, Anthropic tokens and keys, and
# JWTs such as an OIDC token. Notes that hold one would publish it in the PR.
SECRET = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-ant-[\w-]{20,}|eyJ[\w-]{10,}\.eyJ")
RELEASE_FILES = {p.relative_to(ROOT).as_posix() for p in [*release.VERSIONED, release.CHANGELOG]}


def out(*args: str) -> str:
    result = run(*args, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def output(**values: str) -> None:
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a") as f:
            f.writelines(f"{key}={value}\n" for key, value in values.items())


def open_release_prs() -> list[str]:
    prs = json.loads(
        out(
            *("gh", "pr", "list", "--state", "open", "--limit", "1000"),
            *("--json", "url,headRefName,isCrossRepository"),
        )
    )
    # A fork's branch is named without its owner, so a fork could otherwise block releases.
    return [
        pr["url"] for pr in prs if pr["headRefName"].startswith("release/") and not pr["isCrossRepository"]
    ]


# A link that's briefly down fails only this check. CI on a push tolerates it, and the
# nightly run doesn't, so the gate tolerates it too.
FLAKY_CHECK = "check:lychee"
# The job that sums up every check, which fails whenever one does.
SUMMARY_CHECK = "check"


def ci_passed(sha: str) -> str | None:
    """None when the latest CI run on sha passed, otherwise why not."""
    runs = json.loads(
        out("gh", "api", f"repos/{{owner}}/{{repo}}/actions/workflows/ci.yml/runs?head_sha={sha}")
    )["workflow_runs"]
    if not runs:
        return f"CI hasn't run on {sha[:12]}"
    latest = max(runs, key=lambda r: r["created_at"])
    if latest["status"] != "completed":
        return f"CI on {sha[:12]} is still {latest['status']}: {latest['html_url']}"
    if latest["conclusion"] == "success":
        return None
    jobs = json.loads(
        out("gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs/{latest['id']}/jobs?per_page=100")
    )["jobs"]
    failed = [
        j["name"]
        for j in jobs
        if j["conclusion"] not in ("success", "skipped", "neutral") and j["name"] != SUMMARY_CHECK
    ]
    if failed and all(name.endswith(FLAKY_CHECK) for name in failed):
        print(f"CI on {sha[:12]} failed only {FLAKY_CHECK}, which a release tolerates")
        return None
    return f"CI on {sha[:12]} concluded {latest['conclusion']}: {latest['html_url']}"


def gate() -> int:
    sha = out("git", "rev-parse", "HEAD")
    # The last release, skipping candidates, as the release skill finds it.
    previous = out(
        *("git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"),
        *("--exclude", "*-rc*", "HEAD"),
    )
    output(previous=previous)

    if prs := open_release_prs():
        reason = f"a release PR is already open: {', '.join(prs)}"
    elif failed := ci_passed(sha):
        reason = failed
    elif run("git", "diff", "--quiet", previous, sha, "--", *USER_FACING).returncode == 0:
        reason = f"nothing users get has changed since {previous}"
    else:
        print(f"Releasing {sha[:12]}: CI passed, and it changes the plugin since {previous}")
        output(release="true")
        return 0
    print(f"::notice title=No release today::{reason}")
    output(release="false")
    return 0


def escape(text: str) -> str:
    """Text for a workflow command's message, on one line."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def version_key(version: str) -> tuple[int, int, int, float]:
    """Sorts versions: a candidate sorts below its release, as the release skill says."""
    match = release.VERSION.fullmatch(version)
    if not match:
        raise ValueError(version)
    major, minor, patch = (int(part) for part in match.group(1).split("."))
    return major, minor, patch, int(match.group(2)) if match.group(2) else math.inf


def with_section(changelog: str, version: str, notes: str) -> str:
    """CHANGELOG.md's text with a section for version on top, below the HTML comments.

    It replaces a candidate's section at the top, as the release skill does.
    """
    today = datetime.now(RELEASE_TZ).date().isoformat()
    section = f"# Version {version} ({today})\n\n{notes.strip()}\n\n"
    top = re.search(r"^# Version (\S+).*\n", changelog, re.MULTILINE)
    if not top:
        return changelog.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n"
    start = top.start()
    if "-rc." in top.group(1):
        following = re.search(r"^# ", changelog[top.end() :], re.MULTILINE)
        end = top.end() + following.start() if following else len(changelog)
        rest = changelog[end:]
    else:
        rest = changelog[start:]
    return (changelog[:start] + section + rest).rstrip("\n") + "\n"


def open_pr(version: str) -> int:
    """Write Claude's notes and the version from a clean checkout, and open the PR.

    Claude's job can't write to the repository: it returns the version, its reason and the
    notes, and this checks them, so nothing Claude touched runs here.
    """
    tag = f"v{version}"
    notes = os.environ.get("NOTES", "").strip()
    reason = os.environ.get("REASON", "").strip()
    if not version:
        # Claude stopped at a failed check. Escaped, so its text can't start a workflow command.
        print(f"::error title=No release::{escape(reason) or 'Claude picked no version'}")
        return 1
    current = release.version_in(release.CANONICAL, release.CANONICAL.read_text()) or ""
    failures = []
    match = release.VERSION.fullmatch(version)
    if not match or match.group(2):
        failures.append(f"{version!r} is not MAJOR.MINOR.PATCH")
    elif version_key(version) <= version_key(current):
        failures.append(f"{version} is not above the current version, {current}")
    if not notes:
        failures.append("Claude wrote no notes")
    if re.search(r"^# ", notes, re.MULTILINE):
        failures.append("the notes have a top-level heading, which would split the section")
    for text in (notes, reason):
        if found := SECRET.search(text):
            failures.append(f"the notes or reason hold what looks like a credential: {found[0][:8]}…")
    if out("git", "tag", "-l", tag):
        failures.append(f"{tag} already exists")
    if failures:
        for failure in failures:
            print(f"::error title=Release PR::{escape(failure)}")
        return 1

    release.CHANGELOG.write_text(with_section(release.CHANGELOG.read_text(), version, notes))
    out("scripts/set-version.py", version)
    out("scripts/set-version.py", "--check")
    if not release.section(release.CHANGELOG.read_text(), version):
        print(f"::error title=Release PR::CHANGELOG.md has no notes for {version}")
        return 1

    branch = f"release/{tag}"
    title = f"Release antithesis plugin {version}"
    reviewer = os.environ["RELEASE_REVIEWER"]
    previous = os.environ["PREVIOUS"]
    body = (
        f"Releases antithesis plugin {version}. The notes cover what changed since "
        f"{previous}. {reason}\n\n"
        "The Release PR workflow opened this PR on its own: Claude picked the version and "
        "wrote the notes by following the `release` skill. To change the version, run "
        "`scripts/set-version.py` and rename the `CHANGELOG.md` heading. Merging ships the "
        "version to every user, and then the Tag release workflow tags the merge commit, "
        "which runs Release to create the GitHub release.\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    )
    bot = "github-actions[bot]"
    out("git", "switch", "-c", branch)
    out("git", "add", *sorted(RELEASE_FILES))
    out(
        *("git", "-c", f"user.name={bot}"),
        *("-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"),
        *("commit", "-m", f"{title}\n\nCo-Authored-By: Claude <noreply@anthropic.com>"),
    )
    out("gh", "auth", "setup-git")
    # The gate found no open release PR, so a branch already there is left from one that
    # closed without merging. A merged one would have tagged the version.
    if run("git", "ls-remote", "--exit-code", "--heads", "origin", branch).returncode == 0:
        print(f"Replacing {branch}, left from a closed release PR")
    out("git", "push", "--force", "-u", "origin", branch)

    url = out(
        *("gh", "pr", "create", "--base", "main", "--head", branch, "--title", title),
        *("--body", body, "--assignee", reviewer, "--reviewer", reviewer),
    )
    print(f"Opened {url}")
    out("gh", "workflow", "run", "ci.yml", "--ref", branch)
    return 0


def main() -> int:
    match sys.argv[1:]:
        case ["gate"]:
            return gate()
        case ["open", version]:
            return open_pr(version)
        case _:
            print((__doc__ or "").strip(), file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main())
