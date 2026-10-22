---
name: review-issues
description: Pre-release review of every issue merged since the last release tag. Reviews their code together for bugs, functional gaps, and missing test coverage, fixes every finding on one fix/release-<version> branch with a draft PR, and tags the release once that PR merges. Run from main in plan mode, so every question is asked before work starts.
disable-model-invocation: true
---

Review the issues merged since the last release, fix what the review finds, and prepare the next release tag.

A release is a `vX.Y.Z` tag on `main`; the first is `v0.1.0`. The review covers every merged PR that closed an issue since the last tag. Commits that didn't come from an issue PR (CAD, harwood0, utility and script work) are out of scope, as is anything under `harwood0/`. Scripts live in `.claude/workflow/scripts/` and are run from the main checkout's root.

This is the gate before a release. Ask every question during planning (phase 1), so that after the plan is approved the work runs to the end without the developer.

## Phase 1: Review (read-only)

1. **Check the checkout:** run from the main checkout on `main` (`git branch --show-current`, and `git rev-parse --show-toplevel` is not under `worktrees/`). If not, stop and say so.
2. **Load the scope:** run `review-range.sh`. It prints the last release, the candidate next versions, the reviewed commit (`origin/main`), and every issue PR in range with the issues it closed and the files it changed outside `harwood0/`. Note the reviewed commit's full sha (`git rev-parse origin/main`); everything below reviews that commit, not the local checkout.
   - **Pending review:** if it lists one, stop. For an open PR, report it and tell the developer to finish and merge it. For a merged one, its tag is missing: ask whether to tag it now with `tag-release.sh --pr <n>`, run it if confirmed, and stop.
   - **No issue PRs in range:** say there is nothing to release and stop.
3. **Load the issues:** for each PR, read the issues it closed (`gh issue view <n> --comments`) and the PR (`gh pr view <pr> --comments`). Each issue's plan gives the intended behavior, its **Decisions**, and its **Acceptance criteria**; the review checks the code against them.
4. **Read the docs:** CLAUDE.md, `docs/arch.md`, `docs/CONTRIBUTION.md`, and every feature doc the PRs touched.
5. **Review each issue:** launch one general-purpose agent per PR, in parallel in a single message. With more than six PRs, group related PRs so no more than six run. Give each agent its issue numbers, PR numbers, merge commits, and file lists, and tell it to:
   - Stay read-only: no edits, commits, or `gh` writes.
   - Read the issue plans, then the PR's change (`git diff <merge>^1 <merge> -- . ':!harwood0'`), then the same files and the code around them as they are now at `origin/main`, since later PRs may have changed them. Read generated code (`apigen/`, `schema.d.ts`, `routeTree.gen.ts`, `mockstore/`, sqlc output under `store/<domain>/`) and lockfiles only to check them against their sources.
   - Look for:
     - **Correctness:** bugs, unhandled errors, races, wrong status codes or error `code`s, migrations that don't reverse cleanly.
     - **Security:** authorization gaps, missing `security` on operations, secrets in logs, unvalidated input, token or code handling.
     - **Functional:** acceptance criteria that aren't actually met, behavior that contradicts the issue's Decisions or the docs, and rough edges a user would hit in studio or the cli (missing loading or error states, confusing messages, flows that dead-end).
     - **Conventions:** departures from CLAUDE.md and `docs/CONTRIBUTION.md`, and docs that no longer match the code.
     - **Test coverage:** behaviors and error paths without a unit test, and acceptance criteria without an e2e test.
   - Return each finding as: title; severity (`high`: a bug, security hole, data loss, or unmet acceptance criterion; `medium`: a functional gap, missing error handling, or untested critical path; `low`: cleanup, consistency, or minor coverage); category; issue number; `file:line`; what is wrong, with the concrete input or state that triggers it; and the proposed fix with the tests that would prove it.
6. **Review across issues** yourself, while the agents run. Read the code where the issues meet:
   - Flows that span features, such as a signed-in user registering a device, and whether any e2e test covers the whole path.
   - Patterns two issues implemented differently, such as error handling, config loading, or store access, and code duplicated across services that belongs in `internal/`.
   - Shared data that drifted: error codes, config variables, and topics in `docs/arch.md` against the code.
7. **Measure coverage:** run `go test -cover ./internal/... ./services/api/... ./services/cli/... ./services/devicemgr/...` and use the packages the reviewed PRs touched to back the coverage findings.
8. **Verify every finding** against the code at `origin/main`. Drop anything you can't confirm, merge duplicates, and rank the rest by severity. Number them `F1`, `F2`, ….
9. **Ask:** use AskUserQuestion, recommendation first, in rounds of up to four questions:
   - **The version:** offer the candidates from step 2. Recommend `v0.1.0` for the first release; otherwise recommend minor when the issues added features, and patch when they only fixed things.
   - **Findings that need a decision:** where the right fix is a product choice, or several fixes are reasonable.
   - **Findings too big for this branch:** a new feature, a large redesign, or a change to a settled issue Decision. Recommend deferring them to a new issue. Every other finding is fixed in this branch.
