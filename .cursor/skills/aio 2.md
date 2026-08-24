# AIO Task Management

Use the AIO MCP server when the user asks about tasks, deadlines, projects, delegated work, or daily planning.

## Default Flow

1. Use `aio_get_dashboard` for "today", "on my plate", or planning questions.
2. Use `aio_list_tasks` for status-specific views such as inbox, next, waiting, today, or overdue.
3. Use `aio_add_task` for quick capture. Include `due`, `project`, or `assign` when the user provides them.
4. Use `aio_complete_task`, `aio_start_task`, `aio_defer_task`, or `aio_delegate_task` for status changes.
5. Use `aio_get_context` when the user asks for project or domain context from context packs.
6. For focused execution, select a task and call `aio_resume_task`; finish with `aio_record_work`. Use `aio_search` for additional vault material and `aio_link_context` for validated explicit links.
7. Capture substantive follow-ups with `aio_add_task` and promote durable, evidenced knowledge using `aio_promote_knowledge`.

## Examples

- "What's on my plate today?" -> `aio_get_dashboard()`
- "Show my inbox" -> `aio_list_tasks({status: "inbox"})`
- "Add a task to review the roadmap by Friday" -> `aio_add_task({title: "Review the roadmap", due: "friday"})`
- "Delegate API docs to Sarah" -> `aio_add_task({title: "API docs", assign: "Sarah"})`
- "Mark AB2C done" -> `aio_complete_task({query: "AB2C"})`

The Obsidian vault is the source of truth. Do not invent task state if the MCP server can answer it.
