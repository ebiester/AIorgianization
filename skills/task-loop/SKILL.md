---
name: aio-task-loop
description: Work a selected AIorgianization task safely using its assembled vault context, record the outcome, capture substantive follow-ups, and promote durable knowledge.
---

# AIO Task Loop

1. Orient with `aio_get_dashboard` or `aio_list_tasks`, then explicitly select one task. Never assume or persist a global active task.
2. Call `aio_resume_task` with the selected task ID. Treat the returned source paths as the working context; request more through `aio_search` when needed.
3. Perform the work. Do not copy transcripts, hidden reasoning, secrets, or speculation into the vault.
4. Before ending, call `aio_record_work` with the observed outcome, current state, decisions, next action, references, and harness name.
5. Create a separate inbox task through `aio_add_task` for every substantive unresolved follow-up, including concise resume notes.
6. Promote only durable, session-supported knowledge with `aio_promote_knowledge`. Select one of `adr`, `project`, `area`, `context-pack`, or `person`; report every affected path to the user.

The Obsidian vault is canonical. The local search index is disposable and may be rebuilt with `aio index rebuild`.
