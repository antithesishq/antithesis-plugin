# Report issues

Report one issue per root cause, even if several properties failed from it.

Use the destination and format the user specified. Without a format, use the one below; without a destination, print the report in the session. The format is written for GitHub; adapt its syntax for other destinations.

Write for a maintainer who knows this codebase but not Antithesis or this run. Lead with what's wrong and where. Explain one representative occurrence in the code's terms. Put supporting evidence in a collapsed `<details>` block. Don't describe how you investigated.

Each `{placeholder}` is a slot to fill in.

```markdown
# {title}

{failed_property_name}

{bug_description}

## Reproduction

{reproducer}

## Details

* Antithesis run: [`{run_id}`]({run_link})
* Input hash: `{input_hash}`
* vtime: `{vtime}`
* Version: {git_hash}

{duplicate_details}
```

`{run_link}` is `https://{tenant}.antithesis.com/run?run_id={run_id}`, with the tenant from `snouty settings show`.

## Reproducer

Put a reproducer in `{reproducer}`: code the maintainer can run to reproduce the bug without Antithesis. Prose instructions are not reproducers. Run it and confirm it reproduces the bug before including it. Don't commit it to the repository.

If a reproducer would be too hard to write, silently leave out the Reproduction section.

## Find the tracker

Known issues live in the project's issue tracker, which may not be the destination. Find it from:

- the git remote, such as `github.com/{owner}/{repo}`
- the links in `README` and `CONTRIBUTING`
- `<issueManagement>` in `pom.xml`, or `bugs` in `package.json`

Apache projects track issues in JIRA, at `issues.apache.org/jira`: search by project key, such as `ZOOKEEPER`, and the keys of the dependencies the failure involves, such as `CURATOR`.

## Duplicates

Search the tracker and the destination for existing issues before reporting. Check open and closed issues.

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
