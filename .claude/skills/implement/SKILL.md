---
name: implement
description: Implement a refined GitHub issue in its own git worktree, with unit and e2e tests, doc updates, and a draft PR, then print a manual test plan. Run in plan mode, so every question is asked before work starts.
argument-hint: <issue-number>
disable-model-invocation: true
---

Implement GitHub issue #$ARGUMENTS.

The issue body is a plan written by `/refine` or `/intake` from [issue-template.md](../../workflow/issue-template.md). Treat its **Decisions** as settled and don't re-ask them. Scripts live in `.claude/workflow/scripts/` and are run from the main checkout's root.

The developer is refining other work while this runs. Ask every question during planning (phase 1), so that after the plan is approved the work runs to the end without them.

## Phase 1: Plan (read-only)

1. **Load the issue:** `gh issue view $ARGUMENTS --comments`. Stop and report if any of these is true:
   - It is closed.
   - It lacks the `refined` label or the `<!-- refined-plan v1 -->` marker. Suggest `/refine $ARGUMENTS`.
   - It has the `in-progress` label. Another session owns it.
2. **Check dependencies:** run `deps.sh $ARGUMENTS`. If it exits non-zero, list the blocking issues and stop.
3. **Read the docs:** CLAUDE.md, `docs/arch.md`, `docs/CONTRIBUTION.md`, and every section under the plan's **Relevant docs**.
4. **Review the code:** read every path in the **Code map**, and the code around it, until you know exactly which files change. Check for drift since refinement with `git log --oneline --since=<issue updatedAt> -- <paths>`. Changed code, or something the plan assumes that is missing or now different, is a gap to resolve.
5. **Check the docs:** confirm the plan's **Docs to update** against `docs/CONTRIBUTION.md`, and add anything it missed.
6. **Ask:** resolve real gaps only (drift, ambiguity, conflicts with the code) with AskUserQuestion, recommendation first. If an answer changes the plan, note it in your plan as an issue update to make in phase 2.
7. **Write the plan** for approval:
   - Branch `issue/$ARGUMENTS-<slug>`, where `<slug>` is 2–4 kebab-case words.
   - The steps at file level.
   - Every unit and e2e test to add.
   - The docs sections to change.
   - The validation commands.
   - Any issue updates from step 6.

   Then exit plan mode.

## Phase 2: Implement (after approval)

1. **Claim:** run `claim.sh $ARGUMENTS`. If it fails, stop and report.
2. **Create the worktree:** run `worktree.sh $ARGUMENTS <slug>` and note the printed path and branch. From here on:
   - Every file read and edit uses absolute paths inside the worktree.
   - Every command runs with the worktree as its working directory.
   - Never edit the main checkout.
3. **Update the issue** body with any changes from phase 1, step 6: `gh issue edit $ARGUMENTS --body-file <file>`.
4. **Implement** the steps in order, following CLAUDE.md:
   - Spec first, then `make generate`.
   - SQL and migrations before the code that uses them.
   - Handlers return domain sentinel errors.
5. **Write the tests:**
   - Unit tests for every behavior and error path (Go: testify and gomock; studio: Vitest via `renderRoute` and `mockApi`).
   - Playwright e2e tests in `test/studio` for every user-facing flow in the acceptance criteria.
6. **Update the docs** listed in the plan, following `docs/CONTRIBUTION.md`.
7. **Validate locally** with the same checks CI runs: `make generate` (confirm it leaves no diff), then `make lint`, `make test`, `make test-e2e`, and `make build`. Playwright reuses a stack that is already running, so run `./run_local.sh` in the worktree before `make test-e2e` (it stops any colliding stack and starts the worktree's), and `./cleanup_local.sh` once e2e passes. Fix failures and rerun until all pass. If something can't pass, don't hide it; report it in step 10 and in the PR.
8. **Self-review:** read the full diff against `origin/main`. Check it against each acceptance criterion, look for leftover debug code, and confirm generated files were regenerated rather than hand-edited.
9. **Ship:**
   - Commit with a message that summarizes the change and ends with `Closes #$ARGUMENTS`.
   - Push with `git push -u origin <branch>`.
   - Open a draft PR: `gh pr create --draft --base main --title "<issue title>" --body-file <file>`. The body holds a summary, `Closes #$ARGUMENTS`, the validation results, and the test plan.

   Leave the `in-progress` label on; the issue closes when the PR merges.
10. **Pass CI:** CI (`.github/workflows/ci.yml`) is the final gate. Run `gh pr checks <pr> --watch --fail-fast`. On a failure:
    - Read the log with `gh run view <run-id> --log-failed`. For e2e failures, also check the `playwright-report` artifact.
    - Fix the cause in the worktree, then commit and push.
    - Watch again.

    Repeat until every check passes. If it still can't pass, report the failing check and why; don't call the work done.
11. **Report** in the terminal, in this order:
    - The branch name and the worktree path.
    - The PR link.
    - Each validation command and its result, and the final CI status.
    - The **manual test plan**: numbered steps a developer follows to check each acceptance criterion by hand, with the expected result of each step. Every command runs from the worktree's root and is ready to paste, with the issue number filled in:
      - Step 1 is always `./run_local.sh`. It starts the worktree's compose stack and the studio dev server (http://localhost:5173, api on :8080), stopping any stack that collides with it, and prints the command that starts the harwood0 emulator. Don't tell the developer to run `make up` or `make run-studio` themselves.
      - Middle steps are the checks themselves, including any cli commands (e.g. `go run ./services/cli/cmd ...`) and emulator runs.
      - The last step is always `./cleanup_local.sh`.

      Depart from this only when the scripts can't cover the change (e.g. it needs a different env, a service the scripts don't start, or no running stack at all). Then say why, and give the exact commands to use instead and to tear them down.
    - An offer to write the test plan to a file.
    - Last, on its own line so it isn't lost above: `cd <worktree path>`.

## Abandoning

If the work can't be completed:
- Run `release.sh $ARGUMENTS`.
- Push whatever is committed, if any.
- Report what is done, what blocked it, and where the worktree is.
