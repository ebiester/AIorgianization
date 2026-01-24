# User Acceptance Testing Plan: AIorgianization

This document provides a comprehensive UAT plan to verify all documented functionality works as expected. Tests are organized by feature area and phase.

---

## Prerequisites

Before running any tests:

1. **Environment Setup**
   - Python 3.12+ installed
   - `uv` package manager installed
   - Dependencies installed via `uv sync`

2. **Test Vault**
   - **IMPORTANT:** The vault must be created by Obsidian first, not manually via `mkdir`
   - Open Obsidian → "Create new vault" → Name it `aio-dev` → Location: `<project-root>/test-obsidian-vault/`
   - This creates the vault with Obsidian's `.obsidian/` directory structure
   - Test vault path: `<project-root>/test-obsidian-vault/aio-dev`
   - Running `aio init` on a directory that wasn't created by Obsidian will error

3. **Clean State**
   - Each test section assumes a clean or known state
   - To reset the AIO structure (but keep the Obsidian vault): `rm -rf <vault>/AIO <vault>/.aio`
   - Then re-run `aio init` to recreate

---

## Phase 1: Foundation (Core CLI)

### UAT-001: Vault Initialization

**Objective:** Verify `aio init` creates the correct directory structure.

**Prerequisite:** Vault must be created by Obsidian first. Open Obsidian → "Create new vault" → Name: `aio-dev` → Location: `<project-root>/test-obsidian-vault/`. This creates the `.obsidian/` directory that `aio init` requires.

**Test Vault Path:** `test-obsidian-vault/aio-dev` (relative to project root)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Verify `.obsidian/` exists in vault | Obsidian has initialized the vault |
| 2 | Run `aio init test-obsidian-vault/aio-dev` | Success message: vault initialized |
| 3 | Check `test-obsidian-vault/aio-dev/AIO/` exists | Directory exists |
| 4 | Check `AIO/Dashboard/` exists | Directory exists |
| 5 | Check `AIO/Tasks/` exists | Directory exists |
| 6 | Check `AIO/Tasks/Inbox/` exists | Directory exists |
| 7 | Check `AIO/Tasks/Next/` exists | Directory exists |
| 8 | Check `AIO/Tasks/Waiting/` exists | Directory exists |
| 9 | Check `AIO/Tasks/Scheduled/` exists | Directory exists |
| 10 | Check `AIO/Tasks/Someday/` exists | Directory exists |
| 11 | Check `AIO/Tasks/Completed/` exists | Directory exists |
| 12 | Check `AIO/Projects/` exists | Directory exists |
| 13 | Check `AIO/People/` exists | Directory exists |
| 14 | Check `AIO/Areas/` exists | Directory exists |
| 15 | Check `AIO/Archive/` exists | Directory exists |
| 16 | Check `AIO/Archive/Tasks/` exists | Directory exists with parallel subfolders (Inbox/, Next/, Waiting/, Scheduled/, Someday/) |
| 17 | Check `AIO/Archive/Projects/` exists | Directory exists |
| 18 | Check `AIO/Archive/People/` exists | Directory exists |
| 19 | Check `AIO/Archive/Areas/` exists | Directory exists |
| 20 | Check `.aio/config.yaml` exists | Config file exists in vault root |
| 21 | Run `aio init test-obsidian-vault/aio-dev` again | Idempotent: no errors, structure unchanged |

**Pass Criteria:** All directories created, config file present, re-running init doesn't break anything.

**Error Case:** Running `aio init` on a directory without `.obsidian/` should produce a clear error message indicating the vault must be created by Obsidian first.

---

### UAT-002: Configuration Display

**Objective:** Verify configuration can be displayed.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio config show` | Shows `vault.path = test-obsidian-vault/aio-dev` (or configured path) |

**Pass Criteria:** Config displays correctly.

---

### UAT-003: Quick Task Add (Basic)

**Objective:** Verify basic task creation.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Review PR #123"` | Success message with task ID (4-char, e.g., "AB2C") |
| 2 | Check `test-obsidian-vault/aio-dev/AIO/Tasks/Inbox/` | New `.md` file exists with title in filename |
| 3 | Open the created file | Contains YAML frontmatter with: `id`, `type: task`, `status: inbox`, `created`, `updated` |
| 4 | Verify `id` format | 4 alphanumeric characters (excludes 0, 1, I, O) |
| 5 | Verify title in file | Heading `# Review PR #123` present |

**Pass Criteria:** Task file created in Inbox with correct frontmatter and ID format.

---

### UAT-004: Quick Task Add (With Due Date)

