# Open Brain and Context Skills Test Plan

## Purpose

This plan verifies the task-centred open-brain workflow and the reusable AIO skills:

- `skills/action-capture` — captures substantive follow-up tasks with resume notes.
- `.cursor/skills/aio-context.md` — creates, reads, and updates Context-Packs.
- `skills/task-loop` — resumes one explicit task, records work, captures follow-ups, and promotes durable knowledge.

The Obsidian vault is the canonical source in every test. `.aio/index.sqlite` is derived state: removing it must never lose user content and a rebuild must reproduce the searchable documents and relationships.

## Test Levels

| Level | Scope | Location / command |
|---|---|---|
| Unit | Models, Markdown transformations, index, link handling, promotion | `tests/unit/` / `uv run pytest tests/unit` |
| Integration | CLI commands, MCP schemas/handlers, daemon events | `tests/integration/` / `uv run pytest tests/integration` |
| End-to-end | Complete harness task loop against a real temporary vault | `tests/e2e/` / `uv run pytest tests/e2e` |
| UAT | Human-visible behavior in Obsidian and an MCP-capable harness | See acceptance scenarios below |

Run `uv run ruff check .`, `uv run mypy aio`, and `uv run pytest` before release.

## Automated Coverage

### Task fields and work logs

- Parse legacy task files with neither `context` nor `lastWorked`; writing them remains compatible.
- Preserve and de-duplicate validated `context` wikilinks; reject missing targets, traversal, absolute external paths, and malformed links.
- Append the first `## Work Log` heading lazily and append subsequent timestamped entries below it.
- Verify every work-log field: harness, outcome, current state, decisions, next action, and references.
- Confirm `lastWorked` and `updated` are set, while existing task body and frontmatter are retained.
- Verify ambiguous and absent task queries return the existing user-friendly errors.

### Derived vault index

- Index Markdown title, body, tags, type/frontmatter, SHA-256 hash, explicit frontmatter links, and inline wikilinks.
- Verify FTS title/body/tag matching, scope filtering, result limit, excerpts, and match reason.
- Verify backlinks for direct links and removal of stale links after edits, rename, and delete.
- Confirm a no-op reconciliation does not rewrite unchanged rows; changing content changes its stored hash.
- Confirm malformed Markdown increments the error count without stopping other documents from indexing.
- Verify exclusions for `.aio`, `.obsidian`, trash, backup, hidden files, and configured private paths.
- Delete `.aio/index.sqlite`, run `aio index rebuild`, and compare document and relationship sets with the prior rebuild.

### Daemon reconciliation

- Start the daemon with a populated vault and assert it performs an initial index reconciliation.
- Create, modify, atomically replace, move, and delete a Markdown file while it runs; assert the index converges after debounce.
- Stop the daemon, change files, restart it, and assert startup reconciliation captures the changes.
- Simulate a missed file event and assert the five-minute periodic reconciliation corrects the index.
- Verify watcher changes outside task folders refresh derived search state without corrupting task cache data.

### MCP and CLI contracts

- `aio index status`, `aio index rebuild`, and `aio index reconcile` report document count, errors/pending state, last reconciliation, and exclusions.
- `aio_search` returns path, excerpt, entity metadata, and match reason; empty and invalid queries have clear responses.
- `aio_resume_task` returns the selected task, linked project/people/context, first-hop backlinks, recent work log, ranked related material, and honors `max_chars`.
- `aio_link_context` accepts only existing vault artifacts and reports invalid links without partially updating a task.
- `aio_record_work` writes one structured entry and is visible to a later `aio_resume_task` call.
- `aio_promote_knowledge` creates and updates ADR, Project, Area, Context-Pack, and Person destinations atomically, adds task provenance, and backlinks the task.
- Inject an atomic-write failure during promotion and confirm that no partial target artifact or task link remains.

## Skill Scenario Tests

### Action capture

| Scenario | Expected result |
|---|---|
| A conversation ends with one concrete follow-up | One inbox task has a verb-led title and concise Notes covering why, state, next action, and references. |
| Several independent follow-ups arise | Each becomes a separate task; no combined, ambiguous task is created. |
| Work is fully complete | No unnecessary follow-up task is created. |
| A blocker or uncertainty remains | The note captures the fact and labels uncertainty rather than inventing a conclusion. |
| MCP unavailable | `aio add --notes` produces the same task content as `aio_add_task(notes=...)`. |

### Context-Pack skill

| Scenario | Expected result |
|---|---|
| List packs before creating one | Existing matching pack is selected when appropriate. |
| Add content under a named section | Existing section is used or created; unrelated content is unchanged. |
| Add a file to a pack | Source content is copied with the expected attribution/relationship. |
| Create a Domain, System, and Operating pack | Each is stored in its configured category folder with title, tags, and description. |
| Invalid pack/file reference | The operation fails clearly and does not create a partial pack. |

### Task-loop skill

| Scenario | Expected result |
|---|---|
| Two harnesses select different tasks | Each resumes and records only its selected task; no global active-task state exists. |
| Resume a task with project, person, explicit context, and backlinks | Returned material is source-path-labelled and bounded by `max_chars`. |
| Work creates a substantive next action | The harness uses action capture, then records the created task ID in its outcome/reference. |
| Durable decision or operating knowledge emerges | It is promoted once to the correct canonical artifact with task provenance; transcript/reasoning/secrets are absent. |
| Search has no confident result | The harness retains evidence in the task log and creates an inbox organisation task rather than inventing a canonical destination. |

## End-to-End Acceptance Scenario

1. Create a project, person, context pack, and task linked to each.
2. Run `aio index rebuild`; search for a unique phrase in the project and verify its path and excerpt.
3. Call `aio_resume_task` for the task; verify linked material and a backlink appear in deterministic, character-limited context.
4. Call `aio_record_work` with an outcome, decision, next action, and source reference.
5. Use action capture to create the unresolved follow-up task with resume notes.
6. Call `aio_promote_knowledge` for the durable decision and verify its target file contains task provenance and the task's `context` contains the canonical link.
7. Restart the daemon (or delete `.aio/index.sqlite` and rebuild), then search again and verify the task, promotion, and backlinks remain discoverable.
8. Open each affected file in Obsidian and verify it remains readable and editable.

**Pass criteria:** all operations preserve Markdown-canonical state, the rebuilt index matches source content, and the harness can report every task and promoted file it created.

## Release Checklist

- [ ] Unit, integration, and E2E coverage added for new behavior.
- [ ] New MCP tool schemas and error paths covered.
- [ ] Daemon create/modify/atomic-save/move/delete/restart cases covered.
- [ ] Skill scenarios exercised in an MCP-capable harness.
- [ ] `uv run ruff check .`, `uv run mypy aio`, and `uv run pytest` pass.
- [ ] Manual Obsidian review confirms no migration is required and existing files remain usable.
