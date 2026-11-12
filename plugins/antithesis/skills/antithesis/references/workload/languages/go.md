# Go

## Antithesis SDK

- **Module:** `github.com/antithesishq/antithesis-sdk-go`.
- **Latest version:** `curl -s https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@latest | jq -r .Version`.
- **Reference:** in a module that requires it, `go doc -all github.com/antithesishq/antithesis-sdk-go/assert`. Or the source: `https://proxy.golang.org/github.com/antithesishq/antithesis-sdk-go/@v/<version>.zip`.
- **Init:** none.
- **Setup complete:** `lifecycle.SetupComplete(details)`.
- **Assertions:** functions in the `assert` package, such as `assert.Always`, `assert.Sometimes`, `assert.Reachable` and `assert.SometimesGreaterThan`.
- **Cataloging:** build with the SDK's `antithesis-go-toolexec`, which catalogs the assertions, so one that's never reached still fails. Install the latest with `go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest`, and pass `-toolexec=antithesis-go-toolexec` to `go build`.
- **Cgo:** build with cgo enabled, `CGO_ENABLED=1`, and a C compiler in the build image. Without cgo, the SDK still reports assertions, but Antithesis gets no coverage from the binary.

## Instrumentation

Build with `antithesis-go-toolexec`, as "Cataloging" says. It also adds coverage instrumentation, and writes the symbol tables to `/symbols`, which a multi-stage build carries into the runtime image: `snouty docs show /docs/reference/sdk/go/instrumentation/`.

A build stage, on the "Go build image" row in `references/workload/images.md`, that leaves the binary in `/out` and its symbols in `/symbols`:

```dockerfile
FROM <Go build image> AS build
WORKDIR /src
RUN go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest
COPY driver/ .
RUN go build -toolexec=antithesis-go-toolexec -o /out/driver .
```

Pass build tags in `GOFLAGS`, such as `GOFLAGS=-tags=enable_antithesis_sdk`, never as `go build -tags`. A project that requires a `-default-no-op` version of the SDK, as nats-server does, needs that tag for its assertions and its coverage. The toolexec builds the SDK's coverage package in a nested `go list` that sees `GOFLAGS` but not the command line, so with `-tags` it silently links a no-op: the catalogs are written and the assertions fire, but nothing reports coverage ([antithesis-sdk-go#46](https://github.com/antithesishq/antithesis-sdk-go/issues/46)).

**Check instrumentation:** in the build stage, `go tool nm /out/<binary> | grep -c 'voidstarHandler).init_coverage'` prints a number above 0 for each binary. A 0 means the binary reports no coverage, as it does when built without the toolexec, with `CGO_ENABLED=0`, or with a no-op SDK. The symbol tables in `/symbols` prove nothing: the toolexec writes them in all of those cases. The check needs the binary's symbol table, so don't strip the Antithesis build, with `-ldflags=-s` or `strip`. In a run, each instrumented package shows in `Software was instrumented` under its import path, the name in the `# name` line of its table in `/symbols`.

## Local coverage

- Build with `ANTITHESIS_SKIP_COVERAGE=true go build -toolexec=antithesis-go-toolexec -cover -covermode=atomic -coverpkg=./...`, and set `GOCOVERDIR=/coverage/<service>`. The toolexec still catalogs the assertions, so the local loop lists one that's never reached.
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
