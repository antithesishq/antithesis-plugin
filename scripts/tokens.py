"""Report how many tokens each skill file and module costs, and enforce two budgets.

The top level is SKILL.md and the files it names outside any module. It loads in
every context that uses the skill, so it gets a small budget. A module is what its
MODULE.md adds on demand: everything reachable from it, up to another module's
MODULE.md, that the top level doesn't already load. Each budget comes from the
environment, and mise.toml sets both:

    SKILL_TOKEN_BUDGET   (default 2500)
    MODULE_TOKEN_BUDGET  (default 20000)
    MODULE_TOKEN_BUDGETS overrides for named modules, as `name=tokens,...`
    TOKEN_BASE           a git ref: also show the change since it

Counts use tiktoken's o200k_base encoding. Claude's tokenizer differs, so treat them
as estimates for comparing files and changes, not as exact Claude counts. Under
GitHub Actions the report also goes to the job summary.
"""

import os
import subprocess
from collections.abc import Callable
from functools import cache
from pathlib import Path

import tiktoken
from report import ROOT, error
from skills import references, skills

# Matches "Token budgets" in AGENTS.md.
BUDGET_NOTE = (
    "Budgets are soft guidance. Look for a shorter way to say the same thing: cut statements "
    "and words that aren't needed, and rely more on `snouty --help` and `snouty docs`. Never "
    "trade the design for the budget: don't change how pages reference each other, move content "
    "to another module, or leave out something important just to fit. If the right version is "
    "over budget, raise that module's budget in mise.toml (MODULE_TOKEN_BUDGETS), and say so in "
    "the change."
)


def is_module(rel: str) -> bool:
    return rel.endswith("/MODULE.md")


class Tree:
    """The repo's files, either on disk now or at a git ref. Paths are from the repo root."""

    def __init__(self, encoding: tiktoken.Encoding, ref: str | None = None):
        self.encoding = encoding
        self.ref = ref

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)

    @cache  # noqa: B019 - a Tree lives for one run
    def read(self, rel: str) -> str | None:
        if self.ref is None:
            path = ROOT / rel
            return path.read_text() if path.is_file() else None
        result = self._git("show", f"{self.ref}:{rel}")
        return result.stdout if result.returncode == 0 else None

    def markdown(self, directory: str) -> list[str]:
        if self.ref is None:
            return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob("*.md"))
        listed = self._git("ls-tree", "-r", "--name-only", self.ref, "--", directory).stdout
        return [f for f in listed.splitlines() if f.endswith(".md")]

    def tokens(self, rel: str) -> int | None:
        text = self.read(rel)
        return None if text is None else len(self.encoding.encode(text, disallowed_special=()))

    def reachable(self, skill: str, start: str, stop: Callable[[str], bool]) -> set[str]:
        """Files reachable from `start` by following references, not entering `stop` files."""
        seen: set[str] = set()
        queue = [start]
        while queue:
            rel = queue.pop()
            text = self.read(rel)
            if rel in seen or text is None:
                continue
            seen.add(rel)
            for _, target in references(text):
                path = f"{skill}/{target}"
                if path.endswith(".md") and not stop(path):
                    queue.append(path)
        return seen

    def top_level(self, skill: str) -> set[str]:
        """SKILL.md and the files it names outside any module."""
        return self.reachable(skill, f"{skill}/SKILL.md", is_module)

    def top_level_cost(self, skill: str) -> int | None:
        files = self.top_level(skill)
        return sum(self.tokens(rel) or 0 for rel in files) if files else None

    def module_cost(self, skill: str, module_md: str) -> int | None:
        """What the module adds to the top level, which is loaded already."""
        if self.read(module_md) is None:
            return None
        own = self.reachable(skill, module_md, lambda rel: is_module(rel) and rel != module_md)
        return sum(self.tokens(rel) or 0 for rel in own - self.top_level(skill))


def change(now: int | None, before: int | None) -> str:
    if before is None:
        return "new"
    if now is None:
        return f"{-before:+d} (deleted)"
    return f"{now - before:+d}" if now != before else "0"


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|---|" + "---:|" * (len(headers) - 1),
        *("| " + " | ".join(row) + " |" for row in rows),
        "",
    ]


def main() -> int:
    skill_budget = int(os.environ.get("SKILL_TOKEN_BUDGET", "2500"))
    module_budget = int(os.environ.get("MODULE_TOKEN_BUDGET", "20000"))
    overrides = {
        name.strip(): int(tokens)
        for name, tokens in (
            item.split("=", 1)
            for item in os.environ.get("MODULE_TOKEN_BUDGETS", "").split(",")
            if item.strip()
        )
    }
    encoding = tiktoken.get_encoding("o200k_base")
    now = Tree(encoding)
    base = Tree(encoding, os.environ.get("TOKEN_BASE", "").strip() or None)

    def compare(current: int | None, before: int | None) -> list[str]:
        """The change column, when there is a base to compare with."""
        return [change(current, before)] if base.ref else []

    since = [f"Change since `{base.ref[:12]}`"] if base.ref else []
    errors: list[tuple[str, str]] = []
    lines = [
        "## Skill token counts",
        "",
        (
            f"Estimated with tiktoken `o200k_base`. Budgets: top level {skill_budget} "
            f"(SKILL.md and the files it names outside any module), each module {module_budget} "
            "(what its MODULE.md adds), unless the table shows another."
        ),
        "",
    ]
    for skill_md in skills():
        skill = skill_md.parent.relative_to(ROOT).as_posix()
        lines += [f"### `{skill}`", ""]

        top = now.top_level_cost(skill) or 0
        top_before = base.top_level_cost(skill) if base.ref else None
        rows = [["top level", str(top), str(skill_budget), *compare(top, top_before)]]
        if top > skill_budget:
            message = (
                f"the top level (SKILL.md and the files it names outside any module) is {top} tokens; "
                f"the budget is {skill_budget}"
            )
            errors.append((f"{skill}/SKILL.md", message))
        modules = sorted(
            p.relative_to(ROOT).as_posix() for p in (ROOT / skill).glob("references/*/MODULE.md")
        )
        for module_md in modules:
            cost = now.module_cost(skill, module_md) or 0
            cost_before = base.module_cost(skill, module_md) if base.ref else None
            name = Path(module_md).parent.name
            budget = overrides.get(name, module_budget)
            rows.append([f"`{name}` module", str(cost), str(budget), *compare(cost, cost_before)])
            if cost > budget:
                errors.append((module_md, f"module `{name}` adds {cost} tokens; the budget is {budget}"))
        lines += table(["Loads", "Tokens", "Budget", *since], rows)

        files = now.markdown(skill)
        names = [f"{skill}/SKILL.md"] + [f for f in files if f != f"{skill}/SKILL.md"]
        if base.ref:
            names += [f for f in base.markdown(skill) if f not in files]
        rows, total, total_before = [], 0, 0
        for rel in names:
            tokens = now.tokens(rel)
            before = base.tokens(rel) if base.ref else None
            total += tokens or 0
            total_before += before or 0
            rows.append([f"`{Path(rel).relative_to(skill)}`", str(tokens or 0), *compare(tokens, before)])
        rows.append(["**Total**", f"**{total}**", *compare(total, total_before)])
        lines += table(["File", "Tokens", *since], rows)

    report = "\n".join(lines)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(report + "\n")
    for rel, message in errors:
        error("token budget", f"{message}. {BUDGET_NOTE}", rel, 1)
    return 1 if errors else 0
