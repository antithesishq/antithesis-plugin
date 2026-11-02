# Snouty setup guide

Install snouty and ensure that it is configured correctly.

## Install snouty

Snouty source repo is available here:

<https://github.com/antithesishq/snouty>

Snouty can be installed via a bash script installer:

<https://github.com/antithesishq/snouty/releases/latest/download/snouty-installer.sh>

Snouty can also be installed via cargo install or binstall (preferred):

```bash
cargo binstall snouty
```

## Update snouty

If snouty was installed using its official installer (`snouty-installer.sh`) it comes with a built in updater: `snouty update`.

Otherwise you can upgrade snouty via re-installing it.

## Configure snouty

Snouty must be authenticated with an Antithesis tenant to enable most functionality.

Configuration requires three pieces of information:

- Antithesis tenant id
- Docker registry url
- Antithesis authentication

Snouty includes an interactive configuration system `snouty login` which guides the user through setup and authentication.

For headless environments, snouty can be configured via environment variables or configuration files. See the snouty README for more details.

## Verify snouty

Run `snouty version` to check snouty's version number.

Run `snouty doctor` to ensure snouty is setup correctly.
