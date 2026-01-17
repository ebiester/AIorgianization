# Architecture Document: AIorgianization

## System Overview

AIorgianization is an Obsidian-native task and context management system for engineering managers. Tasks are stored as markdown files in the vault, managed via an Obsidian plugin for rich UI, with a CLI for quick capture and Claude integration for AI assistance.

```
┌─────────────────────────────────────────────────────────────────┐
│                       Obsidian Vault                             │
│  (Markdown files: tasks, projects, context packs)               │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │Obsidian │          │   CLI   │          │  Claude │
    │ Plugin  │          │  (aio)  │          │   MCP   │
    │  (UI)   │          │(capture)│          │  (AI)   │
    └─────────┘          └────┬────┘          └─────────┘
                              │
                         ┌────┴────┐
                         │  Jira   │
                         │  Sync   │
                         └─────────┘
```

**Key principle:** The Obsidian vault is the single source of truth. All tools read and write markdown files. No separate database.

---

## Vault Structure

The CLI initializes this structure via `aio init <vault-path>`:

```
Vault/
├── .aio/                          # AIorgianization config & cache
│   ├── config.yaml                # Settings (Jira, sync, etc.)
│   └── jira-cache.json            # Cached Jira state for sync
│
├── AIO/                           # All AIorgianization content
│   ├── Dashboard/                 # Daily dashboards (generated)
│   │   ├── 2024-01-15.md          # Today's dashboard
│   │   └── 2024-01-14.md
│   │
│   ├── Tasks/                     # All tasks organized by status
│   │   ├── Inbox/                 # Unclarified items (GTD)
│   │   │   └── 2024-01-15-review-pr.md
│   │   ├── Next/                  # Next actions
│   │   │   └── 2024-01-14-design-api.md
│   │   ├── Waiting/               # Waiting for others
│   │   ├── Scheduled/             # Calendar-bound
│   │   ├── Someday/               # Someday/maybe
│   │   └── Completed/             # Done
│   │       └── 2024/
│   │           └── 01/
│   │
│   ├── Projects/                  # Active projects (PARA)
│   │   ├── Q4-Migration.md
│   │   └── Hiring-Senior-Eng.md
│   │
│   ├── Areas/                     # Ongoing responsibilities
│   │   ├── Team-Alpha.md
│   │   └── 1on1s.md
│   │
│   ├── People/                    # Team members for delegation
│   │   ├── Sarah.md
│   │   └── John.md
│   │
│   ├── Context-Packs/             # Reusable context for AI
│   │   ├── Domains/
│   │   │   ├── Payments.md
│   │   │   └── Identity.md
│   │   ├── Systems/
│   │   │   ├── Payment-API.md
│   │   │   └── Auth-Service.md
│   │   └── Operating/
│   │       ├── Definition-of-Done.md
│   │       └── Ticket-Standards.md
│   │
│   ├── ADRs/                      # Architecture Decision Records
│   │   └── 2024-01-10-caching-strategy.md
│   │
│   └── Archive/                   # Archived items (parallel structure)
│       ├── Tasks/
│       │   ├── Inbox/
│       │   ├── Next/
│       │   ├── Waiting/
│       │   ├── Scheduled/
│       │   └── Someday/
│       ├── Projects/
│       ├── Areas/
│       └── People/
```

---

## Task File Format

Tasks are markdown files with YAML frontmatter for structured data.

```markdown
---
id: AB2C              # 4-char alphanumeric ID
type: task
status: next          # inbox | next | waiting | scheduled | someday | completed
due: 2024-01-20
project: "[[Projects/Q4-Migration]]"
location:             # Where in the project this task applies
  file: "src/api/payments.ts"    # File path (relative to project root)
  line: 142                       # Optional: specific line number
  url: "https://..."              # Optional: external URL (PR, doc, etc.)
assignedTo: "[[People/Sarah]]"
waitingOn: null       # Person we're waiting on (if status=waiting)
blockedBy: []         # Wikilinks to tasks that must complete first
blocks: []            # Wikilinks to tasks waiting on this one
tags:
  - backend
  - api
timeEstimate: 2h
jiraKey: PLAT-123     # Linked Jira issue
created: 2024-01-15T10:00:00
updated: 2024-01-15T14:30:00
completed: null
---

# Review Q4 roadmap with stakeholders

## Subtasks
- [ ] Draft agenda
- [ ] Schedule meeting
- [ ] Send pre-read

## Notes
- Need to align on timeline
- Check with Sarah about API dependencies

## Related
- [[ADRs/2024-01-10-caching-strategy]]
- [[Context-Packs/Systems/Payment-API]]
```

