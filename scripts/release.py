"""What a release is made of: the version in each manifest, and the notes in CHANGELOG.md.

A version is `MAJOR.MINOR.PATCH` for a release, or `MAJOR.MINOR.PATCH-rc.N` for a release
candidate of it. `plugins/antithesis/plugin.json` holds the canonical version.
"""

import re

from report import ROOT

PLUGIN = ROOT / "plugins" / "antithesis"
CANONICAL = PLUGIN / "plugin.json"
MANIFESTS = [
    CANONICAL,
    PLUGIN / ".claude-plugin" / "plugin.json",
    PLUGIN / ".devin-plugin" / "plugin.json",
]
CHANGELOG = ROOT / "CHANGELOG.md"

# Group 1 is MAJOR.MINOR.PATCH, and group 2 is N for a release candidate.
VERSION = re.compile(r"(\d+\.\d+\.\d+)(?:-rc\.(\d+))?")


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
