# Project Plan: AIorgianization

## Overview

This document outlines the implementation phases for AIorgianization - an Obsidian-native task and context management system for engineering managers.

## Architecture Summary

- **Storage:** Markdown files in Obsidian vault (no database)
- **UI:** Obsidian plugin for viewing/editing tasks
- **CLI:** Python (Click) for human use plus a JSON interface for chat agents
- **Chat integration:** Reusable skill for ChatGPT Desktop, Codex, and Remote Connections
- **Testing:** pytest (unit, integration, e2e)

---

## Phase Summary

| Phase | Name | Status | Focus |
|-------|------|--------|-------|
| 1 | Foundation | Done | Vault structure, CLI basics |
| 2 | Obsidian Plugin Core | Done | Task views, commands |
| 3 | AI Integration | Done | Agent CLI and reusable chat skill |
| 4 | Polish | Done | Weekly review, refinements |
| 5 | Chat-first and Remote | Done | Agent CLI, reusable skill, remote-host workflow |

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
| Contextual task capture | Store Markdown resume context through CLI and agent CLI | Done |
| List command | Query tasks by status/folder | Done |
| Done command | Move task to Completed folder | Done |
| Dashboard command | Generate/append dashboard to daily note | Done |
| Archive commands | Archive tasks, projects, areas, people | Done |
| Date-based archive | `aio archive tasks --before <date>` | Done |
| Unit tests | Test services, utils, models | Done |
| Integration tests | Test CLI commands | Done |
| E2E tests | Test full workflows with fixtures | Done |
| Comprehensive test runner | Language-agnostic test orchestrator (Python + TypeScript) | Done |
| UAT markers | pytest markers for UAT tracking with report generation | Done |
| TypeScript tests | Vitest tests for Obsidian plugin with mocked API | Done |

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
| Right-click menu | Context actions on tasks | Done |
| Inbox view | Process items one-by-one | Done |
| Waiting-for view | Grouped by person | Done |
| Dependency management | Link tasks as blockedBy/blocks | Done |
| Dependency visualization | Show blocked tasks and blockers in views | Done |
| Blocked view | Tasks waiting on dependencies | Done |
| Location linking | Connect task to file path, line number, or URL | Done |
| Location navigation | Click to open file/URL from task view | Done |
| Subtask progress | Track and display subtask completion (e.g., "3/5") | Done |

### Verification

- Open Obsidian with plugin enabled
- Cmd+P → "AIo: Add task" → modal opens
- Create task → file appears in AIO/Tasks/Inbox/
- Open task list view → task visible
- Right-click → Complete → file moves to Completed/
- Link task as blocked by another → shows in Blocked view
- Complete blocking task → blocked task no longer shows blockers

---

## Phase 3: AI Integration

**Objective:** JSON agent CLI and reusable skill expose vault operations to chat agents.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Agent CLI | Stable JSON commands for task lifecycle and context work | Done |
| Reusable skill | `skills/manage-aio/` maps natural-language requests to agent commands | Done |
| Integration tests | Test command envelopes and error handling | Done |

### Verification

- Install `skills/manage-aio/` on the host
- "Add a task to review the roadmap by Friday"
- Chat invokes `aio agent add`
- Task file created in vault

---

## Phase 4: Polish

**Objective:** Weekly review workflow and refinements.

### Deliverables

| Item | Description | Priority |
|------|-------------|----------|
| Weekly review wizard | Multi-step review view in plugin | Done |
| Review tracking | Record review completion | Done |
| Project views | Dataview integration and `aio project list/show` views | Done |
| Project and area creation | Direct `aio project create` and `aio area create` commands | Done |
| Linked task references | Project and area templates query tasks that backlink to the note | Done |
| Delegated summary | Days-since-delegated display | Done |
| CLI improvements | Better output formatting for project summaries | Done |
| Documentation | User manual, PRD, project plan, UAT, client instructions | Done |

---

## Phase 5: Chat-first and Remote

**Objective:** Make chat the primary AIO interface on desktop and remote devices through the host CLI.

### Deliverables

| Item | Description | Status |
|------|-------------|--------|
| Agent CLI group | Add non-interactive `aio agent` commands with stable JSON envelopes | Done |
| Task lifecycle parity | Support list, add, complete, start, defer, wait, and dashboard actions | Done |
| Context workflow parity | Support search, resume, context links, work logs, knowledge promotion, and index health | Done |
| Structured failures | Return JSON errors on stderr with nonzero exit codes | Done |
| Reusable skill | Add `skills/manage-aio/` for natural-language task management | Done |
| ChatGPT Desktop setup | Document local CLI and skill installation | Done |
| Remote Connections setup | Document host requirements and remote-device behavior | Done |
| Acceptance coverage | Add integration and UAT coverage for the agent workflow | Done |

---

## Work Breakdown by Component

### Python Package (aio/)

| Phase | Work |
|-------|------|
| 1 | Project setup, VaultService, TaskService, CLI (add/list/done), tests |
| 3 | Agent CLI and reusable chat skill |
| 4 | Polish, better output |
| 5 | JSON agent commands and chat-workflow integration tests |

### Obsidian Plugin (obsidian-aio/)

| Phase | Work |
|-------|------|
| 2 | All plugin features (TypeScript) |
| 4 | Weekly review, polish |

### Agent Integrations

| Phase | Work |
|-------|------|
| 3 | JSON agent commands and reusable client instructions |
| 5 | `manage-aio` skill, ChatGPT Desktop setup, and Remote Connections workflow |

---

## Migration Notes

The Phase 1 prototype used TypeScript + SQLite + Drizzle. This has been replaced:

- **Before:** TypeScript CLI, tasks in `~/.aio/aio.db` (SQLite)
- **After:** Python CLI, tasks in `Vault/AIO/Tasks/*.md` (Markdown files)

The Python CLI rewrite is complete. All core functionality has been migrated.

---

## Next Actions

**Phase 4 (Polish) - Done:**

1. [x] Implement weekly review wizard in Obsidian plugin
2. [x] Add review tracking (record completion timestamps)
3. [x] Implement Waiting-for view grouped by person
5. [x] Implement dependency visualization in task views
6. [x] Add Blocked view for tasks waiting on dependencies
7. [x] Implement location navigation (click to open file/URL)
8. [x] Add subtask progress display
9. [x] Add project list/show views
10. [x] Add direct project and area creation commands
11. [x] Add `delegate` as CLI alias for `wait` with required person argument

**Phase 5 (Chat-first and Remote) - Done:**

1. [x] Add stable JSON commands under `aio agent`
2. [x] Cover task lifecycle and context-resume workflows
3. [x] Create and validate the `manage-aio` skill
4. [x] Document ChatGPT Desktop local setup
5. [x] Document Remote Connections behavior and prerequisites
7. [x] Add integration and UAT coverage
