#!/usr/bin/env -S uv run --quiet --locked
"""Print the CHANGELOG.md notes for one version.

    scripts/changelog-section.py 1.2.3

Prints the body of the `# Version 1.2.3 (YYYY-MM-DD)` section, and exits 1 if there is none.
A release candidate's version, like 1.2.3-rc.1, works the same way.
"""

import sys

from release import CHANGELOG, section


def main() -> int:
    if len(sys.argv) != 2:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    notes = section(CHANGELOG.read_text() if CHANGELOG.exists() else "", sys.argv[1])
    if not notes:
        print(f"CHANGELOG.md has no notes for version {sys.argv[1]}", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
