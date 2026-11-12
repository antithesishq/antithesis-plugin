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

**Check instrumentation:** in each runtime image that runs the code, its jars are under `/opt/antithesis/catalog/`, at most one symlink deep. In a run, `Paths found for Antithesis instrumentation` lists that container and directory with the language Java.

## Local coverage

Use JaCoCo.

## Hegel driver

Not supported yet: hegel's Java frontend has no main entry point. Don't write the driver in Java; pick another language with `references/workload/languages.md`.
