# Build context is the repo root so the go workspace and shared ./internal resolve.
FROM golang:1.25-alpine AS build
WORKDIR /src

RUN go install github.com/go-delve/delve/cmd/dlv@latest

COPY go.work ./
COPY internal/go.mod internal/
COPY services/api/go.mod services/api/
COPY services/cli/go.mod services/cli/go.sum services/cli/
RUN go mod download

COPY internal internal
COPY services/api services/api
# Unoptimized with symbols so delve can attach to the live process.
RUN CGO_ENABLED=0 go build -gcflags="all=-N -l" -o /out/api ./services/api/cmd

FROM alpine:3.22
RUN apk add --no-cache wget
COPY --from=build /go/bin/dlv /usr/local/bin/dlv
COPY --from=build /out/api /usr/local/bin/api
EXPOSE 8080 2345
ENTRYPOINT ["/usr/local/bin/api"]
