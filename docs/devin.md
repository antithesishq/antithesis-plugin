# Before starting

* Ensure Devin is added to the repository (Settings → Environment).

# Customer setup

* Add organization secrets (Settings → Secrets)
  * ANTITHESIS_API_KEY
  * ANTITHESIS_TENANT
  * ANTITHESIS_REPOSITORY (GAR repository url)
  * ANTITHESIS_GAR_KEY
* Install the plugin: Customize → Plugins → Add plugin → From repository. Enter `antithesishq/antithesis-plugin` and the subdirectory `plugins/antithesis`.
  * Choose to either install it on the enterprise, organization, or personal scope
* Create an automation with a webhook trigger (Automations → New automation → Webhook), with this prompt. Save the webhook URL and secret; the secret is shown only once.

   ```text
   An Antithesis run has started. The webhook payload has this format:

   {
   "event": "run_start",
   "run_id": "<Antithesis run ID>",
   "title": "<run title>"
   }

   Triage the run with `/antithesis triage` from the Antithesis plugin. The code under test is @<owner>/<repo>. Report issues to that github repository.

   If the skill is not found, the plugin is still loading. Wait 10 seconds and try again.
   ```

   Devin installs plugins in the background when a session starts, so a skill call in the first few seconds can fail with "not found". The retry line covers that. It has to be in this prompt because the skill itself isn't loaded yet when the call fails.

   `@<owner>/<repo>` must be an `@` mention: it is what gives the session the repository.

* Launch Antithesis runs with the webhook as the run-start callback:

   ```bash
   snouty launch --launcher advanced_test ... \
     --param custom.callback.run_start.url=$DEVIN_WEBHOOK_URL \
     --param custom.callback.run_start.token=$DEVIN_WEBHOOK_SECRET
   ```

   Antithesis calls the webhook once the deployment has settled and faults are about to start. The token is stored with the run's launch parameters, so anyone who can see the run can see it.
