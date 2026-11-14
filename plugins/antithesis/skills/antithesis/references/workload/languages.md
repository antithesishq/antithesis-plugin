# Languages

Everything specific to one language is on that language's page: its Antithesis SDK, its instrumentation, its local coverage tool, and how to write a hegel driver in it. Read the page for each language you touch, the SUT's and the driver's:

- **Rust:** `references/workload/languages/rust.md`
- **Go:** `references/workload/languages/go.md`
- **C and C++:** `references/workload/languages/cpp.md`
- **Python:** `references/workload/languages/python.md`
- **OCaml:** `references/workload/languages/ocaml.md`
- **Java:** `references/workload/languages/java.md`
- **.NET:** `references/workload/languages/dotnet.md`
- **JavaScript and TypeScript:** `references/workload/languages/javascript.md`
- **Any other language:** `references/workload/languages/fallback.md`

## Always use the latest release

Use the latest release of the Antithesis SDK, of hegel and of every build tool a page names. Look each version up when you need it, with the command the page gives, and never copy one from memory or from an example. If the project already pins a version of the SDK, keep it, and read that version's reference.

`snouty docs` explains each Antithesis SDK, but not its compiled API. Read the exact API, such as every assertion and its arguments, from the reference the page names, at the version you use. Hegel is in beta, and its API changes between releases: trust its docs and its example workload over the spellings on the page when they differ.

## Pick the driver's language

Hegel has one engine, shared by a frontend for each language, so the driver in `references/workload/driver.md` behaves the same in all of them. Pick the first that applies and that "Hegel driver" in `references/workload/languages/<language>.md` supports:

1. The language the user asks for.
2. The language of the system's client library, so the driver calls the real client in-process.
3. Rust.

If the user asks for a language hegel can't write the driver in, tell them why, and use the next that applies. If Antithesis can't instrument the language you pick, as for OCaml or Python, tell the user that Antithesis won't see which branches the driver takes, so they can't guide its search.

## Instrument the software

Build every binary in the workload with Antithesis coverage instrumentation, the driver's as well as the SUT's, wherever its language allows. It's required: without it, Antithesis can't guide exploration by coverage or pause threads. An uninstrumented component is a black box: Antithesis can't see its branch points, so it can't include them in its search.

- Follow "Instrumentation" in `references/workload/languages/<language>.md`, for the code's language, including its instrumentation check. If the project builds with link-time optimization, use the docs page's link-time instructions. Compile-time instrumentation doesn't survive LTO.
- Instrument the binaries that run in the SUT's containers, and make sure the runtime image runs the instrumented build.
- The client library is code under test too. If the workload runs it in client containers (the stateful-clients pattern, `references/patterns/stateful-clients.md`), instrument the client program with it.
- Put symbol files in `/symbols` of the runtime image where the language needs them, or code in `/opt/antithesis/catalog/` for languages Antithesis catalogs or instruments itself.
- Add instrumentation tools and flags in the Antithesis Dockerfiles, not the project's own build. When you choose a base image for them, take it from `references/workload/images.md`.
- If a component can't be instrumented, instrument the rest.
- Instrument the driver too, the same way as any other code in its language. Its branches are where the workload decides what to do next, so they're part of the state space Antithesis searches.

Check it, for every component you instrumented, the SUT's first. A build can write symbol files and run assertions, and still report no coverage:

- **Locally:** the instrumentation check under "Instrumentation" in `references/workload/languages/<language>.md` passes for each binary or code directory that a runtime image gets. The runtime image also has the expected `/symbols` or catalog contents.
- **In the first run:** list the components you instrumented and the module each one registers, which "Instrumentation" in `references/workload/languages/<language>.md` names. Follow `references/triage/instrumentation.md` with that list, and confirm every one before a longer run. Passing properties aren't enough: `Software was instrumented` passes when any one module registers, such as the driver's. Fix the build of any component it reports as uninstrumented, and check it locally again.
