# AIO Task Management

Use the local JSON CLI, `aio agent`, for task and context work.

## Default Flow

1. Use `aio agent dashboard` for “today”, “on my plate”, or planning questions.
2. Use `aio agent list` for status-specific views such as `inbox`, `next`, `waiting`, `today`, or `overdue`.
3. Use `aio agent add "<title>" [--due <date>] [--notes <markdown>]` for quick capture.
4. Use `aio agent complete`, `aio agent start`, `aio agent defer`, or `aio agent wait` for status changes.
5. For focused work, select one task, run `aio agent resume <id>`, and finish with `aio agent record-work <id> "<outcome>"`.
6. Use `aio agent search`, `aio agent link-context`, and `aio agent promote-knowledge` only with evidence from the vault or current work.

## Safety

- Parse the JSON response; successful commands return `"ok": true`.
- Resolve ambiguous titles before a mutation and prefer task IDs.
- Include Why, Current state, Next action, and References in `--notes` when future context matters.
- Promote only observed, durable knowledge. Never save secrets, transcripts, hidden reasoning, or speculation.

## Examples

- “What's on my plate today?” → `aio agent dashboard`
- “Show my inbox” → `aio agent list inbox`
- “Add a task to review the roadmap by Friday” → `aio agent add "Review the roadmap" --due friday`
- “Delegate API docs to Sarah” → `aio agent add "API docs" --assign Sarah`
- “Resume AB2C” → `aio agent resume AB2C`
