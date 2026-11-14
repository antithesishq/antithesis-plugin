# Bug report template

Report one issue per root cause, even if several properties failed from it.

Without a destination, print the report in the session. The format is written for GitHub; adapt its syntax for other destinations.

Write for a maintainer who knows this codebase but not Antithesis or this run. Lead with what's wrong and where. Explain one representative occurrence in the code's terms. Put supporting evidence in a collapsed `<details>` block. Don't describe how you investigated.

Each `{placeholder}` is a slot to fill in.

```markdown
# {title}

{failed_property_name}

{bug_description}

## Reproduction

{reproducer}

## Status

* Confirmed: {confirmed}
* Inferred: {inferred}
* Open: {open}

## Details

* Antithesis run: [`{run_id}`]({run_link})
* Input hash: `{input_hash}`
* vtime: `{vtime}`
* Version: {git_hash}
* Reproduces on: {versions}

{duplicate_details}
```

`{run_link}` is `https://{tenant}.antithesis.com/run?run_id={run_id}`, with the tenant from `snouty settings show`.

`{reproducer}` is the program from "Reproduce it outside Antithesis" in `references/bug-report/MODULE.md`, with the command to run it, or why there is none. Each status line lists the claims with that label, and is left out when empty. `{versions}` lists the versions the reproducer ran against and whether each reproduced.

## Duplicates

Search the destination for existing issues before reporting.

If the bug already exists, edit the issue to add a bullet point to its `{duplicate_details}`.

`{duplicate_details}` has the following format:

```markdown
## Other Antithesis runs

<details><summary>Details</summary>
<p>

* [`{run_id}`]({run_link})

</p>
</details>
```

and is present only if there are duplicates, so you may have to create it. Each bullet holds only the linked `{run_id}`.
