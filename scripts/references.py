"""Check the file references inside every skill.

Skills name their bundled files as paths from the skill root, usually in backticks
(`references/triage/MODULE.md`) and sometimes as Markdown links. For each skill this
fails when a referenced file doesn't exist, or when a bundled file can't be reached
from SKILL.md by following references, at any depth.

It also checks section references, a heading or a list item's bold label in double quotes,
such as "Starting up" in `references/workload/driver.md`: each must name a heading or label
on the page it points at, or a table row's first cell. An image placeholder such as
`<Rust build image>` must name a row of the skill's image table. Steps are referred to by name, so a step number such as "step 2"
fails, since reordering a list would silently change what it points at.
"""

import re
from pathlib import Path

from report import ROOT, error, say
from skills import (
    BUNDLED_DIRS,
    IMAGES_PAGE,
    image_placeholders,
    is_internal,
    references,
    section_names,
    section_references,
    skills,
    step_numbers,
)


def check_sections(skill: Path, source: Path, by_name: dict[str, Path]) -> int:
    """Check each section reference and step number on one page."""
    problems = 0
    text = source.read_text()
    # A shipped skill's install holds only its own plugin, so it may point only at its own
    # files and at skills in the same plugin. A repo-internal skill may name any repo file.
    internal = is_internal(skill)
    for line, name, page, other in section_references(text):
        if other:
            target = by_name.get(other)
            if target is not None and not internal and target.parent.parent != skill.parent:
                target = None
            where = f"the `{other}` skill"
        elif page:
            target = skill / page
            if internal and not target.is_file():
                target = ROOT / page
            where = f"`{page}`"
        else:
            target, where = source, "this page"
        if target is not None and "<" in str(target):
            # A placeholder, as in `references/workload/languages/<language>.md`, names
            # every page that fits it, and the section must be on each of them.
            matches = sorted(target.parent.glob(re.sub(r"<[^>]*>", "*", target.name)))
            missing = [m for m in matches if name not in section_names(m.read_text())]
            if not matches or missing:
                pages = ", ".join(f"`{m.relative_to(skill)}`" for m in missing) or "no page"
                error(
                    "check-references",
                    f'"{name}" is not a heading, list label or table row on {pages}',
                    source,
                    line,
                )
                problems += 1
            continue
        if target is None or not target.is_file():
            error(
                "check-references", f'"{name}" points at {where}, which this skill can\'t reach', source, line
            )
            problems += 1
        elif name not in section_names(target.read_text()):
            error(
                "check-references",
                f'"{name}" is not a heading, list label or table row on {where}',
                source,
                line,
            )
            problems += 1
    images = skill / IMAGES_PAGE
    rows = section_names(images.read_text()) if images.is_file() else set()
    for line, row in image_placeholders(text):
        if row not in rows:
            error("check-references", f"`<{row}>` is not a row in `{IMAGES_PAGE}`", source, line)
            problems += 1
    for line, match in step_numbers(text):
        error(
            "check-references",
            f'"{match}" refers to a step by number: name it by its heading or bold label instead',
            source,
            line,
        )
        problems += 1
    return problems


def check_skill(skill_md: Path, by_name: dict[str, Path]) -> int:
    skill = skill_md.parent
    # A repo-internal skill may name the repo's own files, such as `scripts/set-version.py`.
    # A shipped skill may not: its install has only what the skill bundles.
    internal = is_internal(skill)
    bundled = {p for d in BUNDLED_DIRS for p in (skill / d).rglob("*") if p.is_file()}
    problems = 0
    reached: set[Path] = set()
    queue = [skill_md]
    while queue:
        source = queue.pop()
        if source in reached:
            continue
        reached.add(source)
        if source.suffix != ".md":
            continue
        problems += check_sections(skill, source, by_name)
        found = sorted(set(references(source.read_text())))
        say(f"{source.relative_to(ROOT)}: {len(found)} references")
        for line, target in found:
            say(f"  line {line}: {target}")
            path = skill / target
            if path.is_file():
                queue.append(path)
            elif not path.is_dir() and not (internal and (ROOT / target).exists()):
                error("check-references", f"`{target}` does not exist in skill `{skill.name}`", source, line)
                problems += 1
    for path in sorted(bundled - reached):
        rel = path.relative_to(skill).as_posix()
        error("check-references", f"`{rel}` is not reachable from {skill.name}/SKILL.md", path, 1)
        problems += 1
    return problems


def main() -> int:
    found = skills()
    by_name = {s.parent.name: s for s in found}
    problems = sum(check_skill(s, by_name) for s in found)
    if not problems:
        print(f"{len(found)} skills: every reference resolves and every file is reachable")
    return 1 if problems else 0
