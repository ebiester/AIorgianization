---
name: aio-task-loop
description: Work a selected AIorgianization task safely using its assembled vault context, record the outcome, capture substantive follow-ups, and promote durable knowledge.
---

# AIO Task Loop

1. Orient with `aio agent dashboard` or `aio agent list`, then explicitly select one task. Never assume or persist a global active task.
2. Call `aio agent resume <task-id>` with the selected task ID. Treat the returned source paths as the working context; request more through `aio agent search` when needed.
3. Perform the work. Do not copy transcripts, hidden reasoning, secrets, or speculation into the vault.
4. Before ending, call `aio agent record-work <task-id> "<outcome>"` with current state, decisions, next action, references, and harness name as applicable.
5. Create a separate inbox task through `aio agent add "<title>" --notes "<context>"` for every substantive unresolved follow-up.
6. Promote only durable, session-supported knowledge with `aio agent promote-knowledge`. Select one of `adr`, `project`, `area`, `context-pack`, or `person`; report every affected path to the user.

The Obsidian vault is canonical. The local search index is disposable and may be rebuilt with `aio index rebuild`.
