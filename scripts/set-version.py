#!/usr/bin/env -S uv run --quiet --locked
"""Set or check the plugin version in every manifest, and in the skill's SKILL.md.

`plugins/antithesis/plugin.json` holds the canonical version.

    scripts/set-version.py 1.2.3       write 1.2.3 into every file that holds the version
    scripts/set-version.py 1.2.3-rc.1  write a release candidate's version
    scripts/set-version.py --check     exit 1 if a file disagrees with the canonical version
"""

import sys

from release import CANONICAL, VERSION, VERSIONED, field, version_in
from report import ROOT


def main() -> int:
    if sys.argv[1:] == ["--check"]:
        expected = version_in(CANONICAL, CANONICAL.read_text())
        wrong = [p for p in VERSIONED if version_in(p, p.read_text()) != expected]
        for path in wrong:
            print(f"{path.relative_to(ROOT)}: version is not {expected}")
        return 1 if wrong else 0
    if len(sys.argv) != 2 or not VERSION.fullmatch(sys.argv[1]):
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    for path in VERSIONED:
        text, count = field(path).subn(rf"\g<1>{sys.argv[1]}\g<3>", path.read_text(), count=1)
        if count != 1:
            print(f"{path}: no version field", file=sys.stderr)
            return 1
        path.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
