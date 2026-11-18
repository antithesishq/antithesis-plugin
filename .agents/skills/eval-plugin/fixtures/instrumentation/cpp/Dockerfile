# C++. FLAGS=1 compiles with the coverage flags; index includes the header without them.
FROM debian:trixie AS build
ARG FLAGS=1
ARG SDK_TAG
RUN apt-get update -qq && apt-get install -y -qq clang binutils curl ca-certificates >/dev/null
WORKDIR /src
RUN test -n "$SDK_TAG" && for f in antithesis_instrumentation.h antithesis_sdk.h; do \
      curl -sfLo $f https://raw.githubusercontent.com/antithesishq/antithesis-sdk-cpp/$SDK_TAG/$f; done
COPY main.cpp .
RUN mkdir -p /out /symbols && if [ "$FLAGS" = 1 ]; then F='-fsanitize-coverage=trace-pc-guard,pc-table'; else F=''; fi \
 && clang++ -std=c++20 -O2 -g $F -Wl,--build-id main.cpp -o /out/cpp-service -lpthread \
 && cp /out/cpp-service /symbols/

FROM debian:trixie-slim
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /symbols /symbols
