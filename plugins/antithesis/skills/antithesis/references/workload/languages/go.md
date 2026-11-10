# Go

## Antithesis SDK

- **Module:** `github.com/antithesishq/antithesis-sdk-go`.
- **Latest version:** `curl -s https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@latest | jq -r .Version`.
- **Reference:** in a module that requires it, `go doc -all github.com/antithesishq/antithesis-sdk-go/assert`. Or the source: `https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@v/<version>.zip`.
- **Init:** none.
- **Setup complete:** `lifecycle.SetupComplete(details)`.
- **Assertions:** functions in the `assert` package, such as `assert.Always`, `assert.Sometimes`, `assert.Reachable` and `assert.SometimesGreaterThan`.
- **Cataloging:** build with the SDK's `antithesis-go-toolexec`, which catalogs the assertions, so one that's never reached still fails. Install the latest with `go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest`, and pass `-toolexec=antithesis-go-toolexec` to `go build`.

## Instrumentation

The same `antithesis-go-toolexec` adds coverage instrumentation, and writes the symbol tables to `/symbols`: `snouty docs show /docs/reference/sdk/go/instrumentation/`.

## Local coverage

- Build with `go build -cover -covermode=atomic -coverpkg=./...`, and set `GOCOVERDIR=/coverage/<service>`.
- Go writes counters only when `main` returns or the program calls `os.Exit`.
- Read it with `go tool cover`.

## Hegel driver

- **Module:** `hegel.dev/go/hegel`. The engine ships inside it.
- **Latest version:** `curl -s https://proxy.golang.org/hegel.dev/go/hegel/@latest | jq -r .Version`, or `go get hegel.dev/go/hegel@latest`, which takes it.
- **Docs:** <https://pkg.go.dev/hegel.dev/go/hegel>.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/go/examples/bank>, a concurrent bank workload run from `hegel.Workload`.

| In `driver.md`           | In Go                                                                         |
| ------------------------ | ----------------------------------------------------------------------------- |
| Main entry point         | `hegel.Workload(func(tc hegel.TestCase) { ... }, opts...)` in `func main`     |
| Concurrent state machine | `hegel.RunStateful(tc, m, hegel.WithConcurrency(), ...)`                      |
| Rule                     | a method named `Rule...` on the machine; an invariant is named `Invariant...` |
| Groups                   | `hegel.WithRuleGroup("g", "RuleA", "RuleB")`                                  |
| Always-run invariant     | `hegel.WithAlwaysCheckInvariants("InvariantA")`                               |
| Unbounded step count     | `hegel.WithStatefulStepCount(math.MaxInt)`                                    |
| Generate only            | `hegel.WithPhases(hegel.PhaseGenerate)`, as an option to `hegel.Workload`     |
| Weighted boolean draw    | `hegel.Draw(tc, hegel.WeightedBooleans(p))`                                   |

- **Rules have no weights.** To make an action rarer than the others, guard it with a weighted boolean draw.
- `hegel.Workload` runs test cases without limit, rather than one. With an unbounded step count the first never ends, so this makes no difference.

Build stage:

```dockerfile
FROM golang:1-bookworm AS build
WORKDIR /src
RUN go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest
COPY driver/ .
# Instruments the driver, catalogs its assertions, and writes /symbols.
RUN go build -toolexec=antithesis-go-toolexec -o /out/driver .
```
