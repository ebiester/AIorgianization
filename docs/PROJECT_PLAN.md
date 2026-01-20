# Project Plan: AIorgianization

## Overview

This document outlines the implementation phases for AIorgianization - an Obsidian-native task and context management system for engineering managers.

## Architecture Summary

- **Storage:** Markdown files in Obsidian vault (no database)
- **UI:** Obsidian plugin for viewing/editing tasks
- **CLI:** Python (Click) for quick capture when not in Obsidian
- **MCP:** Python MCP server for Cursor CLI integration
- **Integrations:** Jira sync
- **Testing:** pytest (unit, integration, e2e)

---

## Phase Summary

| Phase | Name | Status | Focus |
|-------|------|--------|-------|
| 1 | Foundation | Done | Vault structure, CLI basics |
| 2 | Obsidian Plugin Core | Done | Task views, commands |
| 3 | Jira Integration | Done | Sync assigned issues |
| 4 | AI Integration | Done | MCP server for Cursor CLI |
| 5 | Polish | Not Started | Weekly review, refinements |

---

## Phase 1: Foundation

**Objective:** Establish vault structure and CLI for task file management.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Vault structure | Define folder layout (AIO/Tasks/, Projects/, People/, Dashboard/, Archive/) | Done |
| Task file format | YAML frontmatter + markdown spec (with dependencies) | Done |
| Project file format | Links, timeline, health queries | Done |
| Dashboard file format | Daily note integration with Dataview queries | Done |
| Python project setup | pyproject.toml, uv, pytest, ruff, mypy | Done |
| CLI scaffold | Python + Click setup | Done |
| Init command | `aio init <vault-path>` creates AIO directory structure | Done |
| VaultService | Locate and read Obsidian vault (Python) | Done |
| TaskService | Parse/write task markdown files (Python) | Done |
| Add command | Create task file in Inbox | Done |
| List command | Query tasks by status/folder | Done |
| Done command | Move task to Completed folder | Done |
| Dashboard command | Generate/append dashboard to daily note | Done |
| Archive commands | Archive tasks, projects, areas, people | Done |
| Date-based archive | `aio archive tasks --before <date>` | Done |
| Unit tests | Test services, utils, models | Done |
| Integration tests | Test CLI commands | Done |
| E2E tests | Test full workflows with fixtures | Done |

### Verification

```bash
aio init /path/to/vault
# Creates: AIO/ directory structure with Archive/ parallel folders

aio add "Test task" -d tomorrow
# Creates: AIO/Tasks/Inbox/2024-01-15-test-task.md

aio list inbox
# Lists tasks in AIO/Tasks/Inbox/

aio done "test-task"
# Moves to AIO/Tasks/Completed/2024/01/

aio dashboard
# Appends to daily note or creates AIO/Dashboard/2024-01-15.md

aio archive tasks --before 2024-01-01
# Moves old completed tasks to AIO/Archive/Tasks/
```

---

## Phase 2: Obsidian Plugin Core

**Objective:** Build Obsidian plugin with task views, commands, and dependency management.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Plugin scaffold | manifest.json, main.ts, esbuild | Done |
| Settings tab | Configure folder paths | Done |
| Task list view | Custom pane showing tasks | Done |
| Quick add modal | Command palette task entry | Done |
| Task edit modal | Edit frontmatter fields | Done |
| Status commands | Complete, start, defer, wait | Done |
| Right-click menu | Context actions on tasks | Not Started |
| Inbox view | Process items one-by-one | Done |
| Waiting-for view | Grouped by person | Not Started |
| Dependency management | Link tasks as blockedBy/blocks | Done (model only) |
| Dependency visualization | Show blocked tasks and blockers in views | Not Started |
| Blocked view | Tasks waiting on dependencies | Not Started |
| Location linking | Connect task to file path, line number, or URL | Done (model only) |
| Location navigation | Click to open file/URL from task view | Not Started |
| Subtask progress | Track and display subtask completion (e.g., "3/5") | Not Started |

### Verification

- Open Obsidian with plugin enabled
- Cmd+P → "AIo: Add task" → modal opens
- Create task → file appears in AIO/Tasks/Inbox/
- Open task list view → task visible
- Right-click → Complete → file moves to Completed/
- Link task as blocked by another → shows in Blocked view
- Complete blocking task → blocked task no longer shows blockers

---

## Phase 3: Jira Integration

