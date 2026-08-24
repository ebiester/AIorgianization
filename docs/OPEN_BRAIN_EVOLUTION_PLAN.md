# Evolve AIO into a Task-Centered Open Brain

## Summary

Evolve AIO toward OB1's shared-memory vision while preserving the Obsidian vault as the only source of truth. Borrow OB1's agent gateway, automatic capture, retrieval, and reusable harness patterns—not its generic database-first "thought" ontology. [OB1's core](https://github.com/NateBJones-Projects/OB1/blob/main/docs/01-getting-started.md) centers on semantic search, recent-item browsing, statistics, and capture; AIO will provide comparable capabilities around tasks and BASB artifacts.

The primary experience becomes:

1. Codex or Claude lists and selects a task.
2. AIO assembles the task, project, people, dependencies, linked context, and relevant vault search results.
3. The harness performs the work.
4. AIO appends a concise work-log entry, automatically captures substantive follow-up tasks, and promotes durable knowledge into canonical notes.
5. The harness reports created tasks and promoted files.

No global "active task" state will be persisted. Each harness conversation explicitly carries its selected task ID, allowing multiple agents or sessions to work safely.

## Architecture and BASB Model

- Retain the existing vault layout without moving files:
  - `Tasks` is the action and attention layer.
  - `Projects` holds time-bound outcomes and current project context.
  - `Areas` holds ongoing responsibilities and standards.
  - `Context-Packs` serves as BASB Resources, using the existing Domain, System, and Operating categories.
  - `People` holds person-specific context.
  - `ADRs` holds durable decisions.
  - `Archive` holds inactive material.
- Add optional task frontmatter:
  - `context: []` — explicit wikilinks to relevant vault artifacts.
  - `lastWorked: datetime` — last recorded harness work.
- Extend task bodies with a lazily created `## Work Log`. Each entry records timestamp, harness, outcome, current state, decisions, next action, references, and promoted artifacts. Existing task files remain valid unchanged.
- Automatically route durable session knowledge:
  - Decisions → ADRs.
  - Project-specific state → linked Project.
  - Ongoing policy or responsibility → Area.
  - Reusable domain, system, or operating knowledge → Context-Pack.
  - Person-specific facts → Person.
- Prefer updating an existing directly linked artifact, then a confident search match. Create a new artifact only when its PARA category and subject are unambiguous. Otherwise retain the material in the task log and create an inbox task to organize it.
- Promotions contain only evidence from the session, include task provenance, use atomic writes, and are reported after completion. Do not persist transcripts, hidden reasoning, secrets, or speculative conclusions.

## Local Retrieval and Reindexing

- Create a disposable `.aio/index.sqlite` containing:
  - Document inventory and content hashes.
  - Parsed frontmatter and entity types.
  - SQLite FTS5 title/body/tag search.
  - Explicit frontmatter relationships and extracted wikilink edges.
  - Backlinks and document freshness metadata.
- Keep the index strictly derived: deleting it and rebuilding from Markdown must reproduce the same searchable state.
- Expand the daemon watcher from `AIO/Tasks` to the configured vault:
  - Debounce create/modify/move/delete events.
  - Exclude `.aio`, `.obsidian`, trash, backups, generated dashboards, and configured private globs.
  - On startup, reconcile relative path, size, modification time, and SHA-256 content hash.
  - Run reconciliation every five minutes by default to recover from missed events or Obsidian Sync changes.
  - Correctly remove stale entries after renames and deletions.
- Add:
  - `aio index status` — indexed count, pending/error count, last reconciliation, exclusions.
  - `aio index rebuild` — recreate the index from the vault.
  - `aio index reconcile` — perform an incremental scan immediately.
- First release retrieval combines metadata filters, FTS, explicit links, and backlinks. Add on-device embeddings in a later milestone after real retrieval misses have been evaluated; embeddings remain rebuildable and never authoritative.

## Agent and Public Interfaces

- Add JSON agent CLI commands:
  - `aio agent search <query> [--scope <folder>] [--limit <n>]` — search indexed vault content.
  - `aio agent resume <query> [--max-chars <n>]` — return the task plus project, people, dependencies, explicit context, first-hop backlinks, recent work log, and ranked related material.
  - `aio agent link-context <query> <targets...>` — add validated vault wikilinks to a task.
  - `aio agent record-work <query> <outcome> [...]` — append a structured work-log entry and update `lastWorked`.
  - `aio agent promote-knowledge <query> <target> --category <category> --content <content>` — atomically update or create a canonical artifact and backlink it to the task.
  - `aio agent index-status` — expose index health to harnesses.
- Extend task serialization to include `context`, `last_worked`, and sufficient task body/work-log information for resumption.
- Preserve existing task, CLI, and plugin behavior. The `--notes` support on `aio agent add` becomes the foundation for automatic resume-context capture.
- Add a shared task-loop skill usable by Codex and Claude:
  - Use dashboard/list tools to orient.
  - Resolve one task and call `aio_resume_task`.
  - Perform work using retrieved context with source paths.
  - Call `aio_record_work` before the session ends.
  - Automatically create substantive follow-up tasks.
  - Automatically promote durable knowledge and then notify the user with the affected files.
- Keep the Obsidian plugin as the human review/edit surface. Harness/CLI parity takes priority over new plugin UI in this release.

## Delivery Sequence

1. **Vault index foundation**
   - Implement inventory, FTS, link graph, exclusions, watcher expansion, startup/periodic reconciliation, and index CLI commands.
2. **Task-centered context assembly**
   - Add task relationship fields, work-log handling, search, resume, linking, and index-health agent CLI interfaces.
3. **Harness workflow**
   - Add the shared Codex/Claude task-loop skill, automatic follow-up capture, knowledge routing, provenance, and promotion notifications.
4. **Retrieval evaluation**
   - Record unsuccessful or low-confidence searches without storing prompt content; use representative test queries to decide local embedding model and vector implementation.
5. **Open Brain extensions**
   - Add on-device semantic retrieval, then task-backed ticket drafting, documentation generation, meeting briefings, and weekly knowledge-distillation workflows.

## Test and Acceptance Plan

- Unit-test frontmatter compatibility, work-log parsing, relationship extraction, routing, provenance, FTS ranking, exclusions, hashes, and atomic promotion.
- Test index convergence for Obsidian edits while the daemon is running, edits while stopped, atomic-save patterns, rename, delete, sync arrival, malformed Markdown, and missed watcher events.
- Verify rebuild and incremental reconciliation produce equivalent document and relationship sets.
- Integration-test every agent CLI interface, context ordering, character limits, ambiguous task matching, invalid links, and promotion failures.
- End-to-end test the complete loop: create/select task → resume context → record work → create follow-up → promote knowledge → restart daemon → retrieve the same state.
- Confirm existing vaults require no migration, existing tasks and plugin views remain usable, and deleting `.aio/index.sqlite` loses no source information.
- Run the full Python and TypeScript suites, Ruff with zero errors, mypy, actual CLI success/error cases, and update Architecture, PRD, Project Plan, User Manual, UAT Plan, README, and agent instructions.

## Assumptions

- The system remains single-user, local-first, and Markdown-canonical.
- Automatic writes are allowed for inbox tasks, task work logs, and confident canonical promotions; every promotion is reported afterward.
- Existing folders are retained and their BASB roles are documented rather than renamed.
- Semantic embeddings are deferred until the lexical/link implementation has measurable retrieval examples.
- Slack is not an AIO interface. Codex and Claude communicate through the same local CLI contract and reusable harness skill.