### Status Transitions

```
Inbox → Next | Waiting | Scheduled | Someday
Next → In Progress → Completed
Waiting → Next (when response received)
Someday → Next (when reactivated)
Completed → (archived to Completed/YYYY/MM/)
```

### Task Hierarchy

Tasks support two levels of organization:

1. **Project**: High-level grouping (e.g., "Q4 Migration") - stored as separate files
2. **Subtasks**: Breakdown of a task - stored within the parent task file as a checklist

```
Project: Q4 Migration (Projects/Q4-Migration.md)
├── Task: API Migration (Tasks/Next/2024-01-15-api-migration.md)
│   └── Subtasks: (inside the task file)
│       - [ ] Design new endpoints
│       - [ ] Implement endpoints
│       - [ ] Write tests
└── Task: Data Migration (Tasks/Next/2024-01-16-data-migration.md)
    └── Subtasks: (inside the task file)
        - [ ] Create migration scripts
        - [ ] Run migration
```

**Task file with subtasks:**

```markdown
---
type: task
status: next
project: "[[Projects/Q4-Migration]]"
due: 2024-01-20
---

# API Migration

## Subtasks
- [ ] Design new endpoints
- [ ] Implement endpoints
- [ ] Write tests

## Notes
Focus on backwards compatibility.
```

The plugin tracks subtask completion progress and can display it in task views.

### Task IDs

Each task is assigned a 4-character alphanumeric ID stored in frontmatter:

```yaml
id: AB2C
```

**ID format:**
- 4 characters from: `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` (32 chars)
- Excludes ambiguous characters: `0`, `1`, `I`, `O`
- Case-insensitive (stored uppercase, matched case-insensitively)
- ~1 million combinations (32^4), sufficient for <10,000 active tasks

**Collision handling:** On creation, generate random ID and retry if collision detected.

### File Naming Convention

```
YYYY-MM-DD-short-title.md

Examples:
2024-01-15-review-q4-roadmap.md
2024-01-16-fix-payment-bug.md
```

---

## Project File Format

Projects are markdown files that serve as the central hub for a body of work, linking to external tools (Jira, Slack), internal docs, timeline milestones, and live task queries.

```markdown
---
type: project
status: active        # active | on-hold | completed | archived
category: project     # project | area (PARA)
team: "[[People/Team-Platform]]"
targetDate: 2024-03-31
jiraEpic: PLAT-500
created: 2024-01-01
---

# Q4 Platform Migration

## Outcome
Migrate payment processing to new platform with zero downtime.

---

## Key Links

| Resource | Link |
|----------|------|
| Jira Epic | [PLAT-500](https://company.atlassian.net/browse/PLAT-500) |
| Jira Board | [Platform Board](https://company.atlassian.net/jira/software/projects/PLAT/boards/42) |
| Backlog | [Filtered Backlog](https://company.atlassian.net/jira/software/projects/PLAT/boards/42/backlog?epics=PLAT-500) |
| Tech Spec | [[Specs/Platform-Migration-Spec]] |
| PRD | [[PRDs/Platform-Migration-PRD]] |
| Slack Channel | [#platform-migration](https://company.slack.com/archives/C123ABC) |
| Runbook | [[Runbooks/Migration-Runbook]] |

---

## Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Design complete | 2024-01-31 | Done |
| API migration | 2024-02-15 | In Progress |
| Data migration | 2024-02-28 | Not Started |
| Cutover | 2024-03-15 | Not Started |
| Hypercare complete | 2024-03-31 | Not Started |

---

## Project Health

### Open Tasks
```dataview
TABLE status, priority, due, assignedTo.file.name AS "Owner"
FROM "Tasks"
WHERE contains(project, this.file.link) AND status != "completed"
SORT priority ASC, due ASC
```

### Blocked / Waiting
```dataview
LIST
FROM "Tasks"
WHERE contains(project, this.file.link) AND status = "waiting"
```

### Completed This Week
```dataview
LIST
FROM "Tasks"
WHERE contains(project, this.file.link) AND status = "completed" AND completed >= date(today) - dur(7d)
```

---

## Team

| Person | Role |
|--------|------|
| [[People/Sarah]] | Tech Lead |
| [[People/John]] | Backend |
| [[People/Maya]] | Backend |

---

## Notes & Decisions

- [[ADRs/2024-01-10-caching-strategy]]
- [[Meeting-Notes/2024-01-12-kickoff]]

---

## Risks & Blockers

- [ ] Dependency on Auth team for token migration
- [ ] Load testing environment not ready
```

