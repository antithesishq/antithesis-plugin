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

## Without a tenant

If `snouty doctor` reports no tenant or credentials, ask the user to configure snouty, or to confirm they have no tenant yet. Without one, keep working: only `snouty launch`, `snouty runs` and `snouty debug` need a tenant. `snouty validate`, `snouty docs` and the local Docker Compose loop work without one, so you can still build a workload up to its local loop and import properties. Skip every step that launches, triages or debugs a run, and tell the user which you skipped, and that they need a tenant for them: <https://antithesis.com/company/contact/>.
