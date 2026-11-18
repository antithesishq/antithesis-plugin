# Java. FFI=1 puts com.antithesis:ffi on the classpath; audit leaves it off, so the
# instrumented bytecode crashes at startup with NoClassDefFoundError.
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY JavaService.java .
RUN javac JavaService.java && printf 'Main-Class: JavaService\n' > manifest.txt \
 && jar cfm java-service.jar manifest.txt JavaService*.class \
 && V=$(curl -s https://repo1.maven.org/maven2/com/antithesis/ffi/maven-metadata.xml | grep -o '<release>[^<]*' | cut -d'>' -f2) \
 && curl -sfLo ffi.jar https://repo1.maven.org/maven2/com/antithesis/ffi/$V/ffi-$V.jar

FROM eclipse-temurin:21-jre
ARG FFI=1
COPY --from=build /src/java-service.jar /app/java-service.jar
COPY --from=build /src/ffi.jar /opt/lib/ffi.jar
RUN mkdir -p /opt/antithesis && ln -s /app /opt/antithesis/catalog \
 && if [ "$FFI" = 1 ]; then CP=/app/java-service.jar:/opt/lib/ffi.jar; else CP=/app/java-service.jar; rm /opt/lib/ffi.jar; fi \
 && printf '#!/bin/sh\nexec java -cp %s JavaService\n' "$CP" > /usr/local/bin/java-service && chmod 755 /usr/local/bin/java-service
CMD ["/usr/local/bin/java-service"]
