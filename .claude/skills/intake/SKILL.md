---
name: intake
description: Turn an inline feature request into a refined, implementation-ready GitHub issue, through follow-up questions and a check for overlap with open issues. Same process as /refine, but the request is typed inline instead of read from an issue.
argument-hint: <description of the work>
disable-model-invocation: true
---

Refine this request into a new GitHub issue:

> $ARGUMENTS

Follow `.claude/workflow/refine.md` from step 1 through step 8, as `/intake`:

- The request is the text above. Gather context with `.claude/workflow/scripts/context.sh` (no issue number).
- Publish by creating the issue with `.claude/workflow/scripts/issue-create.sh "<title>" <body-file>`. The text above goes verbatim into the plan's "Original request" section.

If no description was given, ask for one.
