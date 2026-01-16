# Project Plan: AIorgianization

## Overview

This document outlines the implementation phases for AIorgianization - an Obsidian-native task and context management system for engineering managers.

## Architecture Summary

- **Storage:** Markdown files in Obsidian vault (no database)
- **UI:** Obsidian plugin for viewing/editing tasks
- **CLI:** Quick capture when not in Obsidian
- **Integrations:** Jira sync, Claude MCP
- **AI:** MCP server for Claude Code integration

---

## Phase Summary

| Phase | Name | Status | Focus |
|-------|------|--------|-------|
| 1 | Foundation | In Progress | Vault structure, CLI basics |
| 2 | Obsidian Plugin Core | Not Started | Task views, commands |
| 3 | Jira Integration | Not Started | Sync assigned issues |
| 4 | AI Integration | Not Started | MCP server for Claude |
| 5 | Polish | Not Started | Weekly review, refinements |

---

## Phase 1: Foundation

**Objective:** Establish vault structure and CLI for task file management.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Vault structure | Define folder layout (AIO/Tasks/, Projects/, People/, Dashboard/, Archive/) | Done (in docs) |
| Task file format | YAML frontmatter + markdown spec (with dependencies) | Done (in docs) |
| Project file format | Links, timeline, health queries | Done (in docs) |
| Dashboard file format | Daily note integration with Dataview queries | Done (in docs) |
| CLI scaffold | TypeScript + Commander setup | Partial (needs rewrite) |
| Init command | `aio init <vault-path>` creates AIO directory structure | Not Started |
| VaultService | Locate and read Obsidian vault | Not Started |
| TaskFileService | Parse/write task markdown files | Not Started |
| Add command | Create task file in Inbox | Not Started |
| List command | Query tasks by status/folder | Not Started |
| Done command | Move task to Completed folder | Not Started |
| Dashboard command | Generate/append dashboard to daily note | Not Started |
| Archive commands | Archive tasks, projects, areas, people | Not Started |
| Date-based archive | `aio archive tasks --before <date>` | Not Started |

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
| Plugin scaffold | manifest.json, main.ts, esbuild | Not Started |
| Settings tab | Configure folder paths | Not Started |
| Task list view | Custom pane showing tasks | Not Started |
| Quick add modal | Command palette task entry | Not Started |
| Task edit modal | Edit frontmatter fields | Not Started |
| Status commands | Complete, start, defer, wait | Not Started |
| Right-click menu | Context actions on tasks | Not Started |
| Inbox view | Process items one-by-one | Not Started |
| Waiting-for view | Grouped by person | Not Started |
| Dependency management | Link tasks as blockedBy/blocks | Not Started |
| Dependency visualization | Show blocked tasks and blockers in views | Not Started |
| Blocked view | Tasks waiting on dependencies | Not Started |
| Location linking | Connect task to file path, line number, or URL | Not Started |
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

| Item | Description | Priority |
|------|-------------|----------|
| Jira settings | URL, email, project keys in plugin settings | P0 |
| JiraSyncService | Fetch issues via jira.js | P0 |
| Issue → Task mapping | Convert Jira issue to task file | P0 |
| Status mapping | Map Jira statuses to folders | P0 |
| Sync command (CLI) | `aio sync jira` | P0 |
| Sync command (plugin) | Command palette trigger | P0 |
| Background sync | Periodic sync with status bar | P1 |
| Sync cache | Track last sync, avoid duplicates | P0 |

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

**Objective:** MCP server exposing vault to Claude for AI assistance.

### Deliverables

| Item | Description | Priority |
|------|-------------|----------|
| MCP package | @modelcontextprotocol/sdk setup | P0 |
| aio_add_task tool | Create task via MCP | P0 |
| aio_list_tasks tool | Query tasks via MCP | P0 |
| aio_complete_task tool | Complete task via MCP | P0 |
| aio_get_context tool | Read context packs | P0 |
| Task resources | Expose task lists as resources | P1 |
| Claude skill files | .claude/skills/aio/ instructions | P1 |

### Verification

- Configure MCP server in Claude Code
- "Add a task to review the roadmap by Friday"
- Claude calls aio_add_task
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

### CLI (@aio/cli)

| Phase | Work |
|-------|------|
| 1 | VaultService, TaskFileService, add/list/done commands |
| 3 | sync jira command |
| 5 | Polish, better output |

### Obsidian Plugin (obsidian-aio)

| Phase | Work |
|-------|------|
| 2 | All plugin features |
| 3 | Jira sync UI, settings |
| 5 | Weekly review, polish |

### MCP Server (@aio/mcp)

| Phase | Work |
|-------|------|
| 4 | All MCP features |

---

## Migration Notes

The Phase 1 prototype used SQLite + Drizzle. This has been replaced:

- **Before:** Tasks in `~/.aio/aio.db` (SQLite)
- **After:** Tasks in `Vault/Tasks/*.md` (Markdown files)

The existing CLI code needs rewriting to use VaultService instead of Drizzle.

---

## Next Actions

1. [ ] Rewrite CLI to use markdown files instead of SQLite
2. [ ] Implement VaultService (find vault, read files)
3. [ ] Implement TaskFileService (parse/write frontmatter)
4. [ ] Implement DashboardService (generate daily dashboard)
5. [ ] Test add/list/done/dashboard with real vault
6. [ ] Begin Obsidian plugin scaffold
