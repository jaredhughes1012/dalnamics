# Refinement procedure

Shared by `/refine` (input: an existing issue) and `/intake` (input: an inline description). Both follow every step below. They differ only in where the request comes from (step 1) and how the result is published (step 8).

The output is a GitHub issue labelled `refined` whose body follows [issue-template.md](issue-template.md). A separate `/implement` session will build from that body without talking to the requester, so the plan has to answer every question it would otherwise need to ask.

Scripts live in `.claude/workflow/scripts/` and are run from the repo root.

## 1. Gather context

Run `.claude/workflow/scripts/context.sh [issue-number]`. Pass the number for `/refine`; pass nothing for `/intake`. It prints the issue with its comments, every other open issue, and the outline of `docs/*.md`.

- `/refine`: the request is the issue body and comments. If the issue already has the `refined` label, say so and ask whether to re-refine. When re-refining, the request is the existing plan plus whatever the user wants changed, and the "Original request" section is carried over unchanged.
- `/intake`: the request is the inline description.

## 2. Understand the system

- Read `docs/arch.md` and `docs/CONTRIBUTION.md` in full, then each feature doc that the request touches.
- Explore the code the request touches. Use an Explore agent when finding it means sweeping many files. Find the existing code the change will follow as a pattern, and whether any part of the request already exists.
- Don't ask the user anything the code or docs answer.

## 3. Check for overlap with open issues

Compare the request with every other open issue from step 1. Classify each as:

- **Unrelated**: ignore it.
- **Prerequisite**: the request needs something that issue will build. This issue depends on it.
- **Overlap**: both describe some of the same work.

If anything overlaps, or is a prerequisite, tell the user which issues and what is shared, and propose a split before going on:

- Work already described by an existing issue stays there, and this issue depends on it. **Never edit an existing issue or add work to it.**
- This issue keeps only the work no open issue covers. Design it to build on the existing issues' work rather than duplicating it.
- If the request contains separable pieces of work with no existing issue, propose them as new issues of their own, each refined with the same template.

Confirm the split with AskUserQuestion before planning further.

## 4. Ask follow-up questions

Requests are usually thin. Ask until every template section can be filled in without guessing: intended behavior, who uses it and from which client (studio, cli, or both), edge cases and errors, permissions, data that must persist, what is out of scope, and how success is checked.

- Use AskUserQuestion with up to four questions per round. Put your recommendation first and mark it "(Recommended)". Offer concrete options grounded in the code you read.
- Ask in rounds; let earlier answers shape later questions.
- Stop when the answers would no longer change the plan. Record every answer under **Decisions**.

## 5. Draft the plan

Fill in [issue-template.md](issue-template.md) in a scratchpad file, one per issue when splitting.

- **Relevant docs** and **Code map** are what make `/implement` fast. Use real section anchors and real paths, and name the existing code to copy for each kind of change.
- **Steps** follow CLAUDE.md's order: spec first, `make generate`, then implementation; SQL and migrations before the code that uses them.
- **Tests** name the behaviors to cover, at both the unit and e2e level, following the patterns in CLAUDE.md.
- **Docs to update** follows `docs/CONTRIBUTION.md`: shared data and new services go in arch.md, flows go in the domain's feature doc. A new domain gets a new feature doc and an entry in the arch.md index.
- **Depends on** lists issues by number. For new issues from a split, create those first (step 8) so their numbers exist.
- **Original request** is the requester's text, verbatim.

## 6. Review with the user

Print the full plan, plus a one-line title, in the terminal. Ask for changes, apply them, and repeat until the user approves. Nothing is published before approval.

## 7. Title

Write an imperative title of at most about 70 characters that describes the outcome, e.g. "Let users reset a forgotten password". For `/refine`, keep the existing title unless it no longer fits; if it doesn't, propose the new one in step 6.

## 8. Publish

Create issues that others depend on first, then the ones that depend on them.

- New issue (`/intake`, or a split): `.claude/workflow/scripts/issue-create.sh "<title>" <body-file>`
- Existing issue (`/refine`): `.claude/workflow/scripts/issue-publish.sh <number> <body-file> ["<new title>"]`

Both scripts add the `refined` label and print `#<number> <url>`. Finish by listing every issue published, with links and dependencies, and the command to start each one: `/implement <number>`.
