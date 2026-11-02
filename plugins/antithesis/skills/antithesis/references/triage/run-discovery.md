# Run Discovery

## How to obtain a list of runs on the tenant

```sh
snouty runs list -n 200 [OPTIONS]
```

Use `-n 200` as the default page size. Snouty's built-in default page size is too small for triage — it can miss the run when looking for the oldest non-triaged run (rule 4). Bump higher (e.g. `-n 500` or `-n 1000`) if a search at 200 still doesn't find what the user is asking for.

Run `snouty runs list --help` to learn about statuses and other options. The `--status` option is useful if you know the status. The status `incomplete` usually means the run failed to start for some reason and the failure can be triaged.

## How to tell what run_id the user wants to use

Apply these rules, in order.

1. The user may provide a run id directly -- if so, use that. Here is an example run_id:

   ```text
   2c6fa5b630e543a92c98fbed4b555280-53-1
   ```

2. The user may ask for "the latest run" or "the run where we were trying
   <xxx>". Consult `snouty runs` if this is not in your context. You can also
   consider the description of the runs returned in the run list to identify a
   run the user is asking for. Take into account the webhooks and sources you
   have been using with this user. See the notes below.

3. If the user provides a link to a run, take the run_id from it. A run link looks like:

   ```text
   https://<TENANT_ID>.antithesis.com/run?run_id=<run_id>
   ```

   Verify that the `TENANT_ID` matches snouty's tenant (shown by `snouty settings show`) before proceeding. If it does not match, `snouty` will not be able to find the run.

4. If the user did not provide a run link or run id, use the oldest non-triaged run, if you know whether runs were triaged or not. If you do not know which runs have been triaged, use the most recently completed run.

### Notes

- When trying to intuit a run_id from the runs list, take into account the webhook and the source the user is using. Filter on these fields. If the user is using a non-default webhook or source this should be in your memory. For example, if you know your user is using a webhook "my_special_webhook", consider only runs in the runs list that use that webhook. This is because sometimes tenants are shared by different projects within the same customer. Of course if the user asks you to go beyond just the one webhook or source, do that.

- Make sure NOT to filter by text or status unless explicitly asked. If you are trying to find the most recent run for a project, just look at recent runs with any status first. Only filter by text or status if you can't find what you are looking for.