---

## Person File Format

```markdown
---
type: person
team: Platform
email: sarah@company.com
jiraAccountId: 5f4d3c2b1a
role: Senior Engineer
---

# Sarah Chen

## Current Focus
- Leading API redesign
- Mentoring junior engineers

## 1:1 Notes
- [[Meetings/2024-01-15-sarah-1on1]]

## Tasks Delegated
```dataview
TABLE due AS "Due", status AS "Status"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/Sarah Chen")) AND status != "completed"
SORT due ASC
```

## Previously Completed Tasks
```dataview
TABLE due AS "Due", completed AS "Completed"
FROM "AIO/Tasks"
WHERE contains(waitingOn, link("AIO/People/Sarah Chen")) AND status = "completed"
SORT completed DESC
```
```

---

## Morning Dashboard File Format

The dashboard integrates with Obsidian's daily notes. It can be:
1. **Embedded in daily notes** via Templater template (recommended)
2. **Generated as standalone** file in `AIO/Dashboard/YYYY-MM-DD.md` via CLI

The dashboard surfaces what needs attention today.

```markdown
---
type: dashboard
date: 2024-01-15
generated: 2024-01-15T07:00:00
---

# Wednesday, January 15

## Overdue
```dataview
TABLE due, assignedTo.file.name AS "Owner"
FROM "AIO/Tasks"
WHERE due < date(today) AND status != "completed"
SORT due ASC
```

## Due Today
```dataview
TABLE project.file.name AS "Project"
FROM "AIO/Tasks"
WHERE due = date(today) AND status != "completed"
SORT file.name ASC
```

## Due This Week
```dataview
TABLE due, project.file.name AS "Project"
FROM "AIO/Tasks"
WHERE due > date(today) AND due <= date(today) + dur(7d) AND status != "completed"
SORT due ASC
```

## Blocked
```dataview
TABLE blockedBy AS "Blocked By"
FROM "AIO/Tasks"
WHERE length(blockedBy) > 0 AND status != "completed"
```

---

## Waiting For

### By Person
```dataview
TABLE WITHOUT ID
  rows.file.link AS "Tasks",
  length(rows) AS "Count",
  min(rows.updated) AS "Oldest"
FROM "AIO/Tasks"
WHERE status = "waiting"
FLATTEN waitingOn AS person
GROUP BY person
SORT length(rows) DESC
```

### Stale (>7 days)
```dataview
LIST
FROM "AIO/Tasks"
WHERE status = "waiting" AND (date(today) - updated) > dur(7d)
SORT updated ASC
```

---

## Team Load

```dataview
TABLE WITHOUT ID
  person AS "Person",
  length(rows) AS "Active Tasks"
FROM "AIO/Tasks"
WHERE status != "completed" AND assignedTo
FLATTEN assignedTo AS person
GROUP BY person
SORT length(rows) DESC
```

> **Flag if anyone has >5 active items**

---

## Quick Links

| View | Link |
|------|------|
| Inbox | [[AIO/Tasks/Inbox/]] |
| My Next Actions | [[AIO/Tasks/Next/]] |
| All Projects | [[AIO/Projects/]] |
| 1:1 Prep | [[AIO/Areas/1on1s]] |
```

### Dashboard Generation

The morning dashboard can be generated via:

1. **Templater plugin:** Configure as daily note template with `tp.date.now()` for dynamic date
2. **CLI command:** `aio dashboard` generates today's file in the vault
3. **Manual:** Create from template when starting the day

The Dataview queries run live, so the dashboard always shows current state even if generated earlier.

---

## Obsidian Plugin Architecture

### Plugin Components

