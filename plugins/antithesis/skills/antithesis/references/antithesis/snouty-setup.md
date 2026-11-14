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

Configure the tenant, registry and credentials with `snouty login`; it is interactive. In a headless environment, use environment variables or a settings file instead (see `snouty launch --help` and `snouty settings --help`).

## Verify snouty

Run `snouty doctor`.

## Without a tenant or credentials

If `snouty doctor` reports no tenant or credentials, ask the user to configure snouty or confirm they have none, and keep working. Only `snouty launch`, `snouty runs` and `snouty debug` need a tenant, so you can still build and validate a workload through its local loop, import properties and search `snouty docs`. Skip the steps that launch, triage or debug runs, and tell the user which, and that those need a tenant: <https://antithesis.com/pricing/>.
