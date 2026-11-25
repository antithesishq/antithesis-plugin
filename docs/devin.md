# Devin setup

* Add organization secrets (Settings → Secrets)
  * `ANTITHESIS_API_KEY`
  * `ANTITHESIS_TENANT`
* Install the plugin
  * Customize → Plugins → Add plugin → From repository. Enter `antithesishq/antithesis-plugin` and the subdirectory `plugins/antithesis`.
  * Remember to select the right installation scope ("Myself" vs installing on an org).
* Install the latest version of [snouty](https://github.com/antithesishq/snouty#install-snouty) in the environment Devin runs in. The plugin doesn't install it.

Devin's skill tool doesn't pass arguments to the skill. To run one module, name it in the request text, such as "Run `/antithesis triage` on run `<run_id>`".
