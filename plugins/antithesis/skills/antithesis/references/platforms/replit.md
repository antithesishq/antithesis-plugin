# Replit

- Antithesis credentials come from the App's Secrets. If `ANTITHESIS_TENANT` or `ANTITHESIS_API_KEY` is missing, tell the user to add it there, and meanwhile follow "Without a tenant or credentials" in `references/antithesis/snouty-setup.md`.
- Replit chats can't read secrets. If you are running in a chat rather than an App, tell the user to run the request from an App that has the secrets, then stop.
- Replit preinstalls a `snouty` at `/repl/tools/bin/snouty` that ignores `ANTITHESIS_TENANT` and `ANTITHESIS_API_KEY` and talks to Replit's own Antithesis proxy instead. Don't use it. Install the official snouty with the installer script in `references/antithesis/snouty-setup.md` even though `snouty` is already on the PATH, then run `export PATH="$HOME/.local/bin:$PATH"` and check that `command -v snouty` prints `$HOME/.local/bin/snouty`.
