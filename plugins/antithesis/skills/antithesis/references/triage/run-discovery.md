# Run Discovery

## List the runs on the tenant

List with `-n 200`:

```sh
snouty runs list -n 200 [OPTIONS]
```

Snouty's default page size is too small: it can miss the run the user means. Raise it (e.g. `-n 500` or `-n 1000`) if 200 doesn't find the run. Status `incomplete` usually means the run failed to start, which can be triaged.

## Pick the run the user wants

Apply these rules, in order.

1. If the user gives a run ID, such as `2c6fa5b630e543a92c98fbed4b555280-53-1`, use it.
2. If the user asks for "the latest run" or "the run where we were trying the new retry logic", find it in the run list, using the run descriptions and the launchers and test names you have been using with this user (see the notes).
   For a run you launched, list your runs as "Finding your runs" in `references/launch/MODULE.md` describes.
3. If the user gives a run link, `https://<TENANT_ID>.antithesis.com/run?run_id=<run_id>`, take the run ID from it. Check that `TENANT_ID` matches snouty's tenant (`snouty settings show`); if not, snouty can't find the run.
4. Otherwise ask the user.

### Notes

- A tenant can be shared by several projects. If your memory says the user uses a non-default launcher or test name, consider only runs with that launcher or test name, unless the user asks for more.
- Don't filter by status or description text unless asked. Look at recent runs of any status first, and filter only if that doesn't find the run.
