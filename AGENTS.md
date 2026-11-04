# AGENTS.md

This repo packages the Antithesis skills as one plugin, `plugins/antithesis`, for each agent platform.

## Checks

[mise](https://mise.jdx.dev) installs the tools and runs the checks that CI runs. Run `mise run fix` to apply automatic fixes, then `mise run check` before you finish. `mise tasks` lists each `check:<tool>` and `fix:<tool>` task. `check:docs` uses the `snouty` on your PATH. In Claude Code, a Stop hook (`.claude/hooks/fix_and_check.py`) runs both at the end of every turn. mise only runs a `mise.toml` you trust: run `mise trust` once in each checkout, or add the repo to mise's `trusted_config_paths` setting to cover its worktrees too.

### Token budgets

The token budgets that `check:tokens` enforces are soft. When a change goes over one, look for a shorter way to say the same thing: cut statements and words that aren't needed, and rely more on `snouty --help` and `snouty docs` than on restating them. Never trade the design for the budget. Don't change how pages reference each other, move content to another module, or leave out something important just to fit. If the right version is over budget, raise that module's budget in `mise.toml` (`MODULE_TOKEN_BUDGETS`), and say so in the change.

## Scripts

Write repo tooling in Python, not shell. The scripts under `scripts/` and `.claude/hooks/` run on a uv-managed Python with the dependencies in `pyproject.toml`, locked in `uv.lock`. Each is executable with a `#!/usr/bin/env -S uv run --quiet --locked` shebang, so run it directly, such as `scripts/check.py typos`. Add a dependency with `uv add`, which updates both files. ruff and pyright check the Python.
