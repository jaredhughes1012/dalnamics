GO_MODULES := ./internal/... ./services/api/... ./services/cli/...

.PHONY: build build-api build-cli build-studio test test-go test-studio vet run-api run-studio up down

build: build-api build-cli build-studio

build-api:
	go build -o bin/api ./services/api/cmd

build-cli:
	go build -o bin/cli ./services/cli/cmd

build-studio:
	cd studio && pnpm install --frozen-lockfile && pnpm build

test: test-go test-studio

test-go:
	go test $(GO_MODULES)

test-studio:
	cd studio && pnpm test

vet:
	go vet $(GO_MODULES)

run-api:
	go run ./services/api/cmd

run-studio:
	cd studio && pnpm dev

up:
	docker compose up --build -d

down:
	docker compose down
