#!/usr/bin/env -S uv run --quiet --locked
"""Check that a commit can be released under a tag.

    scripts/verify-release.py vX.Y.Z COMMIT BRANCH
    scripts/verify-release.py vX.Y.Z-rc.N COMMIT BRANCH

Reads the files at COMMIT, not the working tree, so the release skill runs it before it
pushes the tag, and the release workflow runs it again on the pushed tag. It checks that:

- the tag is `vMAJOR.MINOR.PATCH` or `vMAJOR.MINOR.PATCH-rc.N`, and if it already exists,
  it points at COMMIT
- COMMIT is on BRANCH, such as `origin/main`
- every manifest at COMMIT has the tag's version
- CHANGELOG.md at COMMIT has notes for that version
- the version has no GitHub release yet

Exits 1 if a check fails. Under GitHub Actions, writes the version, and whether it is a
release candidate (`prerelease=true` or `false`), to GITHUB_OUTPUT.
"""

import json
import os
import sys
from pathlib import Path

import release
from report import ROOT, run


def show(commit: str, path: Path) -> str | None:
    """A file's text at a commit, or None if it doesn't exist there."""
    rel = path.relative_to(ROOT).as_posix()
    result = run("git", "show", f"{commit}:{rel}", capture_output=True)
    return result.stdout if result.returncode == 0 else None


def git(*args: str) -> str | None:
    result = run("git", *args, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    if len(sys.argv) != 4:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    tag, commit, branch = sys.argv[1:]
    match = release.VERSION.fullmatch(tag.removeprefix("v"))
    if not tag.startswith("v") or not match:
        print(f"{tag} is not vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-rc.N")
        return 1
    version = match.group(0)
    prerelease = match.group(2) is not None

    sha = git("rev-parse", "--verify", f"{commit}^{{commit}}")
    if not sha:
        print(f"{commit} is not a commit")
        return 1
    failures = []

    tagged = git("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if tagged and tagged != sha:
        failures.append(f"{tag} already exists, on {tagged}, not {sha}")
    if run("git", "merge-base", "--is-ancestor", sha, branch).returncode != 0:
        failures.append(f"{sha} is not on {branch}")

    for path in release.MANIFESTS:
        text = show(sha, path)
        found = json.loads(text).get("version") if text else None
        if found != version:
            failures.append(f"{path.relative_to(ROOT)} at {sha[:12]} is at {found}, not {version}")

    if not release.section(show(sha, release.CHANGELOG) or "", version):
        failures.append(f"CHANGELOG.md at {sha[:12]} has no notes for {version}")

    released = run("gh", "release", "view", tag, "--json", "tagName", capture_output=True)
    if released.returncode == 0:
        failures.append(f"{tag} is already released")
    elif "release not found" not in released.stderr:
        failures.append(f"gh can't tell whether {tag} is released: {released.stderr.strip()}")

    for failure in failures:
        print(failure)
    if failures:
        return 1
    print(f"{sha} on {branch} can be released as {tag}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as f:
            f.write(f"version={version}\nprerelease={str(prerelease).lower()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
