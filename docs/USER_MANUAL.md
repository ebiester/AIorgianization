# AIorgianization User Manual

A personal task and deadline management system for engineering managers, built on Obsidian.

---

## Quick Start

### 1. Initialize Your Vault

Point the CLI at your existing Obsidian vault to create the AIO directory structure:

```bash
aio init /path/to/your/obsidian/vault
```

This creates the following structure inside your vault:

```
Vault/
├── AIO/
│   ├── Dashboard/
│   ├── Tasks/
│   │   ├── Inbox/
│   │   ├── Next/
│   │   ├── Waiting/
│   │   ├── Scheduled/
│   │   ├── Someday/
│   │   └── Completed/
│   ├── Projects/
│   ├── People/
│   ├── Areas/
│   └── Archive/                  # Parallel structure for archived items
│       ├── Tasks/
│       │   ├── Inbox/
│       │   ├── Next/
│       │   ├── Waiting/
│       │   ├── Scheduled/
│       │   └── Someday/
│       ├── Projects/
│       ├── People/
│       └── Areas/
└── .aio/
    └── config.yaml
```

### 2. Install Dependencies

- **Obsidian plugins:** Dataview (required), Templater (optional, for dashboard generation)
- **CLI:** `npm install -g @aio/cli` (when available)

### 3. Verify Configuration

```bash
aio config show
# Shows: vault.path = /path/to/your/obsidian/vault
```

### 4. Start Your Day

The dashboard integrates with Obsidian's daily notes. When you open today's daily note, the AIO dashboard sections are automatically included via Dataview queries.

**Option A: Use Templater** (recommended)
Configure your daily note template to include the AIO dashboard template.

**Option B: Manual generation**
```bash
aio dashboard
```
This appends dashboard content to your daily note if it exists, or creates `AIO/Dashboard/2026-01-15.md` as a standalone file.

Your daily note becomes your command center.

---

## Core Concepts

### Task Statuses (GTD-based)

| Status | Meaning | Folder |
|--------|---------|--------|
| **Inbox** | Captured but not processed | `Tasks/Inbox/` |
| **Next** | Ready to work on | `Tasks/Next/` |
| **Waiting** | Delegated, waiting for someone | `Tasks/Waiting/` |
| **Scheduled** | Has a specific date to do | `Tasks/Scheduled/` |
| **Someday** | Maybe later, not now | `Tasks/Someday/` |
| **Completed** | Done | `Tasks/Completed/YYYY/MM/` |

### Task Types

| Type | Use For |
|------|---------|
| **Personal** | Your own work |
| **Delegated** | Work you've given to someone else |
| **Team** | Team-level milestones you're tracking |

---

## Daily Workflow

### Morning (5 minutes)

1. **Generate your dashboard:**
   ```bash
   aio dashboard
   ```

2. **Open the dashboard in Obsidian** and review:
   - **Overdue:** Handle these first
   - **Due Today:** Your focus for the day
   - **Waiting For:** Anyone you need to ping?
   - **Team Load:** Anyone drowning?

3. **Process inbox** if items accumulated overnight

### During the Day

**Capture immediately, process later:**
```bash
aio add "Review Sarah's PR"
aio add "Discuss roadmap in 1:1" -d friday
aio add "Fix auth bug" -d today
```

**Update task status:**
```bash
aio start "auth bug"      # Move to in-progress
aio done "auth bug"       # Complete it
aio wait "roadmap" Sarah  # Delegated to Sarah
aio defer "refactor"      # Move to someday
```

### End of Day (2 minutes)

1. Glance at tomorrow's due items
2. Capture any loose thoughts to inbox
3. Done

### Weekly Review (30 minutes)

1. **Inbox zero:** Process every item in `Tasks/Inbox/`
2. **Review projects:** Does each active project have a next action?
3. **Review waiting-for:** Follow up on stale items (>7 days)
4. **Review someday:** Anything ready to activate?

---

## The Morning Dashboard

Your dashboard is integrated with your daily note and shows:

### Overdue
Tasks past their due date. These need attention or rescheduling.

### Due Today
Your focus for the day.

### Due This Week
What's coming. Plan ahead.

### Blocked
Tasks waiting on dependencies. Shows what's blocking them.

### Waiting For
Tasks you've delegated, grouped by person. Shows:
- How many items per person
- Oldest item (flag if >7 days)

**Action:** If someone has stale items, follow up in your next 1:1.

### Team Load
How many active tasks each person has. Flags people who may be overloaded (>5 active items).

