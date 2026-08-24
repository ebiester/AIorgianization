---
name: manage-aio
description: Manage an AIorgianization (AIO) Obsidian vault through its local CLI. Use for conversational task capture, inbox and dashboard reviews, task status changes, delegation, vault search, resuming task context, recording work, linking context, or promoting durable knowledge in local or Remote Codex chats. Do not use when the `aio` CLI or its configured vault is unavailable.
---

# Manage AIO

Use the JSON-only `aio agent` commands. Treat the Obsidian vault as canonical and never edit task Markdown directly when a command exists.

## Preflight

1. Run `command -v aio` if CLI availability is unknown.
2. Run `aio agent --help` if command compatibility is unknown.
3. If AIO cannot discover its vault, ask the user to configure `AIO_VAULT_PATH` on the host. Do not guess a vault path.
4. Parse the JSON response. A successful command has `"ok": true`; a failed command exits nonzero and returns `"ok": false` on stderr.

## Choose commands

- Show the inbox: `aio agent list inbox`
- Show next actions: `aio agent list next`
- Show today and overdue: `aio agent list today`
- Show waiting items: `aio agent list waiting`
- Show all active tasks: `aio agent list`
- Create: `aio agent add "<title>" [--due <date>] [--project <name>] [--notes <markdown>]`
- Create and delegate: add `--assign <person>`; add `--create-person` only when the user wants a missing person created.
- Start: `aio agent start <id>`
- Complete: `aio agent complete <id>`
- Defer: `aio agent defer <id>`
- Wait: `aio agent wait <id> [person]`
- Generate a dashboard: `aio agent dashboard`
- Search vault context: `aio agent search "<query>" [--scope <folder>]`
- Resume a task: `aio agent resume <id>`
- Link context: `aio agent link-context <id> <vault-relative-path>...`
- Record work: `aio agent record-work <id> "<outcome>" [--current-state ...] [--decisions ...] [--next-action ...] [--reference ...]`
- Promote durable knowledge: `aio agent promote-knowledge <id> <target> --category <category> --content "<content>"`
- Inspect index health: `aio agent index-status`

Use `aio --vault <path> agent ...` only when the user explicitly supplies a different vault for the operation.

## Work safely

- Prefer exact task IDs for mutations. If only a title is known, list or search first and use the returned ID.
- When AIO reports multiple matches, present the matching IDs and ask the user to choose; do not select arbitrarily.
- Confirm the interpreted title, due date, project, or assignee in the response after creating a task.
- Include useful capture context in `--notes`: why the task exists, constraints, current state, next action, and relevant references. Do not store transcripts, hidden reasoning, credentials, or secrets.
- Do not create a missing project or person unless the user requested it or clearly authorized the relationship.
- Do not promote speculative information. Promote only observed, durable knowledge with task provenance.
- Report concise human-readable results rather than pasting raw JSON unless the user requests it.

## Task work loop

When working on a selected task rather than only managing its status:

1. Call `aio agent resume <id>` before substantive work.
2. Use returned task context and linked material; do not treat related search results as authoritative without checking them.
3. Complete the requested work.
4. Call `aio agent record-work` before ending, recording the outcome and next action when one remains.
5. Link or promote new durable context only when warranted.
