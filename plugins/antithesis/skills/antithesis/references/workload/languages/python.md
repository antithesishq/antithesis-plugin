# Python

## Antithesis SDK

- **Package:** `antithesis` on PyPI.
- **Latest version:** `curl -s https://pypi.org/pypi/antithesis/json | jq -r .info.version`.
- **Reference:** after `pip install antithesis==<version>`, `python -m pydoc antithesis.assertions`. Or the source at that version from `github.com/antithesishq/antithesis-sdk-python`.
- **Init:** none.
- **Setup complete:** `antithesis.lifecycle.setup_complete(details)`.
- **Assertions:** functions in `antithesis.assertions`, such as `always`, `sometimes`, `reachable` and `sometimes_greater_than`.
- **Cataloging:** the SDK reports an assertion only when it runs, so one that's never reached is missing rather than failing. In a run, Antithesis catalogs the code in `/opt/antithesis/catalog/` ("Instrumentation"). For the local loop, `python -m antithesis.catalog <src-dir> -o catalog.json` writes the catalog, and the SDK registers it at startup when `ANTITHESIS_ASSERTION_CATALOG` names that file.

## Instrumentation

Antithesis catalogs and instruments the Python code placed in `/opt/antithesis/catalog/` of an image: `snouty docs show /docs/reference/sdk/python/`. Link the code's directory there:

```dockerfile
RUN mkdir -p /opt/antithesis && ln -s /driver /opt/antithesis/catalog
```

## Local coverage

Use `coverage.py`.

## Hegel driver

- **Package:** `hegeltest` on PyPI, imported as `hegel`.
- **Latest version:** `curl -s https://pypi.org/pypi/hegeltest/json | jq -r '.info.version, .info.requires_python'`, which also prints the Python versions it supports.
- **Docs:** <https://hegel.readthedocs.io>. Read `Run tests on Antithesis`, the stateful testing tutorial and reference, and the how-to on threads.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/python/examples/sqlite_bank>, a concurrent bank workload run from `@hegel.main`.

| In `driver.md`              | In Python                                                           |
| --------------------------- | ------------------------------------------------------------------- |
| Main entry point            | `@hegel.main` on `def workload(tc)`, called under `__main__`        |
| Concurrent state machine    | a `hegel.StateMachine` subclass, run with `hegel.run_state_machine` |
| Rule, its groups and weight | `@hegel.rule(groups=["g"], weight=6)`                               |
| Always-run invariant        | `@hegel.invariant(always_run=True)`                                 |
| Unbounded step count        | `steps=2**63 - 1`, with `max_concurrency` above 1                   |
| Generate only               | `@hegel.main(phases=[hegel.Phase.generate])`                        |
| Weighted boolean draw       | `tc.draw(gs.weighted_booleans(p))`                                  |
| Hegel's repeat              | `tc.repeat`                                                         |

- Rules run on worker threads. Requests overlap while they wait on the network, but Python code itself runs one thread at a time, so keep the model's checks cheap.
- Hegel doesn't run `async` functions. Write rules as plain functions, with a blocking client.

Image: Python needs no build stage. Base the driver image on the "Python image" row in `references/workload/images.md`, install the latest `hegeltest` and `antithesis` with `pip`, and run the script as `CMD`.
