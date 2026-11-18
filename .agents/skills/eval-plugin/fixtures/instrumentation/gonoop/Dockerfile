# Go, broken: a -default-no-op SDK with its tag on the command line instead of in GOFLAGS
# (antithesis-sdk-go#46). It writes symbol tables and its assertions work, but it reports
# no coverage.
FROM golang:1-trixie AS build
WORKDIR /src
RUN go install github.com/antithesishq/antithesis-sdk-go/tools/antithesis-go-toolexec@latest
COPY . .
RUN go mod init noopfixture && go get github.com/antithesishq/antithesis-sdk-go@v0.9.0-default-no-op && go mod tidy
RUN mkdir -p /symbols /out && CGO_ENABLED=1 go build -tags enable_antithesis_sdk -toolexec=antithesis-go-toolexec -o /out/gonoop .

FROM debian:trixie-slim
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /symbols /symbols
