"""Check the file references inside every skill.

Skills name their bundled files as paths from the skill root, usually in backticks
(`references/triage/MODULE.md`) and sometimes as Markdown links. For each skill this
fails when a referenced file doesn't exist, or when a bundled file can't be reached
from SKILL.md by following references, at any depth.
"""

from pathlib import Path

from report import ROOT, error, say
from skills import BUNDLED_DIRS, is_internal, references, skills


def check_skill(skill_md: Path) -> int:
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
    problems = sum(check_skill(s) for s in found)
    if not problems:
        print(f"{len(found)} skills: every reference resolves and every file is reachable")
    return 1 if problems else 0
