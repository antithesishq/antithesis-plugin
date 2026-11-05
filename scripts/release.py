"""What a release is made of: the version in each manifest, and the notes in CHANGELOG.md.

A version is `MAJOR.MINOR.PATCH` for a release, or `MAJOR.MINOR.PATCH-rc.N` for a release
candidate of it. `plugins/antithesis/plugin.json` holds the canonical version.
"""

import json
import re
from pathlib import Path

from report import ROOT

PLUGIN = ROOT / "plugins" / "antithesis"
CANONICAL = PLUGIN / "plugin.json"
MANIFESTS = [
    CANONICAL,
    PLUGIN / ".claude-plugin" / "plugin.json",
    PLUGIN / ".devin-plugin" / "plugin.json",
]
# SKILL.md states the version too, for agents that can't see the manifests, such as
# the launch module, which records it on every run.
SKILL = PLUGIN / "skills" / "antithesis" / "SKILL.md"
VERSIONED = [*MANIFESTS, SKILL]
CHANGELOG = ROOT / "CHANGELOG.md"

# Group 1 is MAJOR.MINOR.PATCH, and group 2 is N for a release candidate.
VERSION = re.compile(r"(\d+\.\d+\.\d+)(?:-rc\.(\d+))?")

# Where each file of VERSIONED holds the version: group 2, between groups 1 and 3.
JSON_FIELD = re.compile(r'("version":\s*")([^"]*)(")')
SKILL_LINE = re.compile(r"^(Plugin version: `)([^`]*)(`)$", re.MULTILINE)


def field(path: Path) -> re.Pattern[str]:
    return JSON_FIELD if path.suffix == ".json" else SKILL_LINE


def version_in(path: Path, text: str) -> str | None:
    """The version in the text of a file of VERSIONED, or None when it has none."""
    if path.suffix == ".json":
        return json.loads(text).get("version")
    match = SKILL_LINE.search(text)
    return match.group(2) if match else None


def versions(changelog: str) -> list[str]:
    """The version of every `# Version` section in a CHANGELOG.md's text, top first."""
    return re.findall(r"^# Version (\S+)", changelog, re.MULTILINE)


def section(changelog: str, version: str) -> str:
    """The notes for `version` in a CHANGELOG.md's text, or "" when it has none.

    A section ends at the next top-level heading. HTML comments are left out of the notes.
    """
    match = re.search(
        rf"^# Version {re.escape(version)}(?: \([^\n]*\))?\n(.*?)(?=^# |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    return re.sub(r"<!--.*?-->", "", match.group(1), flags=re.DOTALL).strip() if match else ""


def stray_headings(changelog: str) -> list[tuple[int, str]]:
    """Each top-level heading that isn't `# Version X (date)`, with its line number.

    One would end the section above it early, and cut that version's notes short.
    """
    heading = re.compile(rf"# Version {VERSION.pattern}(?: \([^\n]*\))?")
    return [
        (number, line)
        for number, line in enumerate(changelog.splitlines(), 1)
        if line.startswith("# ") and not heading.fullmatch(line)
    ]
