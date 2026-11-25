# Snouty setup guide

## Install or update snouty

Don't install or update snouty yourself. If `snouty` is missing or older than 0.11.0, ask the user to install or update it, following `Install snouty` in the snouty README, <https://github.com/antithesishq/snouty#install-snouty>. Wait until they have, then run `snouty doctor` again.

## Configure snouty

If `ANTITHESIS_TENANT` and `ANTITHESIS_API_KEY` are set, such as from a platform's secrets, run `snouty login --tenant "$ANTITHESIS_TENANT"` to configure Snouty.

Otherwise, `snouty login` reads the credential only at an interactive terminal, so don't run `snouty login` yourself or through your harness, such as Claude Code's `!` prefix. Ask the user to run it in their own terminal on this machine, and walk them through it:

- It asks for the tenant, the `<tenant>` in `<tenant>.antithesis.com`.
- It offers a choice between an API key and **Single sign-on (OAuth)** (if sso is enabled). SSO waits for a browser redirect to `localhost`, so on a headless machine the user should either forward the port or use the API key option.

## Verify snouty

Run `snouty doctor`.

## Without a tenant or credentials

If `snouty doctor` reports no tenant or credentials, ask the user to configure snouty, or to confirm that you go on without a tenant. Ask before you start, with the up-front questions in `SKILL.md`: otherwise an unattended task can end with no Antithesis runs. Only `snouty launch`, `snouty runs` and `snouty debug` need a tenant, so without one you can still build and validate a workload through its local loop and import properties. Skip the steps that launch, triage or debug runs, and report them as needing a tenant.
