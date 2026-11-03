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

- **snouty**, installed and configured for the Antithesis tenant. If it's missing or not configured, follow `references/antithesis/snouty-setup.md`.
- **Docker or Podman, with Docker Compose.**
- **jq.**

Check them:

```bash
jq --version
snouty doctor
```

Continue only if `jq --version` succeeds and `snouty doctor` reports that all checks passed. Otherwise report what's missing, or the failing check, and stop.

## Modules

Pick the module from the first argument, then read only that module's `MODULE.md`.

| Argument     | Module                            | Use when                                                                    |
| ------------ | --------------------------------- | --------------------------------------------------------------------------- |
| `triage`     | `references/triage/MODULE.md`     | A run has started or finished and you need to know what failed.             |
| `debug`      | `references/debug/MODULE.md`      | A specific property failure needs investigating (multiverse debugging).     |
| `workload`   | `references/workload/MODULE.md`   | Building or iterating on a workload.                                        |
| `launch`     | `references/launch/MODULE.md`     | Launching a new run of a workload with `snouty launch`.                     |
| `properties` | `references/properties/MODULE.md` | Importing the SUT's guarantees (`import`) or defining a new one (`define`). |

If there is no argument, infer the module from the request. If it is still ambiguous, ask.
