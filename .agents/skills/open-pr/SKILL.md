---
name: open-pr
description: Push the current branch of this repo and open a pull request for it. Use when the user asks to "open a PR", "put this up for review", or "turn this branch into a PR", or when another skill hands you a finished branch.
---

# Open a PR

Push the current branch and open a pull request for it. The branch already holds the finished commits. This skill only publishes them.

A release PR is different: the `release` skill opens its own.

## 1. Check the branch

1. The working tree is clean: `git status --porcelain` prints nothing. Commit or stash anything left over first.
2. The branch is not `main`.
3. Read what the PR will contain: `git fetch origin && git log --oneline origin/main..HEAD` and `git diff origin/main...HEAD --stat`.
4. The diff leaves the version alone: `scripts/set-version.py --check` passes, and `CHANGELOG.md` is unchanged. Only a release PR changes them.
5. `mise run check` passes. The Stop hook runs it with `CHECK_OFFLINE` set, which skips the link and schema checks, so run it yourself before the push.

## 2. Push the branch

```bash
git push -u origin <branch>
```

## 3. Write the title and body

Write the body to a file outside the checkout, such as `/tmp/pr-body-<branch>.md`, so the shell never mangles it and the repo's checks never lint or commit it.

Write prose that explains the change and why, as the difference between `main` and the branch. Leave out how the branch got there. Say what an agent that uses the plugin, or a contributor to this repo, does differently after the change. If nothing changes for them, say so. The `release` skill writes the release notes from the diff, not from this body, so explain the reasoning rather than list every edit.

Bullets are fine for listing specific changes. Section headers usually are not. Don't add a `## Summary` header, a `## Test plan` section, or any other template boilerplate. Don't list outstanding work, test checklists, or follow-up TODOs.

When the change raises a token budget in `mise.toml`, say so and why, as `AGENTS.md` asks.

When the work closes an issue, put `fixes #<N>` on its own line, one line per issue.

The title is one line in the voice of the subjects in `git log --oneline origin/main`, such as `Triage runs live instead of waiting for them to finish`. The repo squash-merges, so the title becomes the commit subject on `main`, and GitHub adds the `(#N)`.

## 4. Create the PR

```bash
gh pr create --title "<title>" --body-file /tmp/pr-body-<branch>.md --base main
```

A GitHub proxy can reject the GraphQL write with HTTP 403, which fails `gh pr create`. Create the PR over REST instead:

```bash
gh api -X POST repos/{owner}/{repo}/pulls \
  -f title="<title>" -f head=<branch> -f base=main \
  -F body=@/tmp/pr-body-<branch>.md --jq '.html_url'
```

Delete the body file once the PR exists, and give the user the PR's number and URL. Don't merge the PR yourself.

## 5. Watch it

A larger workflow, such as the `work-on-task` skill, watches the PR in its own step. When nothing else does, because the user asked only for a PR, watch it with the `watch-pr` skill.
