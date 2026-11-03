# SDK references

`snouty docs` explains each Antithesis SDK, but not its compiled API reference. Read the exact API, such as every assertion macro and its arguments, from the machine-readable sources below.

Always read the latest release: look up its version first, and read the reference for that version. Use the same version in the project's dependency, unless the project already pins another; then read the pinned version's reference.

## Rust

- **Package:** `antithesis_sdk` on crates.io.
- **Latest version:** `curl -sA antithesis-skill https://crates.io/api/v1/crates/antithesis_sdk | jq -r .crate.max_stable_version`. crates.io rejects requests without a user agent.
- **Reference:** rustdoc JSON, zstd-compressed: `curl -sL https://docs.rs/crate/antithesis_sdk/<version>/json | zstd -d > antithesis_sdk.json`. Or the source: `curl -sLA antithesis-skill https://crates.io/api/v1/crates/antithesis_sdk/<version>/download | tar xz`.

## Go

- **Module:** `github.com/antithesishq/antithesis-sdk-go`.
- **Latest version:** `curl -s https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@latest | jq -r .Version`.
- **Reference:** in a module that requires it, `go doc -all github.com/antithesishq/antithesis-sdk-go/assert`. Or the source: `https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@v/<version>.zip`.

## C++

- **Source:** the header-only library at `github.com/antithesishq/antithesis-sdk-cpp`.
- **Latest version:** `gh api repos/antithesishq/antithesis-sdk-cpp/tags --jq '.[0].name'`.
- **Reference:** the header itself, `https://raw.githubusercontent.com/antithesishq/antithesis-sdk-cpp/<tag>/antithesis_sdk.h`.

## Java

- **Package:** `com.antithesis:sdk` on Maven Central.
- **Latest version:** `curl -s https://repo1.maven.org/maven2/com/antithesis/sdk/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2`.
- **Reference:** the sources jar, `https://repo1.maven.org/maven2/com/antithesis/sdk/<version>/sdk-<version>-sources.jar`, or the javadoc jar, `sdk-<version>-javadoc.jar` in the same directory.

## .NET

- **Package:** `Antithesis.SDK` on NuGet.
- **Latest version:** `curl -s https://api.nuget.org/v3-flatcontainer/antithesis.sdk/index.json | jq -r '.versions[-1]'`.
- **Reference:** the XML documentation in the package, `lib/<framework>/Antithesis.SDK.xml` inside `https://api.nuget.org/v3-flatcontainer/antithesis.sdk/<version>/antithesis.sdk.<version>.nupkg` (a zip).

## Python

- **Package:** `antithesis` on PyPI.
- **Latest version:** `curl -s https://pypi.org/pypi/antithesis/json | jq -r .info.version`.
- **Reference:** after `pip install antithesis==<version>`, `python -m pydoc antithesis.assertions`. Or the source at that version from `github.com/antithesishq/antithesis-sdk-python`.

## Any other language

Write assertions as JSON lines, following the schema in `snouty docs show /docs/reference/sdk/fallback/schema/`.
