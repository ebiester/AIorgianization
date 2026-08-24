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
| Integration | CLI commands, JSON agent command envelopes, daemon events | `tests/integration/` / `uv run pytest tests/integration` |
| End-to-end | Complete harness task loop against a real temporary vault | `tests/e2e/` / `uv run pytest tests/e2e` |
| UAT | Human-visible behavior in Obsidian and a CLI-capable chat harness | See acceptance scenarios below |

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

### CLI contracts

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
| Chat skill capture | `aio agent add --notes` produces the expected resumable task content. |

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

## Implementable Acceptance Tests

### Shared setup

Implement every acceptance test with a fresh `tmp_path` vault; do not use a developer's real vault.

1. Create `TestVault/.obsidian/`, then initialise it through `VaultService(vault).initialize()`.
2. Create a `TaskService`, `VaultIndex`, and `OpenBrainService` using that vault service.
3. For agent-command cases, invoke `aio agent` through Click's test runner with `--vault` set to the temporary vault.
4. Use deterministic fixture names and marker phrases below, such as `OB-unique-phrase-001`, so an assertion cannot match unrelated fixture content.
5. Assert both the API response and the resulting Markdown/frontmatter. For index tests, also query SQLite or the index service directly where needed.
6. Clean up only the temporary vault. Do not rely on global AIO configuration or an existing index.

### AT-OB-001: Rebuild a disposable lexical index

**Setup:** Create `AIO/Projects/Launch.md` with `# Launch` and body text containing `OB-unique-phrase-001`; create `AIO/Areas/Engineering.md` containing `[[AIO/Projects/Launch]]`.

1. Call `VaultIndex.reconcile(rebuild=True)`.
2. Assert that the result reports two indexed documents and zero errors.
3. Call `search("OB-unique-phrase-001")`.
4. Assert one result has path `AIO/Projects/Launch.md`, title `Launch`, a non-empty excerpt, entity metadata, and match reason `full-text match`.
5. Call `backlinks("AIO/Projects/Launch.md")`.
6. Assert it returns `AIO/Areas/Engineering.md`.
7. Delete `.aio/index.sqlite`, construct a new `VaultIndex`, and call `reconcile(rebuild=True)`.
8. Repeat steps 3–6 and assert the same path and backlink are returned.

### AT-OB-002: Incremental index changes converge

**Setup:** Use the indexed fixture from AT-OB-001.

1. Replace the phrase in `Launch.md` with `OB-unique-phrase-002` and change the backlink target in `Engineering.md` to another existing note.
2. Call `reconcile()` without `rebuild=True`.
3. Assert search for phrase 001 returns no Launch result and search for phrase 002 returns Launch.
4. Assert the old backlink is absent and the new backlink is present.
5. Rename `Launch.md` to `Launch-v2.md`, call `reconcile()`, and assert the old path is absent from search results.
6. Delete `Launch-v2.md`, call `reconcile()`, and assert it is absent from the document inventory and links table.

### AT-OB-003: Task context and work-log persistence

**Setup:** Create `AIO/Projects/Roadmap.md`, then create task `Ship widget` in Inbox.

1. Call `TaskService.link_context(task.id, ["AIO/Projects/Roadmap"])`.
2. Assert task frontmatter contains `context: ["[[AIO/Projects/Roadmap]]"]`.
3. Call `record_work` with outcome `Validated rollout`, current state, one decision, next action, two references, and harness `codex`.
4. Re-read the task from disk.
5. Assert its body contains exactly one `## Work Log` heading and an entry with each supplied field.
6. Assert frontmatter contains a parseable `lastWorked` timestamp and an updated timestamp.
7. Call `record_work` again, then assert there are two dated entries and still one Work Log heading.

### AT-OB-004: Invalid context links are safe

**Setup:** Create a task with no context links and record its original Markdown text.

1. Attempt `link_context` with a missing vault file.
2. Assert it raises the documented file-not-found error.
3. Attempt `link_context` with `../../outside.md` and with an absolute external path.
4. Assert each attempt raises a validation error.
5. Re-read the task and assert its Markdown and `context` list are unchanged from the original.

### AT-OB-005: Resume assembles bounded, linked context

**Setup:** Create a task linked to a Project and explicit Context-Pack; create a separate Area note with an inline link to the task file. Give each artifact a unique marker phrase.

1. Rebuild the index.
2. Call `OpenBrainService.resume(task.id, max_chars=800)`.
3. Assert the response task has the selected ID, path, body, explicit context, and `last_worked` key.
4. Assert linked context includes the Project and Context-Pack source paths.
5. Assert first-hop backlink content from the Area note is included.
6. Assert every included document has a source path and the combined returned text does not exceed the requested budget (allow only fixed response metadata outside the budget).
7. Assert ranked related material contains an artifact matching a unique task title/tag term.

### AT-OB-006: Agent CLI contract for search and work recording

**Setup:** Create and index a task plus one linked project in the temporary vault.

