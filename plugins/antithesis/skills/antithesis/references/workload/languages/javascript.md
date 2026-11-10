# JavaScript and TypeScript

## Antithesis SDK

None released: `snouty docs show /docs/reference/sdk/javascript_sdk/` says to contact Antithesis about it. Until then, write assertions as JSON lines, following `references/workload/languages/fallback.md`.

## Instrumentation

Antithesis instruments JavaScript itself: `snouty docs show /docs/reference/sdk/javascript_sdk/`.

## Local coverage

Use `c8` for Node.

## Hegel driver

Not supported yet: hegel's TypeScript frontend has no concurrent state machines and no main entry point. Don't write the driver in JavaScript or TypeScript; pick another language with `references/workload/languages.md`.
