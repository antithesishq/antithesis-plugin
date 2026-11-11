#!/usr/bin/env -S uv run --quiet --locked
"""Tag a merged release PR's commit, and run the Release workflow for the tag.

    scripts/tag-release.py COMMIT

The Tag release workflow (.github/workflows/tag-release.yml) runs this when a PR from a
`release/` branch merges, with the merge commit. The tag's version is the one the plugin's
manifest holds at COMMIT, so a version changed in review is still the one tagged. It checks
COMMIT with scripts/verify-release.py, pushes `vX.Y.Z` as an annotated tag, and dispatches
release.yml on it: a tag that GITHUB_TOKEN pushes starts no workflow on its own. When the
tag is already on COMMIT, as on a rerun, it only dispatches release.yml.
"""

import sys

import release
from report import ROOT, run


def out(*args: str) -> str:
    result = run(*args, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main() -> int:
    if len(sys.argv) != 2:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    commit = sys.argv[1]
    canonical = release.CANONICAL.relative_to(ROOT).as_posix()
    version = release.version_in(release.CANONICAL, out("git", "show", f"{commit}:{canonical}"))
    tag = f"v{version}"
    if run("scripts/verify-release.py", tag, commit, "origin/main").returncode != 0:
        return 1
    # verify-release.py passed, so a tag already there is on COMMIT: a rerun after the push
    # only needs to start Release.
    if not out("git", "tag", "-l", tag):
        bot = "github-actions[bot]"
        out(
            *("git", "-c", f"user.name={bot}"),
            *("-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"),
            *("tag", "-a", tag, commit, "-m", f"antithesis plugin {version}"),
        )
        out("gh", "auth", "setup-git")
        out("git", "push", "origin", f"refs/tags/{tag}")
    out("gh", "workflow", "run", "release.yml", "--ref", tag)
    print(f"Tagged {commit[:12]} as {tag}, and started Release for it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