10. **Write the plan** for approval:
    - The version, and branch `fix/release-<version>`.
    - The issues and PRs reviewed, and the reviewed commit.
    - Every finding: number, severity, issue, `file:line`, the problem, and the fix at file level, with the unit and e2e tests that prove it.
    - The docs sections to change.
    - Deferred findings, each with a one-paragraph request ready for `/intake`.
    - The validation commands.

    With no findings to fix, the plan is to tag the reviewed commit with `tag-release.sh <version> <reviewed-sha>`. Then exit plan mode.

## Phase 2: Fix (after approval)

With no findings to fix, run `tag-release.sh <version> <reviewed-sha>`, report the tag, and stop. Otherwise:

1. **Create the worktree:** run `worktree.sh fix release-<version>` and note the printed path and branch. From here on:
   - Every file read and edit uses absolute paths inside the worktree.
   - Every command runs with the worktree as its working directory.
   - Never edit the main checkout.

   The worktree starts from the latest `origin/main`. If it is past the reviewed commit, run `review-range.sh --list <reviewed-sha> origin/main`. If that lists any issue PR, stop and report it: that work wasn't reviewed, and the review must be run again.
2. **Fix** the findings in order of severity, following CLAUDE.md: spec first, then `make generate`; SQL and migrations before the code that uses them; handlers return domain sentinel errors. Commit after each finding, or a group of closely related ones, with a message that names the finding numbers and the issues they came from.
3. **Write the tests:** every fixed bug gets a test that fails without the fix. Close every coverage finding with the unit tests (Go: testify and gomock; studio: Vitest via `renderRoute` and `mockApi`) and Playwright e2e tests in `test/studio` it called for.
4. **Update the docs** the plan listed, following `docs/CONTRIBUTION.md`.
5. **Validate locally** with the same checks CI runs: `make generate` (confirm it leaves no diff), then `make lint`, `make test`, `make test-e2e`, and `make build`. Playwright reuses a stack that is already running, so run `./run_local.sh` in the worktree before `make test-e2e` (it stops any colliding stack and starts the worktree's), and `./cleanup_local.sh` once e2e passes. Fix failures and rerun until all pass. If something can't pass, don't hide it; report it in step 8 and in the PR.
6. **Self-review:** read the full diff against `origin/main`. Check that every finding in the plan is fixed and tested, look for leftover debug code, and confirm generated files were regenerated rather than hand-edited.
7. **Ship:**
   - Push with `git push -u origin <branch>`.
   - Open a draft PR: `gh pr create --draft --base main --title "Release review <version>" --body-file <file>`. The body starts with the marker `<!-- release-review <version> reviewed=<reviewed-sha> -->` (the full sha), which `tag-release.sh` reads. Then it lists the issues and PRs reviewed, a table of findings with how each was fixed, the deferred findings, the validation results, and the test plan. The issues are already closed, so it has no `Closes` lines.
8. **Pass CI:** run `gh pr checks <pr> --watch --fail-fast`. On a failure:
   - Read the log with `gh run view <run-id> --log-failed`. For e2e failures, also check the `playwright-report` artifact.
   - Fix the cause in the worktree, then commit and push.
   - Watch again.

   Repeat until every check passes. If it still can't pass, report the failing check and why; don't call the work done.
9. **Report** in the terminal, in this order:
   - The branch name and worktree path, the PR link, and the version it releases.
   - Each finding and how it was fixed, and each deferred finding with its `/intake` request.
   - Each validation command and its result, and the final CI status.
   - The **manual test plan**: the release's smoke test. Numbered steps a developer follows to check, by hand, each fix and each acceptance criterion of every reviewed issue, with the expected result of each step. Every command runs from the worktree's root and is ready to paste:
     - Step 1 is always `./run_local.sh`. It starts the worktree's compose stack and the studio dev server (http://localhost:5173, api on :8080), stopping any stack that collides with it, and prints the command that starts the harwood0 emulator. Don't tell the developer to run `make up` or `make run-studio` themselves.
     - Middle steps are the checks themselves, including any cli commands (e.g. `go run ./services/cli/cmd ...`) and emulator runs.
     - The last step is always `./cleanup_local.sh`.
   - **Releasing:** after the PR merges, run `/review-issues` again from the main checkout, which offers to tag it, or run `.claude/workflow/scripts/tag-release.sh --pr <pr>` directly. It tags the PR's merge commit and pushes the tag. It refuses if another issue PR merged after the reviewed commit, because that work wasn't reviewed.
   - An offer to write the test plan to a file.
   - Last, on its own line so it isn't lost above: `cd <worktree path>`.

## Abandoning

If the work can't be completed, push whatever is committed, if any, and report what is fixed, what blocked the rest, and where the worktree is. Don't tag anything.
