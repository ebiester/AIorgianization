# AIorgianization User Manual

A personal task and deadline management system for engineering managers, built on Obsidian.

---

## Table of Contents

1. [Installation](#installation)
2. [Setup](#setup)
3. [Core Concepts](#core-concepts)
4. [Daily Workflow](#daily-workflow)
5. [CLI Reference](#cli-reference)
6. [Integrations](#integrations)
7. [File Formats](#file-formats)
8. [Tips](#tips)
9. [Troubleshooting](#troubleshooting)
10. [Reference](#reference)

---

## Installation

### Prerequisites

- **Python 3.12+** with [uv](https://github.com/astral-sh/uv) package manager
- **Obsidian** with an existing vault
- **Dataview plugin** for Obsidian (required for dashboard queries)
- **Templater plugin** for Obsidian (optional, for dashboard generation)

### Install the CLI

```bash
# Clone the repository
git clone https://github.com/your-org/AIorgianization.git
cd AIorgianization

# Install dependencies (for development)
uv sync

# Verify installation
uv run aio --help
```

#### Global Installation (Recommended)

Install AIO as a system-wide command using uv's tool feature:

```bash
uv tool install --editable /path/to/AIorgianization
```

This installs `aio` globally while pointing to your local source code—changes are immediately available without reinstalling.

**To update after pulling new code:**
```bash
uv tool upgrade aio
```

**To reinstall after dependency changes in pyproject.toml:**
```bash
uv tool install --editable /path/to/AIorgianization --force
```

#### Configure Your Vault Path

Set your default vault path in your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export AIO_VAULT_PATH="/path/to/your/obsidian/vault"
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### Install the Obsidian Plugin

The plugin is installed automatically when you run `aio init`. To install manually:

1. Copy the `obsidian-aio/` folder contents to your vault's `.obsidian/plugins/aio/` directory
2. Restart Obsidian
3. Enable the "AIorgianization" plugin in Settings → Community plugins

### Install the MCP Server (Optional)

The MCP server allows AI assistants (Claude Code, Cursor, Claude Desktop) to interact with your vault.

#### For Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "aio": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/AIorgianization", "aio-mcp"],
      "env": {
        "AIO_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

#### For Cursor

Add to `~/.cursor/mcp.json` or `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "aio": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/AIorgianization", "aio-mcp"],
      "env": {
        "AIO_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

#### For Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "aio": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/AIorgianization", "aio-mcp"],
      "env": {
        "AIO_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

**Configuration notes:**
- Replace `/path/to/AIorgianization` with the actual path to this repository
- Replace `/path/to/your/obsidian/vault` with the path to your Obsidian vault
- Restart your MCP client after updating the configuration

---

## Setup

### Initialize Your Vault

Point the CLI at your existing Obsidian vault to create the AIO directory structure:

```bash
aio init /path/to/your/obsidian/vault
```

This creates:

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
│   └── Archive/
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

### Enable the Obsidian Plugin

The `aio init` command automatically installs the Obsidian plugin. To activate it:

1. Restart Obsidian (or reload plugins via Settings → Community plugins → "Reload plugins")
2. If prompted about Restricted Mode, click "Turn on community plugins"
3. The AIorgianization plugin should now be active

### Verify Configuration

```bash
aio config show
# Shows: vault.path = /path/to/your/obsidian/vault
```

### Configure Jira Integration (Optional)

```bash
aio config set jira.baseUrl https://company.atlassian.net
aio config set jira.email your@email.com
aio config set jira.projects PLAT,ALPHA
export JIRA_API_TOKEN=your-token-here
```

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

### Task Identifiers

Each task gets a short 4-character ID (e.g., `AB2C`). IDs use alphanumeric characters excluding ambiguous ones (0, 1, I, O) and are case-insensitive.

You can reference tasks by:
- **Task ID:** `aio done AB2C`
- **Title substring:** `aio done "auth bug"`

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
aio start "auth bug"      # Move to Next
aio done "auth bug"       # Complete it
aio wait "roadmap" Sarah  # Delegated to Sarah
aio defer "refactor"      # Move to Someday
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

# Delegate immediately (creates task in Waiting status)
aio add "Review API design" --assign Sarah
aio add "Update docs" -a Bob -d friday

# Combined
aio add "Review spec" -d friday -p "Q4 Migration"
aio add "Design schema" -p "Q4 Migration" --assign Sarah -d "next monday"
```

The `--assign` (or `-a`) flag creates the task and immediately delegates it to a person, moving it to Waiting status. This is equivalent to running `aio add` followed by `aio wait`.

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
aio start <task>      # → Next
aio done <task>       # → Completed
aio defer <task>      # → Someday
aio wait <task> Sarah # → Waiting (for Sarah)
```

### Archiving

Archive items to move them out of active views while preserving their history:

```bash
# Archive a specific item
aio archive task <task>           # Archive a single task
aio archive project <project>     # Archive a project and its tasks
aio archive area <area>           # Archive an area
aio archive person <person>       # Archive a person

# Archive tasks by date
aio archive tasks --before 2026-01-01
aio archive tasks --before "6 months ago"

# Preview what would be archived (dry run)
aio archive tasks --before 2026-01-01 --dry-run
```

Archived items are moved to the parallel `Archive/` folder structure.

### Other Commands

```bash
aio init <vault-path>      # Initialize AIO structure
aio dashboard              # Generate today's dashboard
aio delegated              # Show all delegated tasks by person
aio delegated Sarah        # Show tasks delegated to Sarah
aio project list           # List all projects
aio config show            # Show current configuration
aio config set <key> <val> # Set configuration value
```

---

## Integrations

### Jira Integration

Sync your assigned Jira issues to the vault.

#### Setup

```bash
aio config set jira.baseUrl https://company.atlassian.net
aio config set jira.email your@email.com
aio config set jira.projects PLAT,ALPHA
export JIRA_API_TOKEN=your-token-here
```

#### Syncing

```bash
aio sync jira
```

This:
1. Fetches issues assigned to you
2. Creates/updates task files with `jiraKey` in frontmatter
3. Maps Jira statuses to task folders

#### Status Mapping

| Jira Status | Task Folder |
|-------------|-------------|
| To Do | `Tasks/Inbox/` or `Tasks/Next/` |
| In Progress | `Tasks/Next/` |
| In Review | `Tasks/Waiting/` |
| Blocked | `Tasks/Waiting/` |
| Done | `Tasks/Completed/` |

**Note:** Jira is the source of truth. If you change status locally, the next sync will overwrite it.

### MCP Server Integration

The MCP server allows AI assistants to interact with your vault programmatically.

#### Starting the Server

```bash
uv run aio-mcp
```

Or if installed globally:
```bash
aio-mcp
```

#### Available MCP Tools

| Tool | Description |
|------|-------------|
| `aio_add_task` | Create a new task with optional due date, project, and delegation |
| `aio_list_tasks` | List tasks filtered by status or project |
| `aio_complete_task` | Mark a task as completed |
| `aio_start_task` | Move a task to Next status |
| `aio_defer_task` | Move a task to Someday status |
| `aio_get_dashboard` | Get today's dashboard content |
| `aio_get_context` | Retrieve context pack content |
| `aio_list_context_packs` | List available context packs by category |
| `aio_create_context_pack` | Create a new context pack |
| `aio_add_to_context_pack` | Append content to an existing context pack |
| `aio_add_file_to_context_pack` | Copy a file's content into a context pack |
| `aio_sync_jira` | Sync tasks from Jira (imports assigned issues) |
| `aio_jira_status` | Get Jira sync status and configuration |

#### Available MCP Resources

| Resource URI | Content |
|--------------|---------|
| `aio://tasks/inbox` | Current inbox tasks |
| `aio://tasks/next` | Next actions |
| `aio://tasks/waiting` | Waiting-for items |
| `aio://tasks/today` | Tasks due today + overdue |
| `aio://projects` | Active projects list |
| `aio://dashboard` | Today's dashboard |

#### Example Usage

Once configured, you can ask your AI assistant:

- "What's on my plate today?" → Uses `aio_get_dashboard`
- "Add a task to review the PR by Friday" → Uses `aio_add_task`
- "Add a task for Sarah to update the docs" → Uses `aio_add_task` with `assign`
- "Show my inbox" → Uses `aio_list_tasks`
- "Mark the auth bug task as done" → Uses `aio_complete_task`

---

## File Formats

### Task Files

Tasks are markdown files with YAML frontmatter in `AIO/Tasks/{Status}/`.

**Example:** `AIO/Tasks/Next/2026-01-15-review-sarahs-pr.md`

```markdown
---
id: X7KP
type: task
status: next
due: 2026-01-16
project: "[[Projects/Q4-Migration]]"
location:
  url: "https://github.com/company/repo/pull/456"
blockedBy: []
blocks: []
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

### Project Files

Projects are hubs linking everything related to a body of work.

**Example:** `AIO/Projects/Q4-Migration.md`

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
| Tech Spec | [[Specs/Platform-Migration-Spec]] |
| Slack | [#platform-migration](https://slack.com/...) |

## Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Design complete | 2026-01-31 | Done |
| API migration | 2026-02-15 | In Progress |
| Cutover | 2026-03-15 | Not Started |

## Open Tasks

```dataview
TABLE status, due, assignedTo.file.name AS "Owner"
FROM "Tasks"
WHERE contains(project, this.file.link) AND status != "completed"
SORT due ASC
```

## Risks

- [ ] Dependency on Auth team for token migration
- [ ] Load testing environment not ready
```

### People Files

Track your direct reports and delegates.

**Example:** `AIO/People/Sarah.md`

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

## Tips

### Capture Fast, Process Later

Don't stop to organize when capturing. Just:
```bash
aio add "the thing"
```
Process your inbox during your morning routine or weekly review.

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

### Keyboard Shortcuts (Obsidian)

Set these up in Obsidian's hotkey settings:

| Action | Suggested Hotkey |
|--------|------------------|
| Open today's dashboard | `Cmd+Shift+D` |
| Quick add task | `Cmd+Shift+A` |
| Open inbox folder | `Cmd+Shift+I` |

---

## Troubleshooting

### CLI Issues

**"Vault not found"**
```bash
aio config set vault.path /correct/path/to/vault
```

**Command not found after install**
```bash
uv pip install -e . --force-reinstall
```

### Obsidian Issues

**Dataview queries not working**
1. Ensure Dataview plugin is installed and enabled
2. Check that frontmatter fields match exactly (case-sensitive)
3. Reload Obsidian

**Tasks not appearing in project view**
Ensure the task's `project` field uses wikilink syntax:
```yaml
project: "[[Projects/Q4-Migration]]"
```

### Jira Issues

**Jira sync creates duplicates**
Check that existing task files have the correct `jiraKey` in frontmatter.

### MCP Issues

**Server not starting**
- Verify `uv` is installed and in your PATH
- Check the directory path in the configuration is correct
- Try running `uv run aio-mcp` manually to see error messages

**Vault not found**
- Ensure `AIO_VAULT_PATH` points to a valid Obsidian vault
- The vault must have been initialized with `aio init`

**Tools not appearing**
- Restart your MCP client after configuration changes
- Check your client's logs for connection errors

---

## Reference

### File Locations

| Content | Location |
|---------|----------|
| Config | `.aio/config.yaml` |
| Today's dashboard | `AIO/Dashboard/YYYY-MM-DD.md` |
| Inbox tasks | `AIO/Tasks/Inbox/*.md` |
| Active tasks | `AIO/Tasks/Next/*.md` |
| Delegated tasks | `AIO/Tasks/Waiting/*.md` |
| Scheduled tasks | `AIO/Tasks/Scheduled/*.md` |
| Deferred tasks | `AIO/Tasks/Someday/*.md` |
| Completed tasks | `AIO/Tasks/Completed/YYYY/MM/*.md` |
| Projects | `AIO/Projects/*.md` |
| People | `AIO/People/*.md` |
| Areas | `AIO/Areas/*.md` |
| Archived items | `AIO/Archive/**/*.md` |

### The Morning Dashboard

Your dashboard shows:

| Section | Content |
|---------|---------|
| **Overdue** | Tasks past their due date |
| **Due Today** | Your focus for the day |
| **Due This Week** | What's coming |
| **Blocked** | Tasks waiting on dependencies |
| **Waiting For** | Delegated tasks, grouped by person |
| **Team Load** | Active tasks per person |
| **Quick Links** | Jump to common views |