**Objective:** Verify task creation with natural language dates.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Call vendor" -d tomorrow` | Success message with task ID |
| 2 | Open created file | `due:` field contains tomorrow's date (YYYY-MM-DD format) |
| 3 | Run `aio add "Submit report" -d "next friday"` | Success message with task ID |
| 4 | Open created file | `due:` field contains next Friday's date |
| 5 | Run `aio add "Quarterly planning" -d 2026-02-01` | Success message with task ID |
| 6 | Open created file | `due: 2026-02-01` in frontmatter |
| 7 | Run `aio add "Today task" -d today` | Success message with task ID |
| 8 | Open created file | `due:` field contains today's date |

**Pass Criteria:** All date formats parse correctly and store as ISO dates.

---

### ~~UAT-005: Quick Task Add (With Priority)~~ [DELETED]

*Feature removed - priority not implemented.*

---

### UAT-006: Quick Task Add (With Project)

**Objective:** Verify task creation linked to a project.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Design API" -p "Q4 Migration"` (project doesn't exist) | Error: "Project not found: Q4 Migration" with suggestion to use `--create-project` |
| 2 | Run `aio add "Design API" -p "Q4 Migration" --create-project` | Success: project created, then task created |
| 3 | Check `AIO/Projects/` | `Q4-Migration.md` exists with proper template |
| 4 | Open created task file | `project: "[[Projects/Q4 Migration]]"` in frontmatter |
| 5 | Run `aio add "Another task" -p "Q4 Migration"` | Success (project now exists) |
| 6 | Run `aio add "Typo test" -p "Q4 Migartion"` | Error with fuzzy match suggestion: "Did you mean? Q4-Migration" |

**Pass Criteria:** Project validation prevents typos, `--create-project` flag enables explicit creation, project files created in correct location with template.

**Error Case:** Specifying a non-existent project without `--create-project` should error with helpful suggestions.

---

### UAT-007: Quick Task Add (Combined Options)