**Action:** Rebalance work if someone is drowning.

### Quick Links
Jump to common views.

---

## CLI Reference

### Adding Tasks

```bash
# Basic
aio add "Task title"

# With due date (natural language)
aio add "Review PR" -d tomorrow
aio add "Submit report" -d "next friday"
aio add "Quarterly planning" -d 2026-02-01

# With project
aio add "Design API" -p "Q4 Migration"

# Combined
aio add "Review spec" -d friday -p "Q4 Migration"
```

### Listing Tasks

```bash
aio list              # All active tasks
aio list inbox        # Unprocessed items
aio list next         # Ready to work on
aio list waiting      # Delegated items
aio list someday      # Deferred items
aio list today        # Due today + overdue
aio list overdue      # Past due date
```

### Changing Status

```bash
aio activate <task>   # Inbox → Next
aio start <task>      # → In Progress
aio done <task>       # → Completed
aio defer <task>      # → Someday
aio wait <task> Sarah # → Waiting (for Sarah)
```

### Task Identifiers

Each task gets a short 4-character ID (e.g., `AB2C`). IDs use alphanumeric characters excluding ambiguous ones (0, 1, I, O) and are case-insensitive.

You can reference tasks by:
- **Task ID:** `aio done AB2C`
- **Title substring:** `aio done "auth bug"`

### Archiving

Archive items to move them out of active views while preserving their history:

```bash
# Archive a specific item
aio archive task <task>           # Archive a single task
aio archive project <project>     # Archive a project and its tasks
aio archive area <area>           # Archive an area
aio archive person <person>       # Archive a person

# Archive tasks by date (archive everything completed before a date)
aio archive tasks --before 2026-01-01
aio archive tasks --before "6 months ago"

# Preview what would be archived (dry run)
aio archive tasks --before 2026-01-01 --dry-run
```

Archived items are moved to the parallel `Archive/` folder structure:
- `AIO/Tasks/Next/my-task.md` → `AIO/Archive/Tasks/Next/my-task.md`
- `AIO/Projects/Q4-Migration.md` → `AIO/Archive/Projects/Q4-Migration.md`

### Other Commands

```bash
aio init <vault-path>      # Initialize AIO structure in an Obsidian vault
aio dashboard              # Generate today's dashboard
aio delegated              # Show all delegated tasks by person
aio delegated Sarah        # Show tasks delegated to Sarah
aio project list           # List all projects
```

---

## Task Files

Tasks are markdown files with YAML frontmatter. You can edit them directly in Obsidian.

### Example Task

`AIO/Tasks/Next/2026-01-15-review-sarahs-pr.md`:

```markdown
---
id: X7KP
type: task
status: next
due: 2026-01-16
project: "[[Projects/Q4-Migration]]"
location:
  url: "https://github.com/company/repo/pull/456"  # Link to the PR
blockedBy: []           # Tasks that must complete first
blocks: []              # Tasks waiting on this one
created: 2026-01-15T09:00:00
updated: 2026-01-15T09:00:00
---

# Review Sarah's PR

## Subtasks
- [ ] Read the description
- [ ] Review code changes
- [ ] Run tests locally
- [ ] Leave comments

## Notes
- Focus on error handling
- Check test coverage
```

### Waiting-For Task

When you delegate, add `waitingOn`:

```markdown
---
id: M3TN
type: task
status: waiting
due: 2026-01-20
waitingOn: "[[People/Sarah]]"
created: 2026-01-15T10:00:00
updated: 2026-01-15T10:00:00
---

# Design API schema

Delegated to Sarah. Need draft by Friday.
```

---

## Project Files

Projects are hubs linking everything related to a body of work.

### Example Project

`Projects/Q4-Migration.md`:

```markdown
---
type: project
status: active
team: "[[People/Team-Platform]]"
targetDate: 2026-03-31
jiraEpic: PLAT-500
---

# Q4 Platform Migration

## Outcome
Migrate payment processing to new platform with zero downtime.

## Key Links

| Resource | Link |
|----------|------|
| Jira Epic | [PLAT-500](https://company.atlassian.net/browse/PLAT-500) |
| Jira Board | [Platform Board](https://company.atlassian.net/jira/software/projects/PLAT/boards/42) |
| Tech Spec | [[Specs/Platform-Migration-Spec]] |
| Slack | [#platform-migration](https://slack.com/...) |

## Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Design complete | 2026-01-31 | Done |
| API migration | 2026-02-15 | In Progress |
| Data migration | 2026-02-28 | Not Started |
| Cutover | 2026-03-15 | Not Started |

## Open Tasks

```dataview
TABLE status, priority, due, assignedTo.file.name AS "Owner"
FROM "Tasks"
WHERE contains(project, this.file.link) AND status != "completed"
SORT priority ASC, due ASC
```

## Risks

- [ ] Dependency on Auth team for token migration
- [ ] Load testing environment not ready
```

