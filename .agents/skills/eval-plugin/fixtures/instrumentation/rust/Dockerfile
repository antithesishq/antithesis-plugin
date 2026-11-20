# Rust. FLAGS=1 passes the coverage rustflags; DEBUG=1 turns on release debug info.
# pricing has both, search lacks the flags, shipping lacks the debug info.
FROM rust:1-trixie AS build
ARG FLAGS=1
ARG DEBUG=1
WORKDIR /src
COPY . .
RUN set -e; set -- --config 'build.target = "x86_64-unknown-linux-gnu"'; \
    if [ "$DEBUG" = 1 ]; then set -- "$@" --config 'profile.release.debug = true'; fi; \
    if [ "$FLAGS" = 1 ]; then set -- "$@" --config 'target.x86_64-unknown-linux-gnu.rustflags = ["-Ccodegen-units=1","-Cpasses=sancov-module","-Cllvm-args=-sanitizer-coverage-level=3","-Cllvm-args=-sanitizer-coverage-trace-pc-guard","-Cllvm-args=-sanitizer-coverage-pc-table","-Clink-args=-Wl,--build-id"]'; fi; \
    cargo build --release "$@" \
 && mkdir -p /out /symbols && cp target/x86_64-unknown-linux-gnu/release/rust-service /out/ && cp /out/rust-service /symbols/

FROM debian:trixie-slim
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /symbols /symbols
