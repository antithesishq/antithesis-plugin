---
name: antithesis
description: Entry point to Antithesis. Use for any task that involves Antithesis.
argument-hint: "[triage [monitor|summary|root-cause]|debug|workload|launch|properties] [target]"
---

# Antithesis

## Before starting

1. If you are running on one of these platforms, read its notes:
   - Devin: `references/platforms/devin.md`
   - Replit: `references/platforms/replit.md`
2. Read `references/antithesis/explainer.md`.
3. Check the dependencies below.

### Dependencies

Every module needs:

- **snouty 0.9.0 or later**, installed and configured for the Antithesis tenant. If it's missing or not configured, follow `references/antithesis/snouty-setup.md`. If it's older, run `snouty update`, or reinstall it if it wasn't installed with the installer script
- **Docker or Podman, with Docker Compose**
- **jq**

Assume that dependencies are setup. If any command fails, check dependencies and `snouty doctor` first.

## Modules

Pick the module from the first argument, then read only that module's `MODULE.md`.

| Argument     | Module                            | Use when                                                      |
| ------------ | --------------------------------- | ------------------------------------------------------------- |
| `triage`     | `references/triage/MODULE.md`     | Analyze a run for failures, monitor an in progress run.       |
| `debug`      | `references/debug/MODULE.md`      | Execute commands in Antithesis to debug a moment or property. |
| `workload`   | `references/workload/MODULE.md`   | Building or iterating on a workload.                          |
| `launch`     | `references/launch/MODULE.md`     | Launching a new run of a workload with `snouty launch`.       |
| `properties` | `references/properties/MODULE.md` | Importing the SUT's guarantees or defining a new one.         |

If there is no argument, infer the module from the request. If it is still ambiguous, ask.