```
obsidian-aio/
├── src/
│   ├── main.ts                    # Plugin entry point
│   ├── settings.ts                # Settings tab
│   ├── views/
│   │   ├── TaskListView.ts        # Main task list pane
│   │   ├── InboxView.ts           # Inbox processing view
│   │   ├── KanbanView.ts          # Kanban board (optional)
│   │   ├── ReviewView.ts          # Weekly review wizard
│   │   └── DelegatedView.ts       # Waiting-for dashboard
│   ├── modals/
│   │   ├── QuickAddModal.ts       # Fast task entry
│   │   ├── TaskEditModal.ts       # Edit task details
│   │   └── ReviewModal.ts         # Review step modal
│   ├── commands/
│   │   ├── addTask.ts             # Command: Add task
│   │   ├── completeTask.ts        # Command: Complete task
│   │   └── startReview.ts         # Command: Start weekly review
│   ├── services/
│   │   ├── TaskService.ts         # CRUD operations on task files
│   │   ├── ProjectService.ts      # Project file operations
│   │   ├── JiraSync.ts            # Jira synchronization
│   │   └── FileUtils.ts           # Markdown parsing/generation
│   └── types/
│       └── index.ts               # TypeScript interfaces
├── styles.css
├── manifest.json
├── package.json
└── esbuild.config.mjs
```

### Key Plugin Features

| Feature | Implementation |
|---------|---------------|
| Task list view | Custom `ItemView` pane |
| Quick add | `Modal` with parser |
| Inline editing | `MarkdownPostProcessor` or modal |
| Status change | Right-click menu + commands |
| Filtering | Dataview integration or custom query |
| Weekly review | Multi-step modal wizard |
| Jira sync | Background job + status bar |

### Commands (Command Palette)

```
AIo: Add task
AIo: Add task to inbox
AIo: Quick capture (minimal modal)
AIo: Complete task
AIo: Start task
AIo: Defer task
AIo: Move to waiting
AIo: Start weekly review
AIo: Sync with Jira
AIo: Open task list
AIo: Open inbox
AIo: Show delegated tasks
```

### Settings

```yaml
# Stored in .obsidian/plugins/aio/data.json
taskFolder: "Tasks"
projectFolder: "Projects"
peopleFolder: "People"
contextPackFolder: "Context-Packs"
adrFolder: "ADRs"
completedSubfolders: true    # Organize by YYYY/MM
defaultPriority: "P2"
defaultContext: "@work"
jira:
  enabled: true
  baseUrl: "https://company.atlassian.net"
  email: "user@company.com"
  # Token stored in env or Obsidian secrets
  projectKeys: ["PLAT", "ALPHA"]
  syncInterval: 15  # minutes
```

---

## CLI Architecture

The CLI reads and writes the same markdown files as the plugin.

```
aio/
├── __init__.py
├── cli/                           # CLI commands (Click)
│   ├── __init__.py
│   ├── main.py                    # Entry point, command group
│   ├── add.py                     # Create task file
│   ├── list.py                    # Query task files
│   ├── done.py                    # Move to completed
│   ├── init.py                    # Initialize vault
│   ├── archive.py                 # Archive tasks/projects
│   ├── dashboard.py               # Generate dashboard
│   ├── status.py                  # Start, defer, wait commands
│   ├── sync.py                    # Jira sync
│   └── config.py                  # Configuration management
├── services/                      # Core business logic
│   ├── __init__.py
│   ├── vault.py                   # Find and read vault
│   ├── task.py                    # Parse/write task markdown
│   ├── jira.py                    # Jira sync service
│   ├── dashboard.py               # Dashboard generation
│   └── context_pack.py            # Context pack operations
├── models/                        # Pydantic data models
│   ├── __init__.py
│   ├── task.py                    # Task model
│   ├── project.py                 # Project model
│   ├── person.py                  # Person model
│   ├── jira.py                    # Jira models
│   └── context_pack.py            # Context pack model
├── utils/
│   ├── __init__.py
│   ├── frontmatter.py             # YAML frontmatter parsing
│   ├── dates.py                   # Natural language dates
│   └── ids.py                     # 4-char ID generation
├── mcp/                           # MCP server
│   ├── __init__.py
│   ├── server.py                  # MCP server implementation
│   └── tools.py                   # Tool handlers
└── exceptions.py                  # Custom exceptions
```

### CLI Commands

```bash
# Initialization
aio init <vault-path>      # Initialize AIO structure in an existing Obsidian vault

# Task management
aio add "Task title" [-d due] [-P priority] [-p project]
aio list [inbox|next|waiting|someday|today|all]
aio done <task-file-or-query>
aio start <task>
aio defer <task>
aio wait <task> [person]

# Project/people
aio project list
aio delegated [person]

# Dashboard
aio dashboard              # Generate today's morning dashboard
aio dashboard --date 2024-01-15  # Generate for specific date

# Archiving
aio archive task <task>              # Archive a single task
aio archive project <project>        # Archive a project and its linked tasks
aio archive area <area>              # Archive an area
aio archive person <person>          # Archive a person
aio archive tasks --before <date>    # Archive tasks completed before date
aio archive tasks --before "6 months ago"  # Natural language dates supported
aio archive tasks --before 2024-01-01 --dry-run  # Preview without archiving

# Sync
aio sync jira
aio sync status

# Config
aio config show
aio config set vault.path /path/to/vault
aio config set jira.baseUrl https://company.atlassian.net
```

