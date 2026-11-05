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
    """The notes for `version` in a CHANGELOG.md's text, or "" when it has none."""
    match = re.search(
        rf"^# Version {re.escape(version)}(?: \([^\n]*\))?\n(.*?)(?=^# |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""
