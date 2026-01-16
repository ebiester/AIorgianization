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
| Vault structure | Define folder layout (Tasks/, Projects/, People/, etc.) | Done (in docs) |
| Task file format | YAML frontmatter + markdown spec | Done (in docs) |
| CLI scaffold | TypeScript + Commander setup | Partial (needs rewrite) |
| VaultService | Locate and read Obsidian vault | Not Started |
| TaskFileService | Parse/write task markdown files | Not Started |
| Add command | Create task file in Inbox | Not Started |
| List command | Query tasks by status/folder | Not Started |
| Done command | Move task to Completed folder | Not Started |

### Verification

```bash
aio add "Test task" -d tomorrow -P P1
# Creates: Tasks/Inbox/2024-01-15-test-task.md

aio list inbox
# Lists tasks in Tasks/Inbox/

aio done "test-task"
# Moves to Tasks/Completed/2024/01/
```

---

## Phase 2: Obsidian Plugin Core

**Objective:** Build Obsidian plugin with task views and commands.

### Deliverables

| Item | Description | Priority |
|------|-------------|----------|
| Plugin scaffold | manifest.json, main.ts, esbuild | P0 |
| Settings tab | Configure folder paths | P0 |
| Task list view | Custom pane showing tasks | P0 |
| Quick add modal | Command palette task entry | P0 |
| Task edit modal | Edit frontmatter fields | P0 |
| Status commands | Complete, start, defer, wait | P0 |
| Right-click menu | Context actions on tasks | P1 |
| Inbox view | Process items one-by-one | P1 |
| Waiting-for view | Grouped by person | P1 |

### Verification

- Open Obsidian with plugin enabled
- Cmd+P → "AIo: Add task" → modal opens
- Create task → file appears in Tasks/Inbox/
- Open task list view → task visible
- Right-click → Complete → file moves to Completed/

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
4. [ ] Test add/list/done with real vault
5. [ ] Begin Obsidian plugin scaffold
