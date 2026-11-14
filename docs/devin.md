# Devin setup

* Add organization secrets (Settings → Secrets)
  * `ANTITHESIS_API_KEY`
  * `ANTITHESIS_TENANT`
  * `ANTITHESIS_REGISTRY` (Antithesis container registry URL)
  * `ANTITHESIS_GAR_KEY`
* Install the plugin
  * Customize → Plugins → Add plugin → From repository. Enter `antithesishq/antithesis-plugin` and the subdirectory `plugins/antithesis`.
  * Remember to select the right installation scope ("Myself" vs installing on an org).
