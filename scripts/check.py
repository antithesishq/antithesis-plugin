#!/usr/bin/env -S uv run --quiet --locked
"""Run one of the repo's checks: `scripts/check.py <check>`.

mise.toml defines a `check:<name>` task for each, and `mise run check` runs them all.
See report.py for the environment settings every check follows.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import references
import release
import tokens
from report import ANNOTATE, OFFLINE, ROOT, VERBOSE, error, run, say

CHECKS: dict[str, Callable[[], int]] = {}
SKILL_DIRS = ["plugins/antithesis/skills", ".agents/skills"]
PLUGIN_JSON = ROOT / "plugins/antithesis/plugin.json"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def check(fn: Callable[[], int]) -> Callable[[], int]:
    CHECKS[fn.__name__] = fn
    return fn


@check
def typos() -> int:
    if VERBOSE:
        files = run("typos", "--files", capture_output=True).stdout.split()
        print("typos checks these files:", *(f"  {f.removeprefix('./')}" for f in files), sep="\n")
    result = run("typos", "--format", "json", capture_output=True)
    for line in result.stdout.splitlines():
        found = json.loads(line)
        if found.get("type") != "typo":
            continue
        corrections = found.get("corrections")
        if isinstance(corrections, list) and corrections:
            message = f"`{found.get('typo')}` should be " + " or ".join(f"`{c}`" for c in corrections)
        else:
            message = f"`{found.get('typo')}` is a typo"
        # A typo in a file name has no line: report it against the file.
        line = found.get("line_num") or None
        col = found["byte_offset"] + 1 if line and "byte_offset" in found else None
        error("typos", message, found.get("path", "."), line, col)
    return result.returncode


# markdownlint-cli2 prints a finding as: path:line[:col] [error] MDxxx/alias description
MARKDOWNLINT_FINDING = re.compile(r"^(\S+?):(\d+)(?::(\d+))? (?:error |warning )?(MD\d+/\S+) (.*)$")


@check
def markdownlint() -> int:
    if not ANNOTATE:
        return run("markdownlint-cli2").returncode
    result = run("markdownlint-cli2", capture_output=True)
    for line in (result.stdout + result.stderr).splitlines():
        print(line)
        if match := MARKDOWNLINT_FINDING.match(line):
            path, row, col, rule, message = match.groups()
            error(rule, message, path, int(row), int(col) if col else None)
    return result.returncode


@check
def skillcheck() -> int:
    if not ANNOTATE:
        return run("skillcheck", "lint", "--fail-on", "warning", "--format", "pretty", *SKILL_DIRS).returncode
    # The github format prints only annotations, so print the full report first.
    if VERBOSE:
        run("skillcheck", "lint", "--fail-on", "never", "--format", "pretty", *SKILL_DIRS)
    return run("skillcheck", "lint", "--fail-on", "warning", "--format", "github", *SKILL_DIRS).returncode


@check
def lychee() -> int:
    args = ["lychee", "--no-progress", *(["--verbose"] if VERBOSE else [])]
    if OFFLINE:
        return run(*args, "--offline", ".").returncode
    if not ANNOTATE:
        return run(*args, ".").returncode
    # The JSON report has every finding to annotate, and with --verbose every success too.
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "lychee.json"
        status = run(*args, "--format", "json", "--output", output, ".").returncode
        report = json.loads(output.read_text())
    # Successes include links reached through redirects; redirect_map only details the hops.
    for kind in ("success_map", "error_map"):
        for file, links in (report.get(kind) or {}).items():
            for link in links:
                status_text = (link.get("status") or {}).get("text", "?")
                span = link.get("span") or {}
                if VERBOSE:
                    where = Path(file).as_posix().removeprefix(f"{ROOT}/").removeprefix("./")
                    print(f"[{status_text}] {link.get('url')} ({where}:{span.get('line', '?')})")
                if kind == "error_map":
                    error(
                        "lychee",
                        f"{link.get('url')}: {status_text}",
                        file,
                        span.get("line", 1),
                        span.get("column"),
                    )
    return status


# A snouty docs path, such as `/docs/reference/sdk/`, not the path part of a URL.
DOCS_PATH = re.compile(r"(?<![\w.])/docs/[\w./-]*\w/?")


@check
def docs() -> int:
    """Every docs path the plugin names resolves with `snouty docs show`."""
    if shutil.which("snouty") is None:
        error("snouty docs", "snouty isn't on PATH; install it to check the docs paths", "mise.toml")
        return 1
    if OFFLINE and run("snouty", "docs", "sqlite", "--offline", capture_output=True).returncode != 0:
        print("Skipped offline: there is no local copy of the docs. CI checks the docs paths.")
        return 0
    found: dict[str, tuple[Path, int]] = {}
    for file in sorted((ROOT / "plugins").rglob("*.md")):
        for number, line in enumerate(file.read_text().splitlines(), 1):
            for match in DOCS_PATH.finditer(line):
                found.setdefault(match.group(), (file, number))
    status = 0
    # The first lookup refreshes the local copy, unless offline; the rest read it.
    for index, (path, (file, number)) in enumerate(sorted(found.items())):
        flags = [] if index == 0 and not OFFLINE else ["--offline"]
        if run("snouty", "docs", "show", *flags, path, capture_output=True).returncode == 0:
            if VERBOSE:
                print(f"[ok] {path}")
        elif OFFLINE:
            # The local copy may predate the page, so only an online run can tell.
            where = f"{Path(file).relative_to(ROOT)}:{number}"
            print(f"warning: {where}: the local docs copy has no {path}; an online run checks it")
        else:
            error("snouty docs", f"`snouty docs show {path}` finds no page", file, number)
            status = 1
    say(f"Checked {len(found)} docs paths with snouty")
    return status


@check
def versions() -> int:
    status = run(sys.executable, "scripts/set-version.py", "--check").returncode
    if status == 0:
        say(f"Every manifest and SKILL.md are at version {json.loads(PLUGIN_JSON.read_text())['version']}")
    return status


@check
def changelog() -> int:
    version = json.loads(release.CANONICAL.read_text())["version"]
    # Before the first release there is no CHANGELOG.md, and nothing to check.
    if not release.CHANGELOG.exists():
        say("No CHANGELOG.md yet, so there is nothing to check")
        return 0
    text = release.CHANGELOG.read_text()
    # MD025 is off for CHANGELOG.md, so this catches a stray top-level heading instead.
    stray = release.stray_headings(text)
    for number, line in stray:
        error(
            "changelog",
            f"`{line}` would end the section above it: top-level headings are only"
            " `# Version X.Y.Z (YYYY-MM-DD)`",
            release.CHANGELOG,
            number,
        )
    if stray:
        return 1
    # At most one release candidate's section floats, at the top, while the version is
    # that candidate's. The next candidate replaces it, and the release replaces it with
    # the release's own notes.
    sections = release.versions(text)
    candidates = [v for v in sections if release.VERSION.fullmatch(v) and "-rc." in v]
    if candidates and (len(candidates) > 1 or sections[0] != version):
        error(
            "changelog",
            f"release candidate sections for {', '.join(candidates)}, and the"
            f" version is {version}. Keep one, the top section, for the current release"
            " candidate only: the next candidate replaces it, and the release replaces it"
            " with its own notes",
            release.CHANGELOG,
        )
        return 1
    # Without gh, or when gh can't tell, treat the version as unreleased and check its notes.
    has_gh = shutil.which("gh") is not None
    if has_gh and run("gh", "release", "view", f"v{version}", capture_output=True).returncode == 0:
        say(f"v{version} is already released")
        return 0
    if not release.section(text, version):
        error("changelog", f"no notes for the unreleased {version}", release.CHANGELOG)
        return 1
    say(f"CHANGELOG.md has notes for the unreleased v{version}")
    return 0


@check
def schema() -> int:
    if OFFLINE:
        print("Skipped offline: the schema is downloaded. CI validates it.")
        return 0
    return run(
        "check-jsonschema", *(["-vv"] if VERBOSE else []), "--schemafile", SCHEMA, PLUGIN_JSON
    ).returncode


@check
def plugin() -> int:
    status = 0
    for target in (".", "plugins/antithesis"):
        status |= run("claude", "plugin", "validate", "--strict", target).returncode
    return status


@check
def ruff() -> int:
    if ANNOTATE:
        # ruff's own github format uses absolute paths; annotate from its JSON instead.
        linted = run("ruff", "check", "--output-format", "json", capture_output=True)
        for finding in json.loads(linted.stdout or "[]"):
            location = finding.get("location") or {}
            message = f"{finding.get('code')} {finding.get('message')}"
            print(f"{finding['filename']}:{location.get('row')}:{location.get('column')}: {message}")
            error(
                f"ruff ({finding.get('code')})",
                finding.get("message", ""),
                finding["filename"],
                location.get("row"),
                location.get("column"),
            )
        lint = linted.returncode
    else:
        lint = run("ruff", "check").returncode
    formatted = run("ruff", "format", "--check", capture_output=True)
    print(formatted.stdout + formatted.stderr, end="")
    for line in formatted.stdout.splitlines():
        if line.startswith("Would reformat: "):
            error(
                "ruff format", "not formatted; run `mise run fix:ruff`", line.removeprefix("Would reformat: ")
            )
    return lint or formatted.returncode


@check
def pyright() -> int:
    if not ANNOTATE:
        return run("pyright", *(["--verbose"] if VERBOSE else [])).returncode
    result = run("pyright", "--outputjson", capture_output=True)
    report = json.loads(result.stdout)
    for diagnostic in report.get("generalDiagnostics", []):
        start = diagnostic.get("range", {}).get("start", {})
        line, col = start.get("line", 0) + 1, start.get("character", 0) + 1
        where = f"{Path(diagnostic['file']).relative_to(ROOT)}:{line}:{col}"
        print(f"{where} {diagnostic['severity']}: {diagnostic['message']}")
        if diagnostic["severity"] == "error":
            rule = diagnostic.get("rule") or "pyright"
            error(rule, diagnostic["message"], diagnostic["file"], line, col)
    summary = report.get("summary", {})
    print(
        f"pyright: {summary.get('filesAnalyzed', '?')} files, {summary.get('errorCount', '?')} errors, "
        f"{summary.get('warningCount', '?')} warnings"
    )
    return result.returncode


@check
def references_() -> int:
    return references.main()


@check
def tokens_() -> int:
    return tokens.main()


def main() -> int:
    names = {name.rstrip("_"): fn for name, fn in CHECKS.items()}
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("check", choices=sorted(names))
    return names[parser.parse_args().check]()


if __name__ == "__main__":
    sys.exit(main())
