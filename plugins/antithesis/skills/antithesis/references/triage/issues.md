# Report issues

Report one issue for each root cause among the failed properties. Do not report multiple issues for the same root cause, even if multiple properties failed.

By default, use the following format for reporting issues. If the user has specified a particular place or format of how to report issues, use that instead. If the user has not specified where to report issues, print the report in the session instead. The following format is written with GitHub in mind; adapt any GitHub-specific syntax for other destinations as appropriate.

Write for a maintainer who knows this codebase but not Antithesis or this run. Lead with what's wrong and where. Explain one representative occurrence in the code's terms. Put supporting evidence in a collapsed `<details>` block. Don't describe how you investigated.

```markdown
# <title>

<antithesis property name that failed>

<description of bug>

## Reproduction

<reproducer>

## Details

* Antithesis run: [`<run id>`](<run link>)
* Input hash: `<input hash>`
* vtime: `<vtime>`
* Version: <git hash>

<duplicate_details>
```

<run link> is `https://<tenant>.antithesis.com/run?run_id=<run id>`, with the tenant from `snouty settings show`.

## Reproducer

Write a reproducer for the bug and put it in <reproducer>. A reproducer is code that the maintainer can run to reproduce the bug that does not involve Antithesis. Prose explanations or instructions are not reproducers. Run the reproducer and ensure it reproduces the bug before including it in the report. Don't commit it to the repository.

If writing a reproducer would be too hard, don't write one, and instead silently leave out the Reproducer section entirely.

## Duplicates

Search the destination for existing issues before reporting.

If the bug already exists, edit the issue to add a bullet point to its <duplicate_details>.

<duplicate_details> has the following format:

```markdown
## Other Antithesis runs

<details><summary>Details</summary>
<p>

* [`run id`](run link)

</p>
</details>
```

and is only present if there are any duplicates, so you may have to create it. Do not include any content in each bullet other than the linked `run id`.
