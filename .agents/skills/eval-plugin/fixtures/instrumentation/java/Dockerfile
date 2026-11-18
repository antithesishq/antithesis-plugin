# Java. FFI=1 puts com.antithesis:ffi on the classpath; javanoffi leaves it off, so the
# instrumented bytecode crashes at startup with NoClassDefFoundError.
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY JavaFixture.java .
RUN javac JavaFixture.java && printf 'Main-Class: JavaFixture\n' > manifest.txt \
 && jar cfm javafixture.jar manifest.txt JavaFixture*.class \
 && V=$(curl -s https://repo1.maven.org/maven2/com/antithesis/ffi/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2) \
 && curl -sfLo ffi.jar https://repo1.maven.org/maven2/com/antithesis/ffi/$V/ffi-$V.jar

FROM eclipse-temurin:21-jre
ARG FFI=1
COPY --from=build /src/javafixture.jar /app/javafixture.jar
COPY --from=build /src/ffi.jar /opt/lib/ffi.jar
RUN mkdir -p /opt/antithesis && ln -s /app /opt/antithesis/catalog \
 && if [ "$FFI" = 1 ]; then CP=/app/javafixture.jar:/opt/lib/ffi.jar; else CP=/app/javafixture.jar; rm /opt/lib/ffi.jar; fi \
 && printf '#!/bin/sh\nexec java -cp %s JavaFixture\n' "$CP" > /usr/local/bin/javafixture && chmod 755 /usr/local/bin/javafixture
CMD ["/usr/local/bin/javafixture"]
