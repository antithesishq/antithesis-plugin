"""Flag filler phrases in skill pages, the words an agent reads and gains nothing from.

Every skill file in the repo is checked, outside code fences and code spans. Each phrase
comes with what to write instead. "Writing skill pages" in AGENTS.md is the guidance this
checks a small part of.
"""

import re

from report import ROOT, error
from skills import prose_lines, skills

# (pattern, what to write instead). Matched case-insensitively, on word boundaries.
FILLER: list[tuple[str, str]] = [
    (r"in order to", "write `to`"),
    (r"so as to", "write `to`"),
    (r"due to the fact that", "write `because`"),
    (r"the fact that", "name the fact directly"),
    (r"in the event that", "write `if`"),
    (r"whether or not", "write `whether`"),
    (r"(?:is|are|be) able to", "write `can`"),
    (r"a (?:large )?number of", "write `several`, `many`, or the number"),
    (r"at this point in time", "write `now`, or drop it"),
    (r"prior to", "write `before`"),
    (r"(?:make|be) sure to", "give the instruction directly"),
    # At the start of a sentence, so "only note that it's closed" passes.
    (r"(?:(?<=^)|(?<=[.!?:] )|(?<=- )|(?<=\* ))(?:please )?note that", "drop it, and state the point"),
    (r"keep in mind(?: that)?", "drop it, and state the point"),
    (
        r"it(?: is|'s) (?:important|crucial|essential|worth noting) (?:to|that)",
        "drop it, and state the point",
    ),
    (r"it(?: is|'s) (?:recommended|advisable) (?:to|that)", "give the instruction directly"),
    (
        r"as (?:mentioned|noted|described|stated) (?:above|below|earlier|previously)",
        "name the part, or drop it",
    ),
    (r"feel free to", "write `you can`, or drop it"),
    (r"please", "drop it"),
    (r"simply", "drop it"),
    (r"basically", "drop it"),
    (r"essentially", "drop it"),
    (r"actually", "drop it"),
    (r"really", "drop it"),
    (r"very", "drop it, or use a stronger word"),
    (r"obviously", "drop it"),
    (r"of course", "drop it"),
    (r"clearly", "drop it"),
    (r"furthermore|moreover|additionally", "drop it, or write `also`"),
]
_FILLER = [(re.compile(rf"\b{pattern}\b", re.IGNORECASE), fix) for pattern, fix in FILLER]


def main() -> int:
    found = 0
    for skill_md in skills():
        for path in sorted(skill_md.parent.rglob("*.md")):
            for number, _, prose in prose_lines(path.read_text()):
                for pattern, fix in _FILLER:
                    for match in pattern.finditer(prose):
                        found += 1
                        message = f"filler `{match.group(0)}`: {fix}"
                        error("prose", message, path.relative_to(ROOT), number, match.start() + 1)
    return 1 if found else 0
