# Snouty setup guide

## Install snouty

Install with the installer script (preferred). It installs to `~/.local/bin` and enables `snouty update`:

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/antithesishq/snouty/releases/latest/download/snouty-installer.sh | sh
```

Alternatively you can install snouty via `npm` or `cargo`:

```bash
npm install -g snouty
npx snouty
cargo binstall snouty
cargo install snouty
```

Source: <https://github.com/antithesishq/snouty>.

## Configure snouty

`snouty login` saves the tenant, its container registry and a credential. It reads the credential only at an interactive terminal, so don't run it yourself or through your harness, such as Claude Code's `!` prefix. Ask the user to run `snouty login` in their own terminal on this machine, and walk them through it:

- It asks for the tenant, the `<tenant>` in `<tenant>.antithesis.com`.
- It offers **Single sign-on (OAuth)** if the tenant enables it, or else an API key, read without echo. Single sign-on waits for a browser redirect to `localhost`, so on a remote machine the user forwards that port or picks the API key.

Where no one can run a terminal, such as CI, set `ANTITHESIS_TENANT` and `ANTITHESIS_API_KEY`, then run `snouty login --tenant "$ANTITHESIS_TENANT"` to save the registry.

## Verify snouty

Run `snouty doctor`.

## Without a tenant or credentials

If `snouty doctor` reports no tenant or credentials, ask the user to configure snouty, or to confirm that you go on without a tenant. Ask before you start, with the up-front questions in `SKILL.md`: otherwise an unattended task can end with no Antithesis runs. Only `snouty launch`, `snouty runs` and `snouty debug` need a tenant, so without one you can still build and validate a workload through its local loop and import properties. Skip the steps that launch, triage or debug runs, and report them as needing a tenant.
