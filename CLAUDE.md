# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# dalnamics

Monorepo for the dalnamics platform: Go services, the studio web app, and hardware (`harwood0/`).

Read `docs/arch.md` for the system architecture (services, how they talk, shared error codes and config) and the feature doc for the domain you're touching (e.g. `docs/auth.md`). Docs change in the same commit as the code they describe, following `docs/CONTRIBUTION.md`.

`harwood0/` is a separate Python (uv) and PlatformIO stack with its own `Makefile` and `harwood0/docs/`. None of the commands below, nor CI, cover it.

## Layout

| Path | What |
|---|---|
| `internal/` | Go code shared by every service (module `dalnamics/internal`) |
| `services/api/` | Front-facing HTTP API. Spec: `openapi.yaml` |
| `services/devicemgr/` | Internal device service; only the api calls it. Private spec: `openapi.yaml` |
| `services/cli/` | Cobra cli over the api; agents drive the platform through it |
| `studio/` | Vite + React app (shadcn, TanStack Router, zustand). Self-contained pnpm project |
| `test/studio/` | Playwright e2e across studio, api, and cli |
| `docs/` | Living design docs: `arch.md` (architecture) plus one doc per feature domain. Follow `docs/CONTRIBUTION.md` when editing |

Go modules are wired with `go.work`. Each service keeps app-specific code in `services/<svc>/internal/` and its `main` package in `services/<svc>/cmd/`.

## Commands

```sh
make generate     # after editing openapi.yaml, SQL queries, or mocked interfaces (generate-go + generate-studio)
make test         # Go + studio unit tests
make test-e2e     # Playwright; starts/reuses compose postgres, api, devicemgr, mosquitto, and the studio dev server
make lint         # go vet + oxlint
make up / down    # full stack in docker compose (api on :8080, devicemgr on :8081, mosquitto on :1883, postgres on :5433)
make run-api      # api on the host against compose postgres (env from services/api/.env.example)
make run-devicemgr # devicemgr on the host against compose postgres (env from services/devicemgr/.env.example)
make build        # bin/api, bin/cli, bin/devicemgr, studio/dist
```

Single tests:

```sh
go test ./services/api/internal/auth -run TestSignup             # one Go package / test
cd studio && pnpm vitest run src/routes/login.test.tsx -t "name"  # one studio test file / case
cd test/studio && pnpm exec playwright test tests/login.spec.ts --project=chromium  # one e2e spec (the setup project runs first)
```

CI (`.github/workflows/ci.yml`) runs on every PR and push to `main`. The services and studio jobs run in parallel and fail if code generation changes any committed file. The e2e job runs after both pass, and deploy (a placeholder) runs only on `main`.

## API changes are spec-first

1. Edit `services/api/openapi.yaml`. Operations needing auth declare `security: [{bearerAuth: []}]`; the server derives which operations require a bearer token from the spec, so there is no separate list to update.
2. `make generate` regenerates the Go server (`services/api/internal/apigen`), the Go client (`services/cli/internal/client/apigen`), and studio types (`studio/src/lib/api/schema.d.ts`). Generated code is committed and never hand-edited.
3. Implement the new method of `apigen.StrictServerInterface` in `services/api/internal/server`. Handlers translate between apigen types and domain services, and return domain sentinel errors rather than building error responses; `server/errors.go` maps them to status codes and stable `code` strings.

devicemgr's private spec (`services/devicemgr/openapi.yaml`) follows the same steps, generating `services/devicemgr/internal/apigen`. Its operations require the shared service token (`serviceToken`) by default; only `/healthz` opts out with `security: []`.

## Go conventions

- Flat packages: one package per concern area, with topics split into files (e.g. `auth/{service,tokens,password,pkce}.go`). Add a subpackage only for a real boundary.
- Configuration comes from the environment through a typed `config` package; no globals.
- Each service owns one Postgres schema (`public` for the api, `devicemgr` for devicemgr) and writes only to it; the api may read `devicemgr` tables. A schema a service creates gets a `COMMENT ON SCHEMA`.
- Data access: write SQL in `services/<svc>/internal/store/queries/*.sql`; sqlc generates a domain package under `store/` (e.g. `store/auth`). Compose each domain's `Querier`/`Queries` into the root `store.Querier`/`store.Store`. Application code depends on `store.Querier` only.
  - A domain that reads the other service's schema lists that service's migrations in its sqlc `schema` (e.g. the api's `devices` entry lists devicemgr's).
  - Transactions go through `store.Querier.InTx(ctx, func(store.Querier) error)`; in tests, stub it to run the callback against the same mock.
