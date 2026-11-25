# Replit setup

* Add secrets:
  * `ANTITHESIS_API_KEY`
  * `ANTITHESIS_TENANT`

  Either to a specific App ({App} -> Tools -> Secrets), or to your personal account (Profile -> Account secrets) and then linked to individual Apps.
* Add the plugin: Customization → Skills → Add → Add from GitHub, then enter `https://github.com/antithesishq/antithesis-plugin` and select the `antithesis` skill.
* Install the latest version of the official [snouty](https://github.com/antithesishq/snouty#install-snouty) in the App, with the shell installer script, even though `snouty` is already on the PATH. Replit preinstalls a `snouty` at `/repl/tools/bin/snouty` that ignores `ANTITHESIS_TENANT` and `ANTITHESIS_API_KEY` and talks to Replit's own Antithesis proxy instead. Put `$HOME/.local/bin` first on the PATH, and check that `command -v snouty` prints `$HOME/.local/bin/snouty`. The plugin doesn't install snouty.

Run requests from an App that has the secrets, not from a chat: Replit chats can't read secrets.
