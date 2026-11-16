# Java

## Antithesis SDK

- **Package:** `com.antithesis:sdk` on Maven Central.
- **Latest version:** `curl -s https://repo1.maven.org/maven2/com/antithesis/sdk/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2`.
- **Reference:** the sources jar, `https://repo1.maven.org/maven2/com/antithesis/sdk/<version>/sdk-<version>-sources.jar`, or the javadoc jar, `sdk-<version>-javadoc.jar` in the same directory.
- **Init:** none.
- **Setup complete:** `Lifecycle.setupComplete(details)`, in `com.antithesis.sdk`.
- **Assertions:** static methods of `com.antithesis.sdk.Assert`, such as `always`, `sometimes`, `reachable` and `sometimesGreaterThan`.
- **Cataloging:** follow `snouty docs show /docs/reference/sdk/java/how_to_build_with_sdk/`.

## Instrumentation

`snouty docs show /docs/reference/sdk/java/how_to_build_with_sdk/`.

## Local coverage

Use JaCoCo.

## Hegel driver

- **Package:** `dev.hegel:hegel` on Maven Central, which needs Java 22 or later and ships with its engine. `dev.hegel:hegel-jna` has the same API for Java 17 to 21.
- **Latest version:** `curl -s https://repo1.maven.org/maven2/dev/hegel/hegel/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2`.
- **Docs:** <https://javadoc.io/doc/dev.hegel/hegel>. Read `Hegel.main` and `Stateful`.
- **Example workload:** <https://github.com/hegeldev/hegel/tree/main/frontends/java/examples/sqlite_bank>, a concurrent bank workload run from `Hegel.main`, with its `pom.xml`.

| In `driver.md`              | In Java                                                                  |
| --------------------------- | ------------------------------------------------------------------------ |
| Main entry point            | `Hegel.main(args, tc -> { ... }, settings)` in `public static void main` |
| Concurrent state machine    | `Stateful.run(machine, tc, Stateful.options().maxConcurrency(n))`        |
| Rule, its groups and weight | `@Rule(groups = {"g"}, weight = 6)`                                      |
| Always-run invariant        | `@Invariant(alwaysRun = true)`                                           |
| Unbounded step count        | `.stepCount(Integer.MAX_VALUE)` on the options                           |
| Generate only               | `new Settings().phases(Phase.GENERATE)`, as the settings of `Hegel.main` |
| Weighted boolean draw       | `tc.draw(Generators.booleans(p))`                                        |

Run the driver with `java --enable-native-access=ALL-UNNAMED`. Image: build on the "Runtime image" row in `references/workload/images.md` with `openjdk-25-jdk-headless` and `maven` from apt, copy the dependencies next to the jar with `maven-dependency-plugin`, and run on the runtime image with `openjdk-25-jre-headless`.