**Objective:** Verify task creation with multiple options.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Ensure project "Q4 Migration" exists (from UAT-006) | Project file present |
| 2 | Run `aio add "Review spec" -d friday -p "Q4 Migration"` | Success message |
| 3 | Open created file | Both `due:` (Friday's date) and `project:` present |

**Pass Criteria:** Multiple options combine correctly when project exists.

---

### UAT-007a: Quick Task Add (With Assign)

**Objective:** Verify task creation with immediate delegation using `--assign` flag.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a person first: `aio add "Setup task" && aio wait <id> Sarah --create-person` | Person "Sarah" created |
| 2 | Run `aio add "Review API design" --assign Sarah` | Success message with task ID, status: waiting |
| 3 | Check output | Shows "Status: waiting" and "Waiting on: [[AIO/People/Sarah]]" |
| 4 | Check `AIO/Tasks/Waiting/` | Task file exists (not in Inbox) |
| 5 | Open task file | `status: waiting`, `waitingOn: "[[AIO/People/Sarah]]"` in frontmatter |
| 6 | Run `aio add "Update docs" -a Bob` (person doesn't exist) | Error: "Person not found: Bob" |
| 7 | Run `aio add "Design schema" -p "Q4 Migration" --assign Sarah -d friday` | Task created with project, due date, AND delegation |
| 8 | Check created file | All fields present: `project`, `due`, `waitingOn`, `status: waiting` |

**Pass Criteria:** `--assign` creates task directly in Waiting status with person link. Combines correctly with other options. Fails cleanly if person doesn't exist.

**MCP Equivalent:** `aio_add_task({title: "Review API", assign: "Sarah"})` should produce the same result.

---

### UAT-008: Task Listing (Basic)

**Objective:** Verify task listing commands.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Ensure at least 3 tasks exist in Inbox | (Use previous tests or create manually) |
| 2 | Run `aio list` | Shows all active tasks |
| 3 | Run `aio list inbox` | Shows only Inbox tasks |
| 4 | Output includes | Task ID, title, due date (if set) |

**Pass Criteria:** List commands show appropriate tasks with readable format.

---

### UAT-009: Task Listing (By Status)

**Objective:** Verify filtering by status folders.

**Setup:** Create tasks in different statuses (move some manually if needed).

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio list next` | Shows only Next folder tasks |
| 2 | Run `aio list waiting` | Shows only Waiting folder tasks |
| 3 | Run `aio list someday` | Shows only Someday folder tasks |
| 4 | Run `aio list today` | Shows tasks due today + overdue |
| 5 | Run `aio list overdue` | Shows only tasks past due date |

**Pass Criteria:** Each filter shows only matching tasks.

---

### UAT-010: Task Listing (All Including Completed)

**Objective:** Verify listing completed tasks.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Complete a task (see UAT-012) | Task moves to Completed |
| 2 | Run `aio list` | Completed task NOT shown |
| 3 | Run `aio list all --completed` | Completed task IS shown |

**Pass Criteria:** Completed tasks filtered by default, visible with flag.

---

### UAT-011: Status Transition - Next

**Objective:** Verify moving task from Inbox to Next.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Test next"` | Task in Inbox |
| 2 | Note the task ID | e.g., "XY3Z" |
| 3 | Run `aio next XY3Z` | Success message |
| 4 | Check Inbox folder | Task file no longer there |
| 5 | Check Next folder | Task file now there |
| 6 | Open task file | `status: next` in frontmatter, `updated` timestamp changed |

**Pass Criteria:** File moves to Next folder, status updated.

---

### UAT-012: Status Transition - Done

**Objective:** Verify completing a task.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Test done"` | Task in Inbox |
| 2 | Run `aio done "Test done"` (by title) | Success message |
| 3 | Check Inbox folder | Task file no longer there |
| 4 | Check `Tasks/Completed/YYYY/MM/` | Task file now in year/month subfolder |
| 5 | Open task file | `status: completed`, `completed:` timestamp set |

**Pass Criteria:** Task moves to Completed with date organization, timestamps updated.

---

### UAT-013: Status Transition - Start

**Objective:** Verify starting a task (moving to in-progress).

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create and activate task | Task in Next |
| 2 | Run `aio start <id>` | Success message |
| 3 | Open task file | Status reflects "in progress" or moved to active state |

**Pass Criteria:** Task marked as in-progress.

---

### UAT-014: Status Transition - Defer

**Objective:** Verify deferring a task to Someday.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Test defer"` | Task in Inbox |
| 2 | Run `aio defer "Test defer"` | Success message |
| 3 | Check Inbox folder | Task file no longer there |
| 4 | Check Someday folder | Task file now there |
| 5 | Run `aio list` | Task NOT in default list |
| 6 | Run `aio list someday` | Task IS shown |
| 7 | Run `aio next <id>` | Task moves back to Next |

**Pass Criteria:** Deferred tasks hidden from default view, can be reactivated.

---

### UAT-015: Status Transition - Wait (Delegation)

**Objective:** Verify delegating a task to someone.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Test delegation"` | Task in Inbox |
| 2 | Run `aio wait "Test delegation" Sarah --create-person` | Success: person created (if new), task delegated |
| 3 | Check Inbox folder | Task file no longer there |
| 4 | Check Waiting folder | Task file now there |
| 5 | Open task file | `status: waiting`, `waitingOn: "[[AIO/People/Sarah]]"` |
| 6 | Run `aio list waiting` | Task appears |
| 7 | Open `AIO/People/Sarah.md` in Obsidian | "Tasks Delegated" section shows the task via Dataview |
| 8 | Complete the task: `aio done "Test delegation"` | Task marked completed |
| 9 | Refresh Sarah.md in Obsidian | Task moves from "Tasks Delegated" to "Previously Completed Tasks" |

**Pass Criteria:** Task in Waiting folder with person link. Person file shows active delegations separate from completed tasks.

**Note:** The Person file uses Dataview queries with `link()` function to match wikilinks in the `waitingOn` frontmatter field.

---

### UAT-016: Task Lookup by ID (Case Insensitive)

**Objective:** Verify task lookup works case-insensitively.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task, note ID (e.g., "AB2C") | Task created |
| 2 | Run `aio done AB2C` | Task completed |
| 3 | Create another task, note ID (e.g., "XY3Z") | Task created |
| 4 | Run `aio done xy3z` (lowercase) | Task completed |

**Pass Criteria:** Both uppercase and lowercase IDs work.

---

### UAT-017: Task Lookup by Title Substring

**Objective:** Verify task lookup by partial title.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Review Sarah's PR for authentication"` | Task created |
| 2 | Run `aio done "Sarah's PR"` | Task completed (substring match) |
| 3 | Create task: `aio add "Another unique task"` | Task created |
| 4 | Run `aio done "unique"` | Task completed |

**Pass Criteria:** Substring matching works for task operations.

---

### UAT-018: Task Lookup - Not Found

**Objective:** Verify error handling for non-existent tasks.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio done ZZZZ` | Error: "Task not found" |
| 2 | Run `aio done "nonexistent gibberish"` | Error: "Task not found" |
| 3 | Exit code | Non-zero (1) |

**Pass Criteria:** Clear error message, non-zero exit code.

---

### UAT-019: Waiting Tasks View

**Objective:** Verify listing tasks in waiting status.

**Setup:** Create tasks and move them to waiting status.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task: `aio add "Get feedback from Sarah"` | Task created |
| 2 | Run `aio wait <id> Sarah` | Task moved to waiting, waitingOn set |
| 3 | Run `aio list waiting` | Shows all waiting tasks |
| 4 | Output includes | Task ID, title, status shown as waiting |

**Pass Criteria:** Waiting tasks are listed correctly.

**Deferred:** Grouped delegated view by person (`aio delegated`) - not yet implemented.

---

### UAT-020: Dashboard Generation

**Objective:** Verify dashboard command creates/updates daily note.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio dashboard` | Success message |
| 2 | Check for dashboard file | Either appends to daily note or creates `AIO/Dashboard/YYYY-MM-DD.md` |
| 3 | Open dashboard file | Contains sections: Overdue, Due Today, Due This Week, Waiting For |
| 4 | Run `aio dashboard --date 2026-01-20` | Creates dashboard for specific date |

**Pass Criteria:** Dashboard generated with appropriate sections.

---

### UAT-021: Archive Single Task

**Objective:** Verify archiving individual tasks (tasks that won't be done but are worth keeping for reference).

**Note:** Archiving is for abandoning tasks, not for completed tasks. Completed tasks stay in `Tasks/Completed/`. Archived tasks preserve their original status folder in the archive structure.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a task: `aio add "Feature that got descoped"` | Task in Inbox |
| 2 | Move to Next: `aio start <id>` | Task in Next folder |
| 3 | Run `aio archive task <id>` | Success message |
| 4 | Check `AIO/Tasks/Next/` | Task file no longer there |
| 5 | Check `AIO/Archive/Tasks/Next/` | Task file now in archive (parallel structure) |
| 6 | Open archived task file | Status unchanged (`status: next`), file preserved |

**Pass Criteria:** Task moved to parallel archive structure, preserving original status folder.

---

### UAT-022: Archive Single Project

**Objective:** Verify archiving projects.

**Setup:** Create a project file in `AIO/Projects/`.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio archive project <project-name>` | Success message |
| 2 | Check `AIO/Projects/` | Project file no longer there |
| 3 | Check `AIO/Archive/Projects/` | Project file now in archive |

**Pass Criteria:** Project moved to archive.

---

### UAT-023: Archive Tasks by Date

**Objective:** Verify bulk archiving completed tasks before a date.

**Setup:** Have several completed tasks with different completion dates.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio archive tasks --before 2026-01-01 --dry-run` | Shows what WOULD be archived, no changes made |
| 2 | Verify dry-run | Files still in original locations |
| 3 | Run `aio archive tasks --before 2026-01-01` | Success message with count |
| 4 | Check Completed folder | Old tasks moved |
| 5 | Check Archive/Tasks/ | Archived tasks present |

**Pass Criteria:** Date-based archiving works, dry-run prevents changes.

---

### UAT-024: Archive with Natural Language Date

**Objective:** Verify archive command accepts natural language dates.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio archive tasks --before "6 months ago" --dry-run` | Shows tasks older than 6 months |

**Pass Criteria:** Natural language dates work for archive command.

---

### UAT-025: Error Handling - Invalid Date

**Objective:** Verify error handling for invalid dates.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Test" -d "gibberish not a date"` | Error message about invalid date |
| 2 | Check Inbox folder | No task created |
| 3 | Exit code | Non-zero |

**Pass Criteria:** Clear error, no partial state.

---

### ~~UAT-026: Error Handling - Invalid Priority~~ [DELETED]

*Feature removed - priority not implemented.*

---

### UAT-027: Error Handling - Vault Not Initialized

**Objective:** Verify error when vault not set up.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create empty directory: `mkdir ~/EmptyVault` | Directory exists |
| 2 | Temporarily point config to EmptyVault (or use env var) | |
| 3 | Run `aio list` | Error with clear message to run `aio init` |

**Pass Criteria:** Clear remediation instructions.

---

## Phase 3: Jira Integration

### UAT-028: Jira Configuration

**Objective:** Verify Jira settings can be configured.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio config set jira.baseUrl https://company.atlassian.net` | Success |
| 2 | Run `aio config set jira.email your@email.com` | Success |
| 3 | Run `aio config set jira.projects PLAT,ALPHA` | Success |
| 4 | Set `JIRA_API_TOKEN` environment variable | Token set |
| 5 | Run `aio config show` | Shows Jira configuration |

**Pass Criteria:** Jira settings stored and displayed.

---

### UAT-029: Jira Sync (Requires Live Jira)

**Objective:** Verify Jira sync imports issues.

**Prerequisite:** Valid Jira credentials and assigned issues.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio sync jira` | Output: "Synced X tasks (Y new, Z updated)" |
| 2 | Check Tasks folder | New task files with `jiraKey:` in frontmatter |
| 3 | Run `aio sync jira` again | No duplicates created (idempotent) |
| 4 | Verify task content | Title matches Jira issue summary |

**Pass Criteria:** Issues sync correctly, no duplicates.

---

### UAT-030: Jira Sync - Status Mapping

**Objective:** Verify Jira statuses map to correct folders.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Jira issue with "To Do" status | Task in Inbox or Next |
| 2 | Jira issue with "In Progress" status | Task in Next |
| 3 | Jira issue with "In Review" status | Task in Waiting |
| 4 | Jira issue with "Done" status | Task in Completed |

**Pass Criteria:** Status mapping follows documented rules.

---

### UAT-031: Jira Sync - Auth Failure

**Objective:** Verify error handling for Jira auth issues.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Set invalid `JIRA_API_TOKEN` | |
| 2 | Run `aio sync jira` | Clear error message with remediation steps |
| 3 | Exit code | Non-zero |

**Pass Criteria:** User-friendly auth error message.

---

## Phase 4: MCP Server Integration

### UAT-032: MCP Server Startup

**Objective:** Verify MCP server can start.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `uv run aio-mcp` | Server starts without errors |
| 2 | Server output | Shows available tools/resources |

**Pass Criteria:** Server starts and exposes tools.

---

### UAT-033: MCP Tool - Add Task

**Objective:** Verify MCP add task tool.

**Note:** This requires MCP client (Cursor or test harness).

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_add_task({title: "MCP Test", due: "tomorrow"})` | Returns task ID |
| 2 | Check vault | Task file created in Inbox |

**Pass Criteria:** MCP tool creates task successfully.

---

### UAT-033a: MCP Tool - Add Task with Assign

**Objective:** Verify MCP add task tool with delegation.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create person first: `aio_create_person({name: "Alice"})` | Person created |
| 2 | Call `aio_add_task({title: "Delegated via MCP", assign: "Alice"})` | Returns task ID with status: waiting |
| 3 | Response includes | "Status: waiting" and "Waiting on:" fields |
| 4 | Check vault | Task file in `Tasks/Waiting/` (not Inbox) |
| 5 | Call `aio_add_task({title: "Unknown person", assign: "Nobody"})` | Returns error: "Person not found" |

**Pass Criteria:** MCP assign parameter creates delegated task. Fails cleanly for unknown person.

---

### UAT-034: MCP Tool - List Tasks

**Objective:** Verify MCP list tasks tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_list_tasks({status: "inbox"})` | Returns array of inbox tasks |
| 2 | Response format | Structured task objects with id, title, due, etc. |

**Pass Criteria:** MCP returns properly formatted task list.

---

### UAT-035: MCP Tool - Complete Task

**Objective:** Verify MCP complete task tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task via MCP or CLI | Task exists |
| 2 | Call `aio_complete_task({id: "<task-id>"})` | Returns success |
| 3 | Check vault | Task moved to Completed |

**Pass Criteria:** MCP can complete tasks.

---

### UAT-036: MCP Tool - Start Task

**Objective:** Verify MCP start task tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_start_task({id: "<task-id>"})` | Returns success |
| 2 | Check task status | Marked as in-progress |

**Pass Criteria:** MCP can start tasks.

---

### UAT-037: MCP Tool - Defer Task

**Objective:** Verify MCP defer task tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_defer_task({id: "<task-id>"})` | Returns success |
| 2 | Check vault | Task moved to Someday |

**Pass Criteria:** MCP can defer tasks.

---

### UAT-038: MCP Tool - Get Dashboard

**Objective:** Verify MCP dashboard tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_get_dashboard()` | Returns dashboard content |
| 2 | Response includes | Overdue, Due Today, Waiting For sections |

**Pass Criteria:** Dashboard content returned via MCP.

---

### UAT-039: MCP Tool - Jira Sync

**Objective:** Verify MCP Jira sync tool.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `aio_sync_jira()` | Returns sync result |
| 2 | Response includes | Count of new/updated tasks |

**Pass Criteria:** Jira sync works via MCP.

---

### UAT-040: MCP Resources

**Objective:** Verify MCP resource endpoints.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Access `aio://tasks/inbox` | Returns inbox tasks |
| 2 | Access `aio://tasks/next` | Returns next action tasks |
| 3 | Access `aio://tasks/waiting` | Returns waiting tasks |
| 4 | Access `aio://tasks/today` | Returns today + overdue tasks |
| 5 | Access `aio://projects` | Returns project list |
| 6 | Access `aio://dashboard` | Returns dashboard content |

**Pass Criteria:** All resources return expected data.

---

## Phase 2: Obsidian Plugin

### UAT-041: Plugin Installation

**Objective:** Verify plugin can be installed in Obsidian.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Copy plugin files to `.obsidian/plugins/obsidian-aio/` | Files in place |
| 2 | Restart Obsidian | Plugin appears in community plugins list |
| 3 | Enable the plugin | Plugin activates without errors |

**Pass Criteria:** Plugin loads successfully.

---

### UAT-042: Plugin Settings

**Objective:** Verify plugin settings tab.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open Settings → Community Plugins → AIo | Settings tab opens |
| 2 | Configure folder paths | Paths saved |
| 3 | Configure Jira settings (if applicable) | Settings saved |

**Pass Criteria:** Settings persist after Obsidian restart.

---

### UAT-043: Task List View

**Objective:** Verify task list custom pane.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Cmd+P → "AIo: Open task list" | Task list pane opens |
| 2 | View loads | Shows tasks with summary counts |
| 3 | Click "Inbox (N)" filter | Shows only inbox tasks |
| 4 | Task display | Shows checkbox, title, priority badge, due date |

**Pass Criteria:** Task list renders with filtering.

---

### UAT-044: Quick Add Modal

**Objective:** Verify quick add command.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Cmd+P → "AIo: Add task" | Quick add modal opens |
| 2 | Type "Test task -d tomorrow -P P1" | Preview shows parsed: "Due: tomorrow, Priority: P1" |
| 3 | Press Enter | Modal closes, task created |
| 4 | Press Esc (on new modal) | Modal closes, no task created |

**Pass Criteria:** Quick add with preview and keyboard shortcuts.

---

### UAT-045: Add to Inbox Modal

**Objective:** Verify minimal inbox add.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Cmd+P → "AIo: Add to inbox" | Minimal modal with just title input |
| 2 | Type title, press Enter | Task created in inbox |

**Pass Criteria:** Fast capture with minimal UI.

---

### UAT-046: Task Edit Modal

**Objective:** Verify task editing in plugin.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click a task in list view | Task detail modal opens |
| 2 | All frontmatter fields visible | Title, status, due, project, priority, etc. |
| 3 | Edit title | Change persists to file |
| 4 | Change due date | Date picker works, saves correctly |
| 5 | Change project dropdown | Wikilink picker shows available projects |
| 6 | Press Cmd+Enter | Modal closes, changes saved |

**Pass Criteria:** All fields editable with proper controls.

---

### UAT-047: Status Commands

**Objective:** Verify status commands from plugin.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Select task, Cmd+P → "AIo: Complete task" | Task marked completed |
| 2 | Select task, Cmd+P → "AIo: Start task" | Task moved to Next/in-progress |
| 3 | Select task, Cmd+P → "AIo: Defer task" | Task moved to Someday |
| 4 | Select task, Cmd+P → "AIo: Move to waiting" | Prompt for person, then moves to Waiting |

**Pass Criteria:** All status transitions work from command palette.

---

### UAT-048: Inbox Processing View

**Objective:** Verify inbox processing workflow.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create several inbox items | Items in Inbox |
| 2 | Open Inbox view in plugin | Shows items one-by-one with action buttons |
| 3 | Click "Next Action" on item | Item moves to Next, shows next inbox item |
| 4 | Click "Defer" on item | Item moves to Someday, shows next inbox item |
| 5 | Process all items | "Inbox Zero!" message |

**Pass Criteria:** One-by-one processing with actions.

---

### UAT-049: Manual Jira Sync Command

**Objective:** Verify manual sync from plugin.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Cmd+P → "AIo: Sync Jira" | Sync triggers |
| 2 | Progress indicator | Shows sync in progress |
| 3 | Completion | Shows sync results |

**Pass Criteria:** Manual sync works from Obsidian.

---

## Task File Format Validation

### UAT-050: Task File Frontmatter

**Objective:** Verify task files have correct format.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task via CLI | File created |
| 2 | Open file in text editor | Valid YAML frontmatter between `---` markers |
| 3 | Check required fields | `id`, `type: task`, `status`, `created`, `updated` present |
| 4 | Check ID format | 4 characters, alphanumeric, no 0/1/I/O |
| 5 | Check timestamps | ISO 8601 format (YYYY-MM-DDTHH:MM:SS) |

**Pass Criteria:** File format matches specification.

---

### UAT-051: Waiting-For Task Format

**Objective:** Verify delegated task format and Person file integration.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Delegate task to person | Task in Waiting |
| 2 | Open task file | `waitingOn: "[[AIO/People/PersonName]]"` present |
| 3 | Status field | `status: waiting` |
| 4 | Open Person file in Obsidian | Two Dataview sections: "Tasks Delegated" and "Previously Completed Tasks" |
| 5 | Verify "Tasks Delegated" query | Uses `contains(waitingOn, link("AIO/People/PersonName")) AND status != "completed"` |
| 6 | Verify "Previously Completed Tasks" query | Uses `contains(waitingOn, link("AIO/People/PersonName")) AND status = "completed"` |

**Pass Criteria:** Delegation metadata stored correctly. Person file separates active from completed delegations.

---

### UAT-052: Task with Subtasks

**Objective:** Verify subtask format in task body.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open a task file | Contains markdown body after frontmatter |
| 2 | Add subtasks manually | `## Subtasks` section with `- [ ]` items |
| 3 | Check rendering | Subtasks render as checkboxes in Obsidian |

**Pass Criteria:** Subtask format compatible with Obsidian.

---

### UAT-053: Task with Location

**Objective:** Verify location linking in tasks.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Manually add location to task frontmatter | `location: {file: "src/api.ts", line: 42}` |
| 2 | Or add URL | `location: {url: "https://github.com/..."}` |
| 3 | Check file saves correctly | YAML remains valid |

**Pass Criteria:** Location field format works (manual for now, per PROJECT_PLAN).

---

### UAT-054: Task with Dependencies

**Objective:** Verify dependency linking format.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create two tasks | Tasks A and B exist |
| 2 | Manually add to task A frontmatter | `blockedBy: ["<task-B-id>"]` |
| 3 | Manually add to task B frontmatter | `blocks: ["<task-A-id>"]` |
| 4 | Check files | YAML remains valid |

**Pass Criteria:** Dependency format works (model exists per PROJECT_PLAN).

---

## Workflow Tests

### UAT-055: Daily Workflow - Morning

**Objective:** Verify morning workflow per User Manual.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio dashboard` | Dashboard generated |
| 2 | Open dashboard in Obsidian | Sections visible |
| 3 | Review Overdue section | Shows tasks past due |
| 4 | Review Due Today section | Shows today's tasks |
| 5 | Review Waiting For section | Shows delegated items |

**Pass Criteria:** Dashboard provides actionable morning view.

---

### UAT-056: Daily Workflow - Capture

**Objective:** Verify capture workflow.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Quick thought"` | Task created in <2 seconds |
| 2 | Run `aio add "Meeting prep" -d tomorrow` | Task with due date |
| 3 | Check inbox | Both tasks present |

**Pass Criteria:** Fast capture (<5 seconds per task goal).

---

### UAT-057: Daily Workflow - Status Updates

**Objective:** Verify working on tasks.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | `aio start "Quick thought"` | Task in progress |
| 2 | `aio done "Quick thought"` | Task completed |
| 3 | `aio wait "Meeting prep" Sarah` | Task delegated |
| 4 | `aio defer "some task"` | Task to someday |

**Pass Criteria:** All status transitions work smoothly.

---

### UAT-058: Weekly Review Workflow

**Objective:** Verify weekly review steps.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create items in inbox, next, waiting, someday | Mixed state |
| 2 | Run `aio list inbox` | See all inbox items |
| 3 | Process each inbox item | Move to appropriate status |
| 4 | Run `aio list inbox` | Empty (Inbox Zero) |
| 5 | Run `aio delegated` | Review waiting-for items |
| 6 | Run `aio list someday` | Review deferred items |

**Pass Criteria:** Weekly review achievable via CLI.

---

## Edge Cases and Error Handling

### UAT-059: Empty Vault Operations

**Objective:** Verify commands work with no tasks.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start with empty vault (run init) | Clean state |
| 2 | Run `aio list` | "No tasks found" or empty list (not error) |
| 3 | Run `aio list inbox` | Empty list (not error) |
| 4 | Run `aio delegated` | Empty (not error) |
| 5 | Run `aio dashboard` | Dashboard with empty sections |

**Pass Criteria:** Empty state handled gracefully.

---

### UAT-060: Special Characters in Task Title

**Objective:** Verify handling of special characters.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | `aio add "Review John's PR #123 (urgent!)"` | Task created |
| 2 | Check filename | Special chars handled (escaped or removed) |
| 3 | Check file content | Title preserved correctly in heading |
| 4 | `aio done "John's PR"` | Can find by partial match |

**Pass Criteria:** Special characters don't break system.

---

### UAT-061: Unicode in Task Title

**Objective:** Verify unicode support.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | `aio add "Review café menu 🎉"` | Task created |
| 2 | Check file content | Unicode preserved (UTF-8) |
| 3 | `aio list` | Unicode displays correctly |

**Pass Criteria:** Full unicode support.

---

### UAT-062: Very Long Task Title

**Objective:** Verify handling of long titles.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create task with 200+ character title | Task created |
| 2 | Check filename | Truncated appropriately |
| 3 | Check file content | Full title preserved inside file |
| 4 | Task findable | Can find by ID or partial title |

**Pass Criteria:** Long titles handled without breaking.

---

### UAT-063: Concurrent Operations

**Objective:** Verify handling of rapid commands.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run 3 add commands rapidly | All 3 tasks created |
| 2 | Each task has unique ID | No collisions |
| 3 | No file corruption | All files valid YAML |

**Pass Criteria:** Concurrent operations safe.

---

### UAT-064: Exit Codes

**Objective:** Verify proper exit codes.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio list; echo $?` | Exit code 0 |
| 2 | Run `aio done ZZZZ; echo $?` | Exit code 1 (error) |
| 3 | Run `aio add; echo $?` (missing title) | Exit code 2 (usage error) |

**Pass Criteria:** Exit codes follow convention.

---

### UAT-065: No Stack Traces in Normal Use

**Objective:** Verify user-friendly error messages.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Trigger various errors (not found, invalid input) | User-friendly messages |
| 2 | No Python tracebacks | Clean output |
| 3 | Run with `--debug` flag (if available) | Stack traces shown for debugging |

**Pass Criteria:** Clean errors for users, debug option for developers.

---

## Test Summary Checklist

### Phase 1: Foundation
- [ ] UAT-001: Vault Initialization
- [ ] UAT-002: Configuration Display
- [ ] UAT-003: Quick Task Add (Basic)
- [ ] UAT-004: Quick Task Add (With Due Date)
- [x] ~~UAT-005: Quick Task Add (With Priority)~~ [DELETED]
- [ ] UAT-006: Quick Task Add (With Project)
- [ ] UAT-007: Quick Task Add (Combined Options)
- [ ] UAT-007a: Quick Task Add (With Assign)
- [ ] UAT-008: Task Listing (Basic)
- [ ] UAT-009: Task Listing (By Status)
- [ ] UAT-010: Task Listing (All Including Completed)
- [ ] UAT-011: Status Transition - Next
- [ ] UAT-012: Status Transition - Done
- [ ] UAT-013: Status Transition - Start
- [ ] UAT-014: Status Transition - Defer
- [ ] UAT-015: Status Transition - Wait (Delegation)
- [ ] UAT-016: Task Lookup by ID (Case Insensitive)
- [ ] UAT-017: Task Lookup by Title Substring
- [ ] UAT-018: Task Lookup - Not Found
- [ ] UAT-019: Delegated View
- [ ] UAT-020: Dashboard Generation
- [ ] UAT-021: Archive Single Task
- [ ] UAT-022: Archive Single Project
- [ ] UAT-023: Archive Tasks by Date
- [ ] UAT-024: Archive with Natural Language Date
- [ ] UAT-025: Error Handling - Invalid Date
- [x] ~~UAT-026: Error Handling - Invalid Priority~~ [DELETED]
- [ ] UAT-027: Error Handling - Vault Not Initialized

### Phase 3: Jira Integration
- [ ] UAT-028: Jira Configuration
- [ ] UAT-029: Jira Sync (Requires Live Jira)
- [ ] UAT-030: Jira Sync - Status Mapping
- [ ] UAT-031: Jira Sync - Auth Failure

### Phase 4: MCP Server
- [ ] UAT-032: MCP Server Startup
- [ ] UAT-033: MCP Tool - Add Task
- [ ] UAT-033a: MCP Tool - Add Task with Assign
- [ ] UAT-034: MCP Tool - List Tasks
- [ ] UAT-035: MCP Tool - Complete Task
- [ ] UAT-036: MCP Tool - Start Task
- [ ] UAT-037: MCP Tool - Defer Task
- [ ] UAT-038: MCP Tool - Get Dashboard
- [ ] UAT-039: MCP Tool - Jira Sync
- [ ] UAT-040: MCP Resources

### Phase 2: Obsidian Plugin
- [ ] UAT-041: Plugin Installation
- [ ] UAT-042: Plugin Settings
- [ ] UAT-043: Task List View
- [ ] UAT-044: Quick Add Modal
- [ ] UAT-045: Add to Inbox Modal
- [ ] UAT-046: Task Edit Modal
- [ ] UAT-047: Status Commands
- [ ] UAT-048: Inbox Processing View
- [ ] UAT-049: Manual Jira Sync Command

### Task File Format
- [ ] UAT-050: Task File Frontmatter
- [ ] UAT-051: Waiting-For Task Format
- [ ] UAT-052: Task with Subtasks
- [ ] UAT-053: Task with Location
- [ ] UAT-054: Task with Dependencies

### Workflows
- [ ] UAT-055: Daily Workflow - Morning
- [ ] UAT-056: Daily Workflow - Capture
- [ ] UAT-057: Daily Workflow - Status Updates
- [ ] UAT-058: Weekly Review Workflow

### Edge Cases
- [ ] UAT-059: Empty Vault Operations
- [ ] UAT-060: Special Characters in Task Title
- [ ] UAT-061: Unicode in Task Title
- [ ] UAT-062: Very Long Task Title
- [ ] UAT-063: Concurrent Operations
- [ ] UAT-064: Exit Codes
- [ ] UAT-065: No Stack Traces in Normal Use

---

## Notes

1. **Test Order:** Run Phase 1 tests first as they establish the foundation. Phase 3 and 4 can be run in parallel. Phase 2 (Obsidian plugin) requires manual testing in Obsidian.

2. **Test Environment:** Use a dedicated test vault separate from your production vault.

3. **Cleanup:** Between test runs, you may want to reset the test vault: `rm -rf test-obsidian-vault/aio-dev && mkdir test-obsidian-vault/aio-dev && aio init test-obsidian-vault/aio-dev`

4. **Known Limitations:** Some features marked as "Not Started" in PROJECT_PLAN (dependency visualization, location navigation, subtask progress) are not included in this UAT.

5. **MCP Testing:** MCP tests (UAT-032 to UAT-040) require an MCP client. For manual testing, use Cursor or a test harness.