### Vault Discovery

CLI finds the vault via (in order):
1. `--vault` flag
2. `AIO_VAULT_PATH` environment variable
3. `.aio/config.yaml` in current directory
4. Walk up to find `.obsidian` folder
5. `~/.aio/config.yaml` global config

---

## Jira Sync Architecture

### Sync Strategy

```
┌─────────────────┐                    ┌─────────────────┐
│  Obsidian Vault │                    │   Jira Cloud    │
│                 │                    │                 │
│  Tasks/*.md     │◄────── Sync ──────►│  Issues         │
│  - jiraKey      │                    │  - key          │
│  - status       │   Mapping:         │  - status       │
│  - assignedTo   │   To Do → inbox    │  - assignee     │
│                 │   In Prog → next   │                 │
└─────────────────┘   Done → completed └─────────────────┘
```

### Sync Rules

1. **Import:** Jira issues assigned to you → Task files created/updated
2. **Status sync:** Jira status changes → Task file moved to appropriate folder
3. **No export (MVP):** Local tasks don't push to Jira (avoids complexity)
4. **Conflict:** If both changed, Jira wins (it's the team system of record)

### Sync Flow

```
1. Query Jira: assignee = currentUser() AND status != Done
2. For each issue:
   a. Find task file by jiraKey frontmatter
   b. If not found → create new task file
   c. If found → update frontmatter (status, title, etc.)
   d. Move file to correct status folder if status changed
3. Cache sync timestamp in .aio/jira-cache.json
```

### Status Mapping

| Jira Status | Task Folder |
|-------------|-------------|
| To Do | Tasks/Inbox/ or Tasks/Next/ |
| In Progress | Tasks/Next/ |
| In Review | Tasks/Waiting/ |
| Blocked | Tasks/Waiting/ |
| Done | Tasks/Completed/ |

---

## Archive Architecture

The archive system provides a way to move inactive items out of active views while preserving history and maintaining organizational structure.

### Archive Structure

The `Archive/` folder mirrors the active folder structure:

```
AIO/
├── Tasks/                  # Active tasks
│   ├── Inbox/
│   ├── Next/
│   └── ...
├── Projects/               # Active projects
├── Areas/                  # Active areas
├── People/                 # Active people
│
└── Archive/                # Archived items (parallel structure)
    ├── Tasks/
    │   ├── Inbox/          # Archived inbox tasks
    │   ├── Next/           # Archived next actions
    │   ├── Waiting/
    │   ├── Scheduled/
    │   └── Someday/
    ├── Projects/           # Archived projects
    ├── Areas/              # Archived areas
    └── People/             # Archived people
```

### Archive Operations

| Operation | Behavior |
|-----------|----------|
| `archive task <task>` | Move task file to `Archive/Tasks/<original-status>/` |
| `archive project <project>` | Move project to `Archive/Projects/`, optionally archive linked tasks |
| `archive area <area>` | Move area to `Archive/Areas/` |
| `archive person <person>` | Move person to `Archive/People/` |
| `archive tasks --before <date>` | Bulk archive completed tasks older than date |

### Archive Metadata

When a file is archived, frontmatter is updated:

```yaml
---
archived: true
archivedAt: 2024-06-01T10:00:00
archivedFrom: "AIO/Tasks/Completed/2024/01/"
---
```

### Date-Based Archiving

The `archive tasks --before <date>` command supports:

- ISO dates: `2024-01-01`
- Natural language: `"6 months ago"`, `"last year"`, `"January 1"`
- Dry run mode: `--dry-run` to preview without making changes

This is useful for periodic cleanup (e.g., archive all completed tasks older than 6 months).

---

## Claude MCP Integration

MCP server exposes vault content to Claude for AI assistance. The MCP server runs locally and is invoked by Claude Code or other MCP-compatible clients - no Anthropic API key required in the tool itself.

### MCP Tools

```typescript
const tools = [
  {
    name: 'aio_add_task',
    description: 'Create a task file in the vault',
    inputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        due: { type: 'string' },
        priority: { enum: ['P1', 'P2', 'P3', 'P4'] },
        project: { type: 'string' },
        contexts: { type: 'array', items: { type: 'string' } }
      },
      required: ['title']
    }
  },
  {
    name: 'aio_list_tasks',
    description: 'Query tasks from the vault',
    inputSchema: { /* status, project, due filters */ }
  },
  {
    name: 'aio_complete_task',
    description: 'Mark a task as completed',
    inputSchema: { /* task identifier */ }
  },
  {
    name: 'aio_get_context',
    description: 'Retrieve context pack content for AI use',
    inputSchema: {
      properties: {
        packs: { type: 'array', items: { type: 'string' } }
      }
    }
  }
];
```

### MCP Resources

```typescript
const resources = [
  { uri: 'aio://tasks/inbox', name: 'Inbox Tasks' },
  { uri: 'aio://tasks/next', name: 'Next Actions' },
  { uri: 'aio://tasks/waiting', name: 'Waiting For' },
  { uri: 'aio://projects', name: 'Active Projects' },
  { uri: 'aio://context-packs', name: 'Context Packs Index' }
];
```

---

## Data Flow Examples

### Quick Add (CLI)

```
User: aio add "Review Sarah's PR" -d tomorrow -P P1

1. CLI parses command
2. VaultService locates vault
3. TaskFileService generates markdown:
   - Frontmatter with status=inbox, priority=P1, due=tomorrow
   - Title as H1
4. File written to Tasks/Inbox/2024-01-15-review-sarahs-pr.md
5. Obsidian auto-reloads (if open)
```

### Status Change (Plugin)

```
User: Right-click task → "Start working"

1. Plugin reads current file frontmatter
2. Updates status: inbox → next
3. Moves file: Tasks/Inbox/*.md → Tasks/Next/*.md
4. Updates frontmatter: updated timestamp
5. View refreshes
```

### Jira Sync

```
User: aio sync jira (or plugin sync button)

1. Fetch issues from Jira API
2. For each issue:
   - Search vault for file with jiraKey=PLAT-123
   - If found: update frontmatter, move if status changed
   - If not found: create new task file
3. Update .aio/jira-cache.json with sync timestamp
4. Report: "Synced 5 tasks (2 new, 3 updated)"
```

### AI Task Breakdown

```
User: (via Claude) "Break down the Q4 Migration project"

1. Claude calls aio_get_context with project + relevant packs
2. MCP reads:
   - Projects/Q4-Migration.md
   - Context-Packs/Domains/Payments.md
   - Context-Packs/Systems/Payment-API.md
3. Returns content to Claude
4. Claude analyzes and suggests subtasks
5. Claude calls aio_add_task for each confirmed subtask
```

---

## Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Task storage | Markdown + YAML frontmatter | Human-readable, git-friendly, Obsidian-native |
| Plugin | TypeScript + Obsidian API | Required for Obsidian plugins |
| CLI | Python + Click | Type-safe, excellent CLI framework |
| Jira client | jira (Python) | Well-maintained Python library |
| MCP server | mcp (Python SDK) | Official Python SDK |
| YAML parsing | python-frontmatter | Standard for frontmatter |
| Date parsing | dateparser | Natural language dates |
| Data validation | Pydantic | Type-safe models with serialization |
| Terminal output | Rich | Beautiful terminal formatting |

---

## Security Considerations

1. **Jira token:** Stored in environment variable or Obsidian encrypted settings, never in vault files
2. **Vault permissions:** CLI respects filesystem permissions
3. **MCP scope:** Read-only by default, write operations require explicit tool calls
4. **No cloud sync:** All data stays local (Obsidian Sync is user's choice)

---

## Migration from SQLite Prototype

The Phase 1 prototype used SQLite. Migration is complete:

- ~~Export tasks: `aio export --format markdown --output ./Tasks/`~~
- ~~Each task becomes a markdown file~~
- ~~Delete `~/.aio/aio.db`~~
- ~~Update CLI to use VaultService instead of Drizzle~~

**Status:** Migration complete. The Python CLI now uses markdown files in the vault as the source of truth.

---

## Future Considerations

1. **Dataview integration:** Use Dataview queries for dynamic task views
2. **Templater integration:** Task templates for common patterns
3. **Mobile:** Obsidian mobile app provides cross-device access
4. **Sharing:** Export context packs to Confluence when ready
5. **Bidirectional Jira sync:** Push local tasks to Jira (requires careful conflict handling)
