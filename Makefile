GO_MODULES := ./internal/... ./services/api/... ./services/cli/...

.PHONY: build build-api build-cli build-studio generate generate-go generate-studio test test-go test-studio test-e2e vet lint \
	db-up run-api run-studio up down

build: build-api build-cli build-studio

build-api:
	go build -o bin/api ./services/api/cmd

build-cli:
	go build -o bin/cli ./services/cli/cmd

build-studio:
	cd studio && pnpm install --frozen-lockfile && pnpm build

# Regenerates sqlc queries, mocks, and the OpenAPI server/clients for Go and studio.
generate: generate-go generate-studio

generate-go:
	go generate $(GO_MODULES)

generate-studio:
	cd studio && pnpm gen:api

test: test-go test-studio

test-go:
	go test $(GO_MODULES)

test-studio:
	cd studio && pnpm test

# Starts (or reuses) postgres, the api, and studio, then runs Playwright.
test-e2e:
	cd test/studio && pnpm install --frozen-lockfile && pnpm test

vet:
	go vet $(GO_MODULES)

lint: vet
	cd studio && pnpm lint

db-up:
	docker compose up -d --wait postgres

# Runs the api on the host against the compose postgres, configured by services/api/.env.example.
run-api: db-up
	set -a && . ./services/api/.env.example && set +a && go run ./services/api/cmd

run-studio:
	cd studio && pnpm dev

up:
	docker compose up --build -d --wait

down:
	docker compose down
