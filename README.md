# antithesis-plugin

This plugin gives a coding agent an entry point to any task involving [Antithesis](https://www.antithesis.com/docs/).

Generally, you'll want to include a prompt of the form "Use Antithesis to test this PR, then triage and debug any failures you find."

## Install

- Claude Code:
  - `claude plugin marketplace add antithesishq/antithesis-plugin`
  - `claude plugin install antithesis@antithesis`
- Codex:
  - `codex plugin marketplace add antithesishq/antithesis-plugin`
  - `codex plugin add antithesis@antithesis`
- GitHub Copilot CLI:
  - `copilot plugin marketplace add antithesishq/antithesis-plugin`
  - `copilot plugin install antithesis@antithesis`
- Devin: [docs/devin.md](docs/devin.md)
- Replit: [docs/replit.md](docs/replit.md)
- Cursor: [docs/cursor.md](docs/cursor.md)

## Prerequisites

The Antithesis Plugin requires the following tools to be installed.

- [Snouty CLI](https://github.com/antithesishq/snouty)
- [Docker](https://github.com/docker) or [Podman](https://github.com/podman-container-tools/podman), with Docker Compose.
- [jq](https://github.com/jqlang/jq)

In addition, Snouty must be authenticated with your Antithesis tenant: `snouty login`. You can check that Snouty is setup correctly by running `snouty doctor`.

## Usage

The Antithesis plugin provides a skill called `/antithesis` (or `$antithesis` in some harnesses). The skill should be invoked automatically for Antithesis related prompts.

Given a free-form prompt, such as `/antithesis test the latest release of my system`, the skill plans a workflow: the chain of the tasks below that gets from what exists to what you asked for. Common shapes are setting up a new system, healing a workload after its system changed, and testing a system and triaging what breaks.

Or prompt the agent with one of the tasks directly:

- Write a new workload for system S
- Add functionality to existing workload W
- Define or import a property into workload W
- Launch workload W
- Triage test run R
- Root cause failure F

The skill is designed to be composable, so feel free to ask your agent to chain multiple things together:

> /antithesis write a workload for <https://github.com/etcd-io/etcd> which imports properties from <https://antithesis.com/docs/resources/kv_property_catalog.md>. You can consume up to 200 compute hours of testing. Use short smoke tests to verify the workload before switching to soak tests to verify etcd. Triage the results, root cause high confidence failures, and file issues for anything new you discover.

### Key differences from Antithesis docs

- Uses [Hegel](https://www.hegel.dev) as the generator that drives the system under test, not Antithesis' native test composer.
- Focuses on reaching coverage of all surfaces in the system under test first, rather than leading with system properties.

## Managing compute consumption

Antithesis bills by compute hours, so consider giving your agent a compute hour budget to spend, per run or overall. Keep your system's setup fast too: every run spends that time before fuzzing starts, so a faster setup makes every Antithesis run shorter. See [the Antithesis docs on usage](https://antithesis.com/docs/configuration/usage/) for details.

## Getting help

- Questions, discussion and feedback: the [Antithesis Discord](https://discord.com/invite/antithesis).
- A bug or request for this plugin: [file an issue here](https://github.com/antithesishq/antithesis-plugin/issues).
- A bug or request for Snouty: [file an issue on Snouty](https://github.com/antithesishq/snouty/issues).
- Anything about your Antithesis account, tenant or runs: email [support@antithesis.com](mailto:support@antithesis.com).

---

[Privacy policy](https://antithesis.com/legal/privacy_policy/) • [Support email](mailto:support@antithesis.com)
