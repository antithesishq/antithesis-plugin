"""Where skills live, and how a skill file names the other files it bundles."""

import re
from collections.abc import Iterator
from pathlib import Path

from report import ROOT

SKILL_GLOBS = ["plugins/*/skills/*/SKILL.md", ".agents/skills/*/SKILL.md"]
BUNDLED_DIRS = ("references", "scripts", "assets")
# A path from the skill root, in backticks or as a Markdown link target.
_REFERENCE = re.compile(rf"(?:`|\]\()((?:{'|'.join(BUNDLED_DIRS)})/[^`)\s#]+)")
_PLACEHOLDER = re.compile(r"[<>{}*]")


def skills() -> list[Path]:
    """Every SKILL.md in the repo."""
    return sorted(p for g in SKILL_GLOBS for p in ROOT.glob(g))


def is_internal(skill: Path) -> bool:
    """Whether a skill directory is the repo's own tooling, under .agents/, not part of a plugin."""
    return skill.relative_to(ROOT).parts[0] == ".agents"


def references(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line number, path from the skill root) for each file the text names."""
    for number, line in enumerate(text.splitlines(), 1):
        for match in _REFERENCE.finditer(line):
            target = match.group(1).rstrip(".,:;")
            if not _PLACEHOLDER.search(target):
                yield number, target


# A section reference names a heading, or the bold label that opens a list item, in double
# quotes, starting with a capital letter: "Starting up", or "Wait until every node is up".
# It points at the page given right after it, as in `"Types" in \`references/properties/assertions.md\``,
# at another skill's SKILL.md, as in `"Write the title and body" in the \`open-pr\` skill`, or,
# with neither, at the page it's on. A step number, as in "step 2", is never a reference.
# Quote any other literal text that starts with a capital letter in backticks, not double quotes.
_QUOTED = re.compile(r'"([A-Z][^"]{0,80})"')
_PAGE_TARGET = re.compile(r"(?: step| section)? (?:in|on|of) (?:the [a-z ]+ )?`([^`]+\.md)`")
_SKILL_TARGET = re.compile(r"(?: step| section)? (?:in|on|of) the `([a-z0-9-]+)` skill")
_STEP_NUMBER = re.compile(r"\b[Ss]teps? \d+")
_CODE_SPAN = re.compile(r"`[^`]*`")
_HEADING = re.compile(r"^#+\s+(?:\d+\.\s+|Step \d+:\s+)?(.+?)\s*$")
_LIST_LABEL = re.compile(r"^\s*(?:\d+\.|[-*])\s+\*\*(.+?)\*\*")


def _prose_lines(text: str) -> Iterator[tuple[int, str, str]]:
    """Yield (line number, line, line with code spans blanked) for each line outside code fences."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line, _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)


def section_names(text: str) -> set[str]:
    """Every name a section reference can point at on a page: its headings, without a leading
    number such as "2. " or "Step 2: ", and the bold label opening each list item."""
    names: set[str] = set()
    for _, line, _ in _prose_lines(text):
        if m := _HEADING.match(line):
            names.add(m.group(1))
        elif m := _LIST_LABEL.match(line):
            names.add(m.group(1).strip().rstrip(":,."))
    return names


def section_references(text: str) -> Iterator[tuple[int, str, str | None, str | None]]:
    """Yield (line number, name, page path or None, skill name or None) for each section reference."""
    for number, line, prose in _prose_lines(text):
        for m in _QUOTED.finditer(prose):
            after = line[m.end() :]
            page = _PAGE_TARGET.match(after)
            skill = _SKILL_TARGET.match(after)
            yield number, line[m.start(1) : m.end(1)], page and page.group(1), skill and skill.group(1)


def step_numbers(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line number, match) for each step number used outside headings and code."""
    for number, line, prose in _prose_lines(text):
        if not line.startswith("#"):
            for m in _STEP_NUMBER.finditer(prose):
                yield number, m.group(0)
