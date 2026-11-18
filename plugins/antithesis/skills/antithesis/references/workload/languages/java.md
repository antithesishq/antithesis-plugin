# Java

## Antithesis SDK

- **Package:** `com.antithesis:sdk` on Maven Central.
- **Latest version:** `curl -s https://repo1.maven.org/maven2/com/antithesis/sdk/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2`.
- **Reference:** the sources jar, `https://repo1.maven.org/maven2/com/antithesis/sdk/<version>/sdk-<version>-sources.jar`, or the javadoc jar, `sdk-<version>-javadoc.jar` in the same directory.
- **Init:** none.
- **Setup complete:** `Lifecycle.setupComplete(details)`, in `com.antithesis.sdk`.
- **Assertions:** static methods of `com.antithesis.sdk.Assert`, such as `always`, `sometimes`, `reachable` and `sometimesGreaterThan`. Details are a Jackson `ObjectNode`, from `JsonNodeFactory.instance.objectNode()`.
- **Locally:** with no catalog, the SDK writes an assertion only once it's hit, so an assertion never reached is missing from `sdk.jsonl`, not listed as unmet. Compare the messages in `sdk.jsonl` with the `Assert` calls in the source.
- **Cataloging:** follow `snouty docs show /docs/reference/sdk/java/how_to_build_with_sdk/`.

## Instrumentation

`snouty docs show /docs/reference/sdk/java/how_to_build_with_sdk/`.

Antithesis's instrumented bytecode calls the SDK's `com.antithesis:ffi` package, so every instrumented program needs it on its classpath at run time, as a dependency of `com.antithesis:sdk` or on its own. Without it the program exits at startup with `NoClassDefFoundError: com/antithesis/ffi/internal/FfiHandler`.

**Check instrumentation:** in each runtime image that runs the code, its jars are under `/opt/antithesis/catalog/`, at most one symlink deep, and the program starts with `com.antithesis:ffi` on its classpath. In a run, each jar is a module named after the jar file, without `.jar`. Antithesis assigns its module ID, so look for it by name and container.

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

Image: build on the "Runtime image" row in `references/workload/images.md` with `openjdk-25-jdk-headless` and `maven` from apt. Copy the jar and its dependencies into one directory, such as `/opt/driver/`, with `maven-dependency-plugin`'s `copy-dependencies` goal; the example's `build-classpath` names paths that don't survive a multi-stage copy. Run on the runtime image with `openjdk-25-jre-headless`, catalog the directory with `mkdir -p /opt/antithesis && ln -s /opt/driver /opt/antithesis/catalog`, and start it with `CMD ["java", "--enable-native-access=ALL-UNNAMED", "-cp", "/opt/driver/*", "<main class>"]`, never `java -jar`: Antithesis adds its own jars beside the cataloged ones. For `hegel-jna`, use `openjdk-21-*`, and set `maven.compiler.release` to 21.
