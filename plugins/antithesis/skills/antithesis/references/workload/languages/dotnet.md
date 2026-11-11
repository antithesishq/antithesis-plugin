# .NET

## Antithesis SDK

- **Package:** `Antithesis.SDK` on NuGet.
- **Latest version:** `curl -s https://api.nuget.org/v3-flatcontainer/antithesis.sdk/index.json | jq -r '.versions[-1]'`.
- **Reference:** the XML documentation in the package, `lib/<framework>/Antithesis.SDK.xml` inside `https://api.nuget.org/v3-flatcontainer/antithesis.sdk/<version>/antithesis.sdk.<version>.nupkg` (a zip).
- **Init:** none.
- **Setup complete:** `Lifecycle.SetupComplete(details)`, in the `Antithesis.SDK` namespace.
- **Assertions:** static methods of `Antithesis.SDK.Assert`, such as `Always`, `Sometimes`, `Reachable` and `SometimesGreaterThan`.
- **Cataloging:** follow `snouty docs show /docs/reference/sdk/dotnet/`.

## Instrumentation

`snouty docs show /docs/reference/sdk/dotnet/instrumentation/`.

## Local coverage

Use the standard coverage tool for .NET.

## Hegel driver

Not supported yet: hegel has no .NET frontend. Don't write the driver in .NET; pick another language with `references/workload/languages.md`.
