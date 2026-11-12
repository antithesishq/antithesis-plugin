# Rust

## Antithesis SDK

- **Package:** `antithesis_sdk` on crates.io.
- **Latest version:** `curl -sA antithesis-skill https://crates.io/api/v1/crates/antithesis_sdk | jq -r .crate.max_stable_version`. crates.io rejects requests without a user agent.
- **Reference:** rustdoc JSON, zstd-compressed: `curl -sL https://docs.rs/crate/antithesis_sdk/<version>/json | zstd -d > antithesis_sdk.json`. Or the source: `curl -sLA antithesis-skill https://crates.io/api/v1/crates/antithesis_sdk/<version>/download | tar xz`.
- **Init:** call `antithesis_sdk::antithesis_init()` at the start of `main`. It also emits the assertion catalog, so Rust needs no cataloging step.
- **Setup complete:** `antithesis_sdk::lifecycle::setup_complete(&details)`.
- **Assertions:** macros, such as `assert_always!`, `assert_sometimes!`, `assert_reachable!` and `assert_sometimes_greater_than!`.

## Instrumentation

Follow `snouty docs show /docs/reference/sdk/rust/instrumentation/`: add the latest `antithesis-instrumentation` crate, reference it once with `use antithesis_instrumentation as _;`, and pass the page's build flags as `--config` options of `cargo build` in the Antithesis Dockerfile, as the page's command-line option shows. Copy the flags from the page, not from memory. They set the build target, so the binary lands under `target/<target>/release/`. Keep an unstripped copy of each binary in `/symbols` of its runtime image.

A build stage, on the "Rust build image" row in `references/workload/images.md`, that leaves the binary in `/out` and its symbols in `/symbols`:

```dockerfile
FROM <Rust build image> AS build
WORKDIR /src
COPY driver/ .
RUN cargo build --release \
      --config 'build.target = "x86_64-unknown-linux-gnu"' \
      --config '<the page's target.x86_64-unknown-linux-gnu.rustflags>' \
 && mkdir -p /out /symbols \
 && cp target/x86_64-unknown-linux-gnu/release/driver /out/ \
 && cp /out/driver /symbols/
```

**Check instrumentation:** as the page's validation section says, in the build stage, for the unstripped copy in `/symbols` of each binary the runtime image gets: `nm <binary> | grep antithesis_load_libvoidstar` shows a `T` symbol, and `readelf -S <binary> | grep sancov` lists the `__sancov_guards` and `__sancov_pcs` sections.

## Local coverage

- In the build stage, run `rustup component add llvm-tools-preview` and build with the same command and `RUSTFLAGS="-Cinstrument-coverage -Cllvm-args=-runtime-counter-relocation"` set. `RUSTFLAGS` replaces the Antithesis rustflags, and the build target, so the binary's path, stays the same.
- Set `LLVM_PROFILE_FILE=/coverage/<service>/%c%m.profraw`. `%c` writes counters as they change, so the data survives a killed process. `%m` merges restarts into one file. Don't use `%p`: every container's process is PID 1, so a restart overwrites the data.
- Read it with `llvm-cov`.

## Hegel driver

- **Package:** the `hegeltest` crate, imported as `hegel`, with `features = ["static-engine"]`, which links the engine into the binary.
- **Latest version:** `curl -sA antithesis-skill https://crates.io/api/v1/crates/hegeltest | jq -r .crate.max_stable_version`, or `cargo add hegeltest --features static-engine`, which takes it.
- **Docs:** <https://docs.rs/hegeltest/latest/hegel/>.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/rust/examples/sqlite>, a concurrent bank workload run from `#[hegel::main]`.

| In `driver.md`              | In Rust                                                  |
| --------------------------- | -------------------------------------------------------- |
| Main entry point            | `#[hegel::main]` on `fn main(tc: hegel::TestCase)`       |
| Concurrent state machine    | `#[hegel::concurrent_state_machine]` on the `impl` block |
| Rule, its groups and weight | `#[rule(groups = ["g"], weight = 6)]`                    |
| Always-run invariant        | `#[invariant(always_run)]`                               |
| Unbounded step count        | `.steps(i64::MAX)`                                       |
| Generate only               | `#[hegel::main(phases = [hegel::Phase::Generate])]`      |
| Weighted boolean draw       | `tc.draw(gs::weighted_booleans(p))`                      |
| Hegel's repeat              | `tc.repeat`                                              |
