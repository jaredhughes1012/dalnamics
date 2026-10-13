---
name: refine
description: Turn a thin GitHub issue into a refined, implementation-ready plan, through follow-up questions and a check for overlap with other open issues. Rewrites the issue body and labels it refined.
argument-hint: <issue-number>
disable-model-invocation: true
---

Refine GitHub issue #$ARGUMENTS.

Follow `.claude/workflow/refine.md` from step 1 through step 8, as `/refine`:

- The request is issue #$ARGUMENTS. Gather context with `.claude/workflow/scripts/context.sh $ARGUMENTS`.
- Publish by rewriting this issue with `.claude/workflow/scripts/issue-publish.sh $ARGUMENTS <body-file>`. Any work split into new issues is created with `issue-create.sh` first.

If no issue number was given, or the issue doesn't exist or is closed, say so and stop.
