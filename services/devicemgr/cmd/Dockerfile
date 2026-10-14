# Build context is the repo root so the go workspace and shared ./internal resolve.
FROM golang:1.27-alpine AS build
WORKDIR /src

RUN go install github.com/go-delve/delve/cmd/dlv@latest

COPY go.work go.work.sum ./
COPY internal/go.mod internal/
COPY services/api/go.mod services/api/go.sum services/api/
COPY services/cli/go.mod services/cli/go.sum services/cli/
COPY services/devicemgr/go.mod services/devicemgr/go.sum services/devicemgr/
RUN go mod download

COPY internal internal
COPY services/devicemgr services/devicemgr
# Unoptimized with symbols so delve can attach to the live process.
RUN CGO_ENABLED=0 go build -gcflags="all=-N -l" -o /out/devicemgr ./services/devicemgr/cmd

FROM alpine:3.22
RUN apk add --no-cache wget
COPY --from=build /go/bin/dlv /usr/local/bin/dlv
COPY --from=build /out/devicemgr /usr/local/bin/devicemgr
EXPOSE 8081 2346
ENTRYPOINT ["/usr/local/bin/devicemgr"]
