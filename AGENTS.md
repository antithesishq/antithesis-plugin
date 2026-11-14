# AGENTS.md

This repo packages the Antithesis skills as one plugin, `plugins/antithesis`, for each agent platform.

## Checks

[mise](https://mise.jdx.dev) installs the tools and runs the checks that CI runs. Run `mise run fix` to apply automatic fixes, then `mise run check` before you finish. `mise tasks` lists each `check:<tool>` and `fix:<tool>` task. `check:docs` uses the `snouty` on your PATH. In Claude Code, a Stop hook (`.claude/hooks/fix_and_check.py`) runs both at the end of every turn. mise only runs a `mise.toml` you trust: run `mise trust` once in each checkout, or add the repo to mise's `trusted_config_paths` setting to cover its worktrees too.

### Token budgets

`check:tokens` enforces two budgets. The top level, `SKILL.md` and the files it names outside any module, loads in every context that uses the skill, so its budget is tight. The whole skill, every file reachable from `SKILL.md`, is the worst case: an agent that reads every page. It also reports what each module adds, and, in CI, each file's change since the PR's base, so a reviewer can judge whether growth is earned. Neither budget catches wordiness inside a page; "Writing skill pages" does.

The budgets are soft. When a change goes over one, look for a shorter way to say the same thing: cut statements and words that aren't needed, and rely more on `snouty --help` and `snouty docs` than on restating them. Never trade the design for the budget. Don't change how pages reference each other, move content to another module, or leave out something important just to fit. If the right version is over budget, raise the budget in `mise.toml`, and say so in the change.

## Writing skill pages

An agent reads every word of a page it loads, and pays for it in context. Write so each sentence changes what the agent does.

- **Give the instruction, not a preamble.** Write `Run X`, not `Make sure to run X` or `It's important to run X`. Drop `note that`, `keep in mind`, `please`, and intensifiers such as `very` and `really`.
- **State each fact once,** on the page that owns it, and name that page elsewhere ("Cross-references").
- **Say why only when the agent needs it to decide,** such as when to break a rule, and in one clause.
- **Don't restate snouty.** Name the command, `snouty --help` or the `snouty docs` path, and say only what the docs don't: which flag to use here, and why.
- **Prefer one concrete example to a paragraph of description,** and cut an example the rule already makes clear.
- **Cut hedges and asides** that don't change the action: `generally`, `in most cases`, `as mentioned above`.
- **Read the page as an agent new to it.** Delete a sentence, and if the agent would still act the same, leave it out.

`check:prose` (`scripts/prose.py`) fails on common filler phrases in every skill page, outside code, and says what to write instead. Add a phrase there when review keeps catching it.

## Cross-references

A skill page names another file by its path from the skill root, in backticks, such as `references/workload/driver.md`. It names a part of a page by that part's heading, or by the bold label that opens a list item, in double quotes: "Starting up" in `references/workload/driver.md`, the "Wait until every node is up" step in `references/workload/driver.md`, "Write the title and body" in the `open-pr` skill, or just "Report" for a part of the same page. A table row counts as a part too, named by its first cell: the "Go build image" row in `references/workload/images.md`. A Dockerfile names a base image by its row in that table, as `<Go build image>`. Never refer to a step by its number, such as "step 2": reordering the list would silently change what it points at. Give the step a bold label and name that instead. Put any other quoted text that starts with a capital letter in backticks, so it isn't read as a reference. `check:references` fails on a reference that doesn't resolve, and on any step number.

## Scripts

Write repo tooling in Python, not shell. The scripts under `scripts/` and `.claude/hooks/` run on a uv-managed Python with the dependencies in `pyproject.toml`, locked in `uv.lock`. Each is executable with a `#!/usr/bin/env -S uv run --quiet --locked` shebang, so run it directly, such as `scripts/check.py typos`. Add a dependency with `uv add`, which updates both files. ruff and pyright check the Python.