**Objective:** Sync Jira issues to vault as task files.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Jira settings | URL, email, project keys in config | Done |
| JiraSyncService | Fetch issues via jira library | Done |
| Issue → Task mapping | Convert Jira issue to task file | Done |
| Status mapping | Map Jira statuses to folders | Done |
| Sync command (CLI) | `aio sync jira` | Done |
| Sync command (MCP) | `aio_sync_jira` tool | Done |
| Background sync | Periodic sync with status bar | Not Started |
| Sync cache | Track last sync, avoid duplicates | Done |

### Verification

```bash
aio sync jira
# Output: Synced 5 tasks (2 new, 3 updated)

# Check vault:
# Tasks/Next/2024-01-15-plat-123-fix-bug.md exists
# Frontmatter has jiraKey: PLAT-123
```

---

## Phase 4: AI Integration

**Objective:** MCP server exposing vault to Cursor CLI for AI assistance.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| MCP package | Python mcp SDK setup | Done |
| aio_add_task tool | Create task via MCP | Done |
| aio_list_tasks tool | Query tasks via MCP | Done |
| aio_complete_task tool | Complete task via MCP | Done |
| aio_start_task tool | Start task via MCP | Done |
| aio_defer_task tool | Defer task via MCP | Done |
| aio_delegate_task tool | Delegate task (alias for wait with person) via MCP | Not Started |
| aio_get_context tool | Read context packs | Done |
| aio_get_dashboard tool | Get daily dashboard | Done |
| aio_sync_jira tool | Sync Jira via MCP | Done |
| aio_jira_status tool | Get Jira status via MCP | Done |
| Context pack tools | Create, list, append context packs | Done |
| Task resources | Expose task lists as resources | Done |
| Cursor skill file | .cursor/skills/aio.md instructions | Not Started |
| MCP integration tests | Test tool invocations | Not Started |

### Verification

- Configure MCP server in Cursor (`~/.cursor/mcp.json`)
- "Add a task to review the roadmap by Friday"
- Cursor calls aio_add_task
- Task file created in vault

---

## Phase 5: Polish

**Objective:** Weekly review workflow and refinements.

### Deliverables

| Item | Description | Priority |
|------|-------------|----------|
| Weekly review wizard | Multi-step modal in plugin | P0 |
| Review tracking | Record review completion | P1 |
| Project views | Dataview integration or custom | P1 |
| Delegated summary | Days-since-delegated display | P1 |
| CLI improvements | Better output formatting | P2 |
| Documentation | README, setup guide | P1 |

---

## Work Breakdown by Component

### Python Package (aio/)

| Phase | Work |
|-------|------|
| 1 | Project setup, VaultService, TaskService, CLI (add/list/done), tests |
| 3 | JiraSyncService |
| 4 | MCP server, tools, resources |
| 5 | Polish, better output |

### Obsidian Plugin (obsidian-aio/)

| Phase | Work |
|-------|------|
| 2 | All plugin features (TypeScript) |
| 3 | Jira sync UI, settings |
| 5 | Weekly review, polish |

### Cursor Integration

| Phase | Work |
|-------|------|
| 4 | MCP config, skill file (.cursor/skills/aio.md) |

---

## Migration Notes

The Phase 1 prototype used TypeScript + SQLite + Drizzle. This has been replaced:

- **Before:** TypeScript CLI, tasks in `~/.aio/aio.db` (SQLite)
- **After:** Python CLI, tasks in `Vault/AIO/Tasks/*.md` (Markdown files)

The Python CLI rewrite is complete. All core functionality has been migrated.

---

## Next Actions

**Phase 5 (Polish) - Not Started:**

1. [ ] Implement weekly review wizard in Obsidian plugin
2. [ ] Add review tracking (record completion timestamps)
3. [ ] Implement Waiting-for view grouped by person
4. [ ] Add right-click context menu in plugin
5. [ ] Implement dependency visualization in task views
6. [ ] Add Blocked view for tasks waiting on dependencies
7. [ ] Implement location navigation (click to open file/URL)
8. [ ] Add subtask progress display
9. [ ] Create Cursor skill file (.cursor/skills/aio.md)
10. [ ] Write MCP integration tests
11. [ ] Add background Jira sync with status bar indicator
12. [ ] Add `delegate` as CLI alias for `wait` with required person argument
13. [ ] Add `aio_delegate_task` MCP tool (alias for wait with person)
