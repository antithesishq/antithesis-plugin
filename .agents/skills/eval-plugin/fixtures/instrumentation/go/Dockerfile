# Go, instrumented correctly: the driver and the orders service, sharing one package.
FROM golang:1-trixie AS build
WORKDIR /src
RUN go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest
COPY . .
RUN go mod init shop && go get github.com/antithesishq/antithesis-sdk-go@latest && go mod tidy
RUN mkdir -p /symbols /out \
 && CGO_ENABLED=1 go build -toolexec=antithesis-go-toolexec -o /out/driver ./cmd/driver \
 && CGO_ENABLED=1 go build -toolexec=antithesis-go-toolexec -o /out/orders ./cmd/orders

FROM debian:trixie-slim
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /symbols /symbols
ARG TEST_TEMPLATE=
RUN if [ -n "$TEST_TEMPLATE" ]; then mkdir -p /opt/antithesis/test/v1/main \
 && printf '#!/bin/sh\ntouch /workload-active\n' > /opt/antithesis/test/v1/main/first_start_workload \
 && chmod 755 /opt/antithesis/test/v1/main/first_start_workload; fi