- Migrations live in `services/<svc>/internal/store/migrations` as `{version}_{name}.{up,down}.sql`, are embedded, and are applied when the service starts. devicemgr tracks its migrations in `public.devicemgr_schema_migrations`, separate from the api's `schema_migrations`.
  - Enable extensions inline in the first migration that needs them.
  - Prefer triggers for cross-cutting concerns (`set_updated_at()` exists).
  - Every table except `users` and pure join tables gets a `COMMENT ON TABLE`.
- Tests use testify (`require` for preconditions, `assert` for checks) and gomock.
  - Mocks are generated by mockgen through a `//go:generate go tool mockgen ...` line beside the interface, into a `mock<package>` package (e.g. `store/mockstore`).
  - Never hand-write mocks.
- Tools (oapi-codegen, sqlc, mockgen) are pinned as `tool` directives in each module's go.mod and run with `go tool`.

## Studio conventions

- `src/lib/api/client.ts` exports `publicApi` (no credentials) and `api` (bearer token + refresh-on-401 middleware from `stores/auth.ts`). Use `unwrap()` to turn failures into `ApiError`.
- Routes are files in `src/routes`. Pages that need a user go under `_authed/`, whose `beforeLoad` redirects to `/login?redirect=…`.
- Unit tests use Vitest + Testing Library + user-event.
  - Render real routes with `renderRoute(path)` from `src/test/render.tsx`.
  - Stub the api with `mockApi({'METHOD /path': handler})` from `src/test/api.ts`.

## E2E auth

The api seeds the users in `DEV_EMAILS` when `DEBUG=true`, and they sign in without a password (compose sets both). `test/studio/tests/auth.setup.ts` signs in `e2e@dalnamics.local` through studio's dev-login button and saves the browser state to `AUTH_FILE`.

- Tests that need a signed-in user: `test.use({ storageState: AUTH_FILE })`.
- Tests that end a session (logout): sign in their own session with `devLogin(page, email)` from `fixtures.ts`.
- New users: create them with `uniqueEmail()`.
- Devices: play the device's side over MQTT with `handshake()` and `connectBroker()` from `tests/device.ts`.

The api also seeds `DEV_REGISTRATION_CODE` (compose: `000000`) for `dev@dalnamics.local`, so a local harwood0 registers without studio. Each api start lets it be redeemed once, so e2e tests issue their own codes rather than use it.

## Issue workflow

Work is planned and built through GitHub issues with three project skills:

- `/intake <description>` and `/refine <issue#>` turn a request into a refined plan. They share one procedure (`.claude/workflow/refine.md`) and differ only in input: `/intake` creates a new issue, `/refine` rewrites an existing one. Each asks follow-up questions and checks for overlap with open issues. Overlapping work becomes a `Depends on` link and is never added to an existing issue. The issue body follows `.claude/workflow/issue-template.md` and gets the `refined` label.
- `/implement <issue#>` runs in plan mode and asks all its questions before approval, so it can then run unattended. It refuses unrefined issues, issues labelled `in-progress`, and issues whose dependencies aren't closed as completed. After approval it claims the issue (`in-progress`), works in its own worktree at `../dalnamics.worktrees/issue-<n>-<slug>` on branch `issue/<n>-<slug>`, and opens a draft PR. It is done only when CI passes, and it ends by printing the branch and a manual test plan.

GitHub I/O for these skills lives in `.claude/workflow/scripts/` (`context.sh`, `issue-publish.sh`, `issue-create.sh`, `deps.sh`, `claim.sh`, `release.sh`, `worktree.sh`). Change behavior there, not by duplicating logic in a skill.