---

## People Files

Track your direct reports and delegates.

### Example Person

`People/Sarah.md`:

```markdown
---
type: person
team: Platform
role: Senior Engineer
email: sarah@company.com
---

# Sarah Chen

## Current Focus
- Leading API redesign
- Mentoring junior engineers

## Delegated Tasks

```dataview
TABLE status, due, file.name AS "Task"
FROM "Tasks"
WHERE waitingOn = this.file.link AND status != "completed"
SORT due ASC
```

## 1:1 Notes
- [[Meetings/2026-01-15-sarah-1on1]]
```

---

## Jira Integration

Sync your assigned Jira issues to the vault.

### Setup

```bash
aio config set jira.baseUrl https://company.atlassian.net
aio config set jira.email your@email.com
aio config set jira.projects PLAT,ALPHA
```

Set your API token:
```bash
export JIRA_API_TOKEN=your-token-here
```

### Syncing

```bash
aio sync jira
```

This:
1. Fetches issues assigned to you
2. Creates/updates task files with `jiraKey` in frontmatter
3. Maps Jira statuses to task folders

### Status Mapping

| Jira Status | Task Folder |
|-------------|-------------|
| To Do | `Tasks/Inbox/` or `Tasks/Next/` |
| In Progress | `Tasks/Next/` |
| In Review | `Tasks/Waiting/` |
| Blocked | `Tasks/Waiting/` |
| Done | `Tasks/Completed/` |

**Note:** Jira is the source of truth. If you change status locally, the next sync will overwrite it.

---

## Tips

### Capture Fast, Process Later

Don't stop to organize when capturing. Just:
```bash
aio add "the thing"
```
Process your inbox during your morning routine or weekly review.

### Use Contexts Sparingly

Contexts like `@1on1` or `@deep-work` are useful for filtering, but don't over-categorize. Start with none and add only if you find yourself needing to filter.

### Keep Projects Linked

Always link tasks to projects:
```bash
aio add "Write tests" -p "Q4 Migration"
```
This makes the project health queries work.

### Review Waiting-For Weekly

Stale delegated items erode trust. Check your "Waiting For" section weekly and follow up.

### Don't Fight the System

If a task doesn't fit neatly, just put it in inbox and process later. The system works when you use it consistently, not perfectly.

---

## Keyboard Shortcuts (Obsidian)

Set these up in Obsidian's hotkey settings:

| Action | Suggested Hotkey |
|--------|------------------|
| Open today's dashboard | `Cmd+Shift+D` |
| Quick add task | `Cmd+Shift+A` |
| Open inbox folder | `Cmd+Shift+I` |

---

## Troubleshooting

### "Vault not found"
```bash
aio config set vault.path /correct/path/to/vault
```

### Dataview queries not working
1. Ensure Dataview plugin is installed and enabled
2. Check that frontmatter fields match exactly (case-sensitive)
3. Reload Obsidian

### Tasks not appearing in project view
Ensure the task's `project` field uses wikilink syntax:
```yaml
project: "[[Projects/Q4-Migration]]"
```

### Jira sync creates duplicates
Check that existing task files have the correct `jiraKey` in frontmatter.

---

## File Locations Summary

| Content | Location |
|---------|----------|
| Today's dashboard | `AIO/Dashboard/2026-01-15.md` |
| Inbox tasks | `AIO/Tasks/Inbox/*.md` |
| Active tasks | `AIO/Tasks/Next/*.md` |
| Delegated tasks | `AIO/Tasks/Waiting/*.md` |
| Deferred tasks | `AIO/Tasks/Someday/*.md` |
| Completed tasks | `AIO/Tasks/Completed/YYYY/MM/*.md` |
| Projects | `AIO/Projects/*.md` |
| People | `AIO/People/*.md` |
| Areas | `AIO/Areas/*.md` |
| Archived tasks | `AIO/Archive/Tasks/**/*.md` |
| Archived projects | `AIO/Archive/Projects/*.md` |
| Archived people | `AIO/Archive/People/*.md` |
| Archived areas | `AIO/Archive/Areas/*.md` |
| Config | `.aio/config.yaml` |