1. Invoke `aio agent search "<unique phrase>"`.
2. Parse the JSON response and assert path, excerpt, entity type, and match reason exist.
3. Invoke `aio agent link-context <task-id> AIO/Projects/<project>`; assert `ok: true` and the task frontmatter link.
4. Invoke `aio agent record-work <task-id> "Validated rollout"`; assert `ok: true`.
5. Invoke `aio agent resume <task-id>` and assert its JSON response contains the new Work Log entry.
6. Invoke `aio agent index-status`; assert it reports the index path, document count, exclusions, and last reconciliation.
7. Invoke each command with a missing task or invalid link and assert an `ok: false` JSON response, not a traceback.

### AT-OB-007: Knowledge promotion is canonical and atomic

**Setup:** Create a task named `Decide rollout`, record evidence for a staged rollout, and construct `OpenBrainService`.

1. Call `promote(task.id, "Staged rollout", "adr", "Use staged rollout.", None, None)`.
2. Assert `AIO/ADRs/Staged-rollout.md` exists and has an H1, supplied evidence, and a provenance link to the task's actual vault-relative path and ID.
3. Re-read the task and assert its `context` includes the ADR wikilink.
4. Promote a second statement to the same target with `section="Consequences"`.
5. Assert the existing artifact is updated under that section rather than a duplicate file being created.
6. Repeat steps 1–3 once each for `project`, `area`, `context-pack`, and `person`; assert each target is under the category's configured folder.
7. Inject a `write_frontmatter` failure for a new target, then call promotion.
8. Assert the call raises, no partial target file exists, and the task did not gain a link to that target.

### AT-OB-008: Daemon catches vault-wide edits

**Setup:** Create a task and start `VaultCache`/daemon services with the temporary vault; set a short reconciliation interval only in the test fixture.

1. Assert startup creates or reconciles `.aio/index.sqlite`.
2. Create a Project Markdown file outside `AIO/Tasks`; wait until the debounce condition is satisfied.
3. Assert `VaultIndex.search` finds its unique phrase.
4. Modify the file using an atomic-save pattern (write temporary file then rename); assert search returns the revised phrase.
5. Rename and then delete the file; after each operation, assert stale search records and backlinks are removed.
6. Stop the daemon, create a note, restart it, and assert startup reconciliation indexes the note.
7. Stop the daemon and assert its observer and periodic timer are no longer active.

### AT-OB-009: Action-capture skill creates a resumable follow-up

**Setup:** Invoke `aio agent add` against the temporary vault. Provide a conversation fixture with one unresolved approval request, current state, decision constraint, and source reference.

1. Apply the action-capture skill's workflow to the fixture.
2. Assert one task is created with a specific verb-led title, not a generic noun phrase.
3. Assert `notes` contains Why, Current state, Next action, and References from the fixture without fabricated facts.
4. Read the saved task and assert the same notes occur beneath `## Notes`.
5. Repeat with two independent follow-ups and assert two separate task IDs are created.
6. Repeat with a completed-only fixture and assert no task is created.

### AT-OB-010: Context-Pack skill selects and updates the right artifact

**Setup:** Create an existing System context pack named `Payments` with a `## Compliance` section and a separate source ADR.

1. List context packs and assert `Payments` is discoverable as a System pack.
2. Call `aio_add_to_context_pack` for `Payments`, content `OB-context-addition`, and section `Compliance`.
3. Assert the marker is appended under `## Compliance`; assert unrelated sections are byte-for-byte unchanged.
4. Call `aio_add_file_to_context_pack` with the source ADR and `References` section.
5. Assert the copied source material is in the pack and any service-managed source attribution is present.
6. Create one Domain and one Operating pack; assert the files are in their respective folders with requested tags and description.
7. Attempt to update a nonexistent pack and add a file outside the vault; assert each fails without creating a partial artifact.

### AT-OB-011: Task-loop isolates concurrent task selection

**Setup:** Create two distinct tasks, each with a different unique Project marker. Construct two independent harness sessions or service instances.

1. Session A resumes task A; session B resumes task B.
2. Assert each response contains only its own selected task as `task.id` and its own linked Project marker.
3. Record work for A from session A and work for B from session B.
4. Assert each task contains only its own Work Log entry.
5. Assert no vault file, config entry, or service state persists a global `active task` / `activeTask` value.

**Pass criteria:** every acceptance test preserves Markdown-canonical state, emits user-facing failures instead of tracebacks, and leaves a rebuilt index equivalent to the source vault.

## Release Checklist

- [ ] Unit, integration, and E2E coverage added for new behavior.
- [ ] New agent-command JSON envelopes and error paths covered.
- [ ] Daemon create/modify/atomic-save/move/delete/restart cases covered.
- [ ] Skill scenarios exercised in a CLI-capable chat harness.
- [ ] `uv run ruff check .`, `uv run mypy aio`, and `uv run pytest` pass.
- [ ] Manual Obsidian review confirms no migration is required and existing files remain usable.
