# Product Requirements Document: AIorgianization

## Overview

AIorgianization is a personal task and deadline management system designed for engineering managers overseeing multiple teams. It combines GTD (Getting Things Done) and BASB (Building a Second Brain) methodologies with modern tooling to provide a unified system for tracking personal work, delegated tasks, and team deadlines.

## Problem Statement

Engineering managers face unique productivity challenges:

1. **Multiple deadline streams**: Personal commitments, deadlines given to direct reports, and team-level milestones all compete for attention
2. **Tool fragmentation**: Jira tracks team work, personal notes live in Obsidian/Notion, and todos scatter across apps
3. **Context switching**: Moving between strategic planning and tactical execution requires different views of the same work
4. **Delegation tracking**: "Waiting for" items easily fall through cracks when not systematically tracked
5. **Project decomposition**: Vague initiatives need breakdown into concrete next actions, ideally with AI assistance

Existing tools (Todoist, Things, OmniFocus) are designed for individual contributors, not managers who must track work across people and teams.

## Target User

**Primary persona**: Engineering Manager

- Manages 2-4 teams (5-20 direct/indirect reports)
- Familiar with GTD concepts (inbox zero, next actions, weekly review)
- Uses Obsidian or similar for notes and documentation
- Team uses Jira for sprint/project tracking
- Comfortable with command-line tools
- Wants AI assistance for task breakdown and prioritization

## Goals

1. **Unified view**: See all deadlines (personal, delegated, team) in one place
2. **Fast capture**: Add tasks in <5 seconds from terminal
3. **Smart organization**: GTD-style workflow with contexts, projects, and reviews
4. **Integration**: Pull from Jira, reference Obsidian notes
5. **AI-powered**: Claude helps break down projects and suggests prioritization
6. **Visual dashboard**: Obsidian plugin for daily/weekly planning and reviews

## Non-Goals

- Replacing Jira for team sprint management
- Full calendar/scheduling functionality
- Mobile app (CLI + web dashboard is sufficient)
- Multi-user collaboration (this is a personal tool)
- Real-time sync across devices (local-first is acceptable)

## Features

### P0: Core Task Management (Phase 1) ✓

| Feature | Description | Status |
|---------|-------------|--------|
| Vault init | `aio init <vault-path>` creates AIO directory structure | Done |
| Quick add | `aio add "Task" -d tomorrow` | Done |
| Task listing | Filter by status, project, due date | Done |
| Status transitions | inbox → next → waiting → completed | Done |
| Waiting-for | Track tasks delegated to others | Done |
| Someday/maybe | Defer non-urgent items | Done |
| Natural dates | "tomorrow", "next monday", "in 3 days" | Done |
| Archiving | Archive tasks, projects, areas, people | Done |
| Date-based archive | `aio archive tasks --before <date>` | Done |

### P0: Project & Team Structure (Phase 2) ✓

| Feature | Description | Status |
|---------|-------------|--------|
| Projects | Group tasks under projects with links, timeline, health | Done |
| Teams | Define teams and members | Done (via Person model) |
| People | Track who you delegate to | Done |
| Delegated view | See all tasks you've given to others | Done (`aio list waiting`) |
| Morning dashboard | Daily view: due today, due soon, waiting-for, team load | Done |
| Team load view | See task counts per person, flag overload (>5 items, >2 P1s) | Planned |

### P1: Obsidian Plugin (Phase 3) ✓

| Feature | Description | Status |
|---------|-------------|--------|
| Task list view | Custom pane showing tasks by status | Done |
| Quick add modal | Fast task entry via command palette | Done |
| Inbox processing | GTD clarify/organize workflow | Done |
| Waiting-for view | Delegated items grouped by person | Not Started |
| Weekly review | Guided review wizard | Not Started |
| Task editing | Modal to edit all task fields | Done |
| Status commands | Complete, start, defer via commands | Done |
| Task dependencies | Link tasks as blockers/blocked-by | Done (model only) |
| Dependency visualization | See blocked tasks and blockers in views | Not Started |
| Location linking | Connect task to file path, line, or URL in project | Done (model only) |
| Location navigation | Click to open file/URL from task view | Not Started |
| Subtask progress | Track and display completion of subtasks within tasks | Not Started |
| Template system | Customizable templates for tasks, projects, people from template directory | Not Started |
| Jira sync | Background sync with status bar indicator | Not Started |

#### Obsidian Plugin Detailed Requirements

**Purpose:** Provide visual interface for viewing, editing, and organizing tasks within Obsidian. Tasks stored as markdown files in the vault. CLI available for quick capture when not in Obsidian.

**Views (Custom Panes):**

| View | Purpose |
|------|---------|
| Task List | Main view showing tasks, filterable by status/project |
| Inbox | Process unclarified items one-by-one with action buttons |
| Waiting For | Delegated items grouped by person with days-waiting |
| Weekly Review | Guided wizard: inbox → projects → waiting → someday |

**Commands (Command Palette):**

| Command | Action |
|---------|--------|
| AIo: Add task | Open quick add modal |
| AIo: Add to inbox | Minimal modal, just title |
| AIo: Complete task | Complete current/selected task |
| AIo: Start task | Move to Next, set in-progress |
| AIo: Defer task | Move to Someday |
| AIo: Move to waiting | Set waiting status, prompt for person |
| AIo: Open task list | Show task list pane |
| AIo: Start weekly review | Launch review wizard |
| AIo: Sync Jira | Trigger manual sync |

**Quick Add Modal:**
- Title input with natural language parsing
- Shows preview: "Due: tomorrow"
- Keyboard: Enter to save, Esc to cancel
- Optional fields expandable (project, notes)

**Task Edit Modal:**
- All frontmatter fields editable
- Wikilink pickers for project and person
- Due date with natural language
- Delete with confirmation

**Task Display (in views):**
- Checkbox for completion
- Title (click to open file)
- Due date (relative, red if overdue)
- Project link
- Person link (if delegated)

**Right-Click Context Menu:**
- Complete
- Start working
- Defer to someday
- Move to waiting...
- Edit details...
- Open in editor

**Settings Tab:**
- Folder paths (Tasks, Projects, People, etc.)
- Default settings
- Jira configuration (URL, email, projects)
- Sync interval
- Completed task archiving (by month/year)
- Template directory path (default: `AIO/Templates/`)
- Template selection for each entity type (task, project, person, etc.)

**Template Customization:**
- Templates stored as markdown files in configurable template directory
- Each template contains frontmatter defaults and body content
- Template selection when creating new items via modal or CLI
- Templates support Obsidian's template variables ({{date}}, {{time}}, etc.)
- Default templates provided on init, user can customize or add new ones

### P1: Jira Integration (Phase 4) ✓

| Feature | Description | Status |
|---------|-------------|--------|
| Jira import | Sync assigned issues to vault as task files | Done |
| Status mapping | Map Jira statuses to task folders | Done |
| Automatic sync | Background sync at configurable interval | Not Started |
| Manual sync | Command to trigger immediate sync | Done |
| Conflict handling | Jira wins (team system of record) | Done |

### P2: AI Features (Phase 5) ✓

| Feature | Description | Status |
|---------|-------------|--------|
| Claude skill | Add tasks via Claude Code | Done (MCP tools) |
| MCP server | Structured API for Claude | Done |
| Task breakdown | Decompose projects into actions | Not Started |
| Context injection | Use Obsidian notes in breakdown | Done (context packs) |
| Priority suggestions | AI-assisted daily planning | Not Started |

### P2: Polish (Phase 6)

| Feature | Description | Status |
|---------|-------------|--------|
| Recurrence | Repeating tasks (daily standup, weekly review) | Planned |
| Time estimates | Track estimated vs actual time | Planned |
| Search | Full-text search across tasks | Planned |
| Export | Markdown/JSON export for backup | Planned |

## User Stories

### Task Capture
> As an EM, I want to capture tasks instantly from terminal so that ideas don't escape during coding sessions.

**Acceptance criteria:**
- `aio add "Review John's PR"` creates task in <1 second
- Natural language dates parse correctly
- Task appears in inbox by default

### Delegation Tracking
> As an EM, I want to see all tasks I've delegated so that I can follow up appropriately in 1:1s.

**Acceptance criteria:**
- `aio delegated` shows all waiting-for items grouped by person
- Each item shows days since delegated
- Can filter by team or person

### Weekly Review
> As an EM, I want a guided weekly review so that I maintain GTD discipline.

**Acceptance criteria:**
- Plugin review wizard walks through: inbox → projects → waiting-for → someday
- Can process inbox items one-by-one
- Review marked complete with timestamp

### AI Task Breakdown
> As an EM, I want Claude to help break down vague projects using my notes as context.

**Acceptance criteria:**
- `aio breakdown "Q4 Platform Migration"` triggers AI analysis
- AI reads linked Obsidian notes for context
- Outputs concrete next actions with estimates
- User confirms before tasks are created

### Jira Integration
> As an EM, I want my Jira assignments to appear in my task list so I have one source of truth.

**Acceptance criteria:**
- `aio sync jira` imports assigned issues
- Status changes sync bidirectionally
- Conflicts flagged for manual resolution
- Can filter local list to show/hide Jira items

## Use Cases (Test Scenarios)

These use cases are designed to drive automated test development.

### UC-001: Quick Task Capture

**Preconditions:** Vault initialized with AIO structure, CLI available

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Review PR #123"` | Task created with status=inbox, taskType=personal |
| 2 | Run `aio add "Call vendor" -d tomorrow` | Task created with dueDate=tomorrow 00:00:00 |
| 3 | Run `aio add "Urgent fix" -d today` | Task created with dueDate=today |
| 4 | Run `aio list inbox` | All three tasks appear in inbox list |

**Test assertions:**
- Task ID is valid 4-char alphanumeric (e.g., `AB2C`)
- createdAt and updatedAt are set to current timestamp
- Default status is "inbox"
- Default taskType is "personal"

### UC-002: Task Status Transitions

**Preconditions:** Task exists in inbox

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio next <id>` | status changes to "next" |
| 2 | Run `aio start <id>` | status changes to "in_progress" |
| 3 | Run `aio done <id>` | status=completed, completedAt set |
| 4 | Run `aio list` | Task no longer appears (completed filtered) |
| 5 | Run `aio list all --completed` | Task appears with completed status |

**Test assertions:**
- Each transition updates `updatedAt`
- `completedAt` only set on completion
- Completed tasks excluded from default list

### UC-003: Defer to Someday/Maybe

**Preconditions:** Task exists in inbox or next_action

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio defer <id>` | status changes to "someday_maybe" |
| 2 | Run `aio list` | Task not in default list |
| 3 | Run `aio list someday` | Task appears |
| 4 | Run `aio next <id>` | status changes to "next" |

**Test assertions:**
- Deferred tasks hidden from default view
- Can reactivate deferred tasks

### UC-004: Waiting-For Delegation

**Preconditions:** Task file exists, Person file "Sarah.md" exists in vault

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio wait <id> Sarah` | status=waiting_for, assignedToId=Sarah's ID |
| 2 | Run `aio list waiting` | Task appears with Sarah attribution |
| 3 | Run `aio delegated` | Task appears under Sarah |
| 4 | Run `aio done <id>` | Task completed |

**Test assertions:**
- assignedToId correctly linked to person
- Waiting-for list groups by person
- Delegated view shows days-since-delegated

### UC-005: Natural Language Date Parsing

**Preconditions:** Current date is known (e.g., Monday 2024-01-15)

| Input | Expected dueDate |
|-------|------------------|
| `tomorrow` | 2024-01-16 |
| `next monday` | 2024-01-22 |
| `in 3 days` | 2024-01-18 |
| `friday` | 2024-01-19 |
| `end of week` | 2024-01-21 (Sunday) |
| `2024-02-01` | 2024-02-01 |

**Test assertions:**
- All formats parse without error
- Invalid dates return parse error, task not created

### UC-006: Task Lookup by ID

**Preconditions:** Task exists with ID `AB2C`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio done AB2C` | Task found and completed |
| 2 | Run `aio done ab2c` | Task found (case-insensitive) |
| 3 | Run `aio done "Review PR"` | Task found by title match |
| 4 | Run `aio done ZZZZ` | Error: "Task not found" |

**Test assertions:**
- 4-char ID match works (case-insensitive)
- Title substring match works (case-insensitive)
- No match returns clear error

### UC-007: Project Task Organization

**Preconditions:** Vault initialized, no projects exist yet

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Design API" -p "Q4 Migration"` | Error: "Project not found" with `--create-project` suggestion |
| 2 | Run `aio add "Design API" -p "Q4 Migration" --create-project` | Project created in AIO/Projects/, task linked |
| 3 | Run `aio add "Review spec" -p "Q4 Migration"` | Task linked (project now exists) |
| 4 | Run `aio add "Typo task" -p "Q4 Migartion"` | Error with fuzzy suggestion: "Did you mean? Q4-Migration" |
| 5 | Run `aio list "Q4 Migration"` | Both tasks appear under project |
| 6 | Run `aio project show "Q4 Migration"` | Project details + all tasks shown |

**Test assertions:**
- Project validation errors by default for non-existent projects
- Fuzzy matching suggests similar project names on typos
- `--create-project` flag creates project with template in AIO/Projects/
- projectId correctly set after validation passes
- Project filter returns only project tasks
- Project view shows task count and statuses

### ~~UC-008: Priority Filtering~~ [REMOVED]

*Feature removed - priority not implemented.*

### UC-009: Overdue Detection

**Preconditions:** Task exists with dueDate = yesterday

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio list overdue` | Task appears |
| 2 | Run `aio list today` | Task appears (overdue included in today) |
| 3 | Complete the task | Task no longer in overdue |

**Test assertions:**
- Overdue = dueDate < today AND status not completed/archived
- Overdue tasks included in "today" view
- Visual indicator (red) for overdue

### UC-010: Jira Sync (Import)

**Preconditions:** Jira configured, issues assigned to user exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio sync jira` | Issues imported as tasks |
| 2 | Check imported task | jiraIssueKey set, title matches |
| 3 | Run `aio sync jira` again | No duplicates created |
| 4 | Update issue in Jira | Local task updated on next sync |

**Test assertions:**
- jiraIssueKey is unique constraint
- Sync is idempotent
- Status mapping applied correctly
- Sync log records success/failure

### UC-011: Obsidian Note Linking

**Preconditions:** Obsidian vault configured, note exists at `1-Projects/Migration.md`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Review migration plan" --note "1-Projects/Migration.md"` | obsidianNotePath set |
| 2 | Run `aio show <id>` | Note path displayed |
| 3 | Run `aio breakdown <id>` | Note content loaded as AI context |

**Test assertions:**
- Note path stored correctly
- Note content readable from vault
- Missing note handled gracefully

### UC-012: Weekly Review Workflow

**Preconditions:** Inbox has items, projects exist, waiting-for items exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start weekly review | Inbox items presented first |
| 2 | Process each inbox item | Item moved to appropriate list |
| 3 | Review all projects | Each project checked for next action |
| 4 | Review waiting-for | Each item checked for follow-up |
| 5 | Complete review | weeklyReview record created with completedAt |

**Test assertions:**
- Review tracks which sections completed
- Review can be resumed if interrupted
- Completion timestamp recorded

### UC-013: AI Task Breakdown

**Preconditions:** Task exists, Obsidian note linked

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio breakdown <id>` | AI analyzes task + note context |
| 2 | AI suggests subtasks | List of proposed tasks shown |
| 3 | User confirms | Subtasks created, linked to parent |
| 4 | User rejects one | Only confirmed tasks created |

**Test assertions:**
- Subtasks have parentTaskId set
- Subtasks inherit project from parent
- Each subtask is actionable (has verb)

### UC-014: MCP Tool Invocation

**Preconditions:** MCP server running

| Tool Call | Expected Result |
|-----------|-----------------|
| `aio_add_task({title: "Test", due: "tomorrow"})` | Task created, ID returned |
| `aio_list_tasks({status: "inbox"})` | Array of inbox tasks returned |
| `aio_complete_task({id: "..."})` | Task completed, confirmation returned |
| `aio_breakdown({id: "...", noteContext: "..."})` | Subtask suggestions returned |

**Test assertions:**
- MCP responses match schema
- Errors return structured error objects
- Tool descriptions accurate

### UC-015: Vault Initialization

**Preconditions:** Obsidian vault exists, AIO structure not yet created

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio init /path/to/vault` | AIO directory structure created |
| 2 | Check vault/AIO/ | All folders exist (Tasks/, Projects/, People/, etc.) |
| 3 | Check vault/AIO/Tasks/ | Status subfolders exist (Inbox/, Next/, Waiting/, etc.) |
| 4 | Check vault/.aio/ | Config directory created |

**Test assertions:**
- AIO directory structure created with correct layout
- Idempotent (running again doesn't break)
- Works with existing Obsidian vault (.obsidian folder present)

### UC-016: Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Invalid date format | Error message, task not created |
| Non-existent task ID | "Task not found" error |
| Vault not initialized | Clear error with `aio init` instructions |
| Jira auth failure | Clear error with remediation steps |

**Test assertions:**
- All errors are user-friendly (no stack traces in normal use)
- Exit codes: 0=success, 1=error
- Errors written to stderr

### UC-017: Obsidian Plugin - View Tasks

**Preconditions:** Plugin enabled, task files exist in vault

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open Task List view | Dashboard loads with summary counts |
| 2 | Click "Inbox (5)" | Filter to inbox, 5 tasks shown |
| 3 | Click a task | Task detail modal opens |
| 4 | Click outside modal | Modal closes |

**Test assertions:**
- Summary counts match task files in vault
- Task list renders within 500ms
- Modal opens/closes without page reload
- Task data matches markdown file content

### UC-018: Obsidian Plugin - Edit Task Inline

**Preconditions:** Task file exists, plugin loaded

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click task title | Title becomes editable input |
| 2 | Change title, press Enter | Title saved, input closes |
| 3 | Click due date | Date picker appears |
| 4 | Select new date | Due date updates |

**Test assertions:**
- Changes persist to task file
- UI updates optimistically (before API response)
- Rollback on API error with error message
- updatedAt timestamp changes

### UC-019: Obsidian Plugin - Edit Task Modal

**Preconditions:** Task exists with all fields populated

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click task to open modal | Modal shows all task fields |
| 2 | Edit description | Textarea accepts multiline text |
| 3 | Change project dropdown | Project selection updates |
| 4 | Click Save (or Cmd+Enter) | Modal closes, task updated |
| 5 | Reopen task | All changes persisted |

**Test assertions:**
- All fields editable
- Validation errors shown inline
- Save disabled while submitting
- Keyboard shortcuts work (Esc=close, Cmd+Enter=save)

### UC-020: Obsidian Plugin - Quick Add

**Preconditions:** Plugin loaded in Obsidian

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Press `/` or click quick add bar | Input focused |
| 2 | Type "Review PR -d tomorrow" | Preview shows parsed task |
| 3 | Press Enter | Task created, appears in list |
| 4 | Type invalid syntax | Preview shows error, submit disabled |

**Test assertions:**
- Same parsing as CLI
- Preview updates as user types
- New task appears without page reload
- Input clears after successful add

### UC-021: Obsidian Plugin - Status Transitions

**Preconditions:** Task in inbox status

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Activate" button | Status → next_action |
| 2 | Click "Start" button | Status → in_progress |
| 3 | Click "Complete" button | Status → completed, task fades out |
| 4 | Navigate to completed view | Task appears there |

**Test assertions:**
- Status icon updates immediately
- Task moves to appropriate list
- Completed tasks hidden from default view
- Undo available for 5 seconds after complete

### UC-022: Obsidian Plugin - Bulk Actions

**Preconditions:** Multiple tasks exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click checkbox on 3 tasks | 3 tasks selected, bulk bar appears |
| 2 | Click "Select All" | All visible tasks selected |
| 3 | Click "Complete" in bulk bar | Confirmation dialog appears |
| 4 | Confirm | All selected tasks completed |
| 5 | Click "Undo" (within 5s) | Tasks restored to previous status |

**Test assertions:**
- Selection persists across scroll
- Bulk actions apply to all selected
- Confirmation required for destructive actions
- Undo works for bulk operations

### UC-023: Obsidian Plugin - Filtering

**Preconditions:** Tasks exist with various projects, dates

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Project: Migration" filter | Only Migration project tasks shown |
| 2 | Add "Due: This week" filter | Migration project tasks due this week |
| 3 | Check URL | URL contains filter params |
| 4 | Copy URL, open in new tab | Same filtered view loads |
| 5 | Click "Clear filters" | All tasks shown again |

**Test assertions:**
- Filters are AND-combined
- URL is bookmarkable
- Filter state persists on navigation
- Count updates to show "5 of 23 tasks"

### UC-024: Obsidian Plugin - Drag and Drop

**Preconditions:** Multiple tasks in next_action status

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Drag task to reorder | Task moves, order saves |
| 2 | Drag task to "Waiting" column | Task status changes to waiting_for |
| 3 | Drag task to project section | Task assigned to that project |

**Test assertions:**
- Drag preview shows task card
- Drop zones highlight on hover
- Order persists after refresh
- Status change triggers on cross-list drop

### UC-025: Obsidian Plugin - Weekly Review Flow

**Preconditions:** Inbox has items, projects exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/review` | Review wizard starts |
| 2 | Step 1: Inbox | Each inbox item shown with actions |
| 3 | Click "Next Action" on item | Item status changes, next item shown |
| 4 | Click "Defer" on item | Item goes to someday, next shown |
| 5 | All inbox processed | "Inbox Zero!" message, proceed to Step 2 |
| 6 | Step 2: Projects | Each project shown, "Has next action?" prompt |
| 7 | Complete all steps | Review record saved, summary shown |

**Test assertions:**
- Progress indicator shows current step
- Can skip steps
- Can go back to previous step
- Review completion timestamp saved
- "Last review: 3 days ago" shown on dashboard

### UC-026: Obsidian Plugin - Responsive Layout

**Preconditions:** Plugin loaded in Obsidian

| Viewport | Expected Layout |
|----------|-----------------|
| Desktop (>1024px) | Sidebar + main content side by side |
| Tablet (768-1024px) | Collapsible sidebar, full-width content |
| Mobile (<768px) | Bottom navigation, stacked cards |

**Test assertions:**
- All features accessible on mobile
- Touch targets minimum 44px
- No horizontal scroll
- Quick add accessible on all sizes

### UC-027: Obsidian Plugin - Keyboard Navigation

**Preconditions:** Plugin loaded in Obsidian with task list

| Shortcut | Action |
|----------|--------|
| `/` or `Cmd+K` | Focus quick add |
| `j` / `k` | Move selection down/up |
| `Enter` | Open selected task |
| `Esc` | Close modal / clear selection |
| `c` | Complete selected task |
| `e` | Edit selected task |
| `d` | Defer selected task |
| `?` | Show keyboard shortcuts help |

**Test assertions:**
- Shortcuts work when no input focused
- Visual indicator shows selected task
- Help modal lists all shortcuts

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Capture speed | <5 seconds | Time from thought to saved task |
| Inbox zero | Daily | Zero inbox items at end of day |
| Weekly review | Weekly | Review completed each week |
| Delegation visibility | 100% | All delegated items tracked |
| Integration adoption | 80% | Jira items synced, notes linked |

## Technical Constraints

1. **Local-first**: All data in markdown files within Obsidian vault
2. **CLI primary**: Must work entirely from terminal
3. **Python + TypeScript**: Python for CLI/MCP, TypeScript for Obsidian plugin
4. **No account required**: No cloud services, no login
5. **Portable**: Markdown files in vault, git-friendly, easy backup

## Open Questions

1. **Calendar integration**: Should scheduled tasks sync to calendar?
2. **Mobile access**: Is web dashboard on localhost sufficient, or need remote access?
3. **Team visibility**: Should there be a read-only view for sharing with teams?
4. **Obsidian plugin**: Build plugin or just read vault directly?

## Appendix: GTD Workflow Reference

```
CAPTURE → CLARIFY → ORGANIZE → REFLECT → ENGAGE

Inbox: Unclarified items
  ↓ (Is it actionable?)
  ├─ No → Trash / Reference / Someday-Maybe
  └─ Yes → (What's the next action?)
       ├─ <2 min → Do it now
       ├─ Delegate → Waiting-for
       └─ Defer → Next Actions / Calendar

Weekly Review:
1. Get inbox to zero
2. Review next actions lists
3. Review waiting-for list
4. Review someday-maybe
5. Review projects (do they have next actions?)
```

## Appendix: PARA Reference

```
PARA = Projects, Areas, Resources, Archives

Projects: Active with deadline/outcome
  - Q4 Platform Migration
  - Hiring: Senior Engineer

Areas: Ongoing responsibilities (no end date)
  - Team Alpha management
  - 1:1s
  - Architecture decisions

Resources: Reference material
  - Technical documentation
  - Process guides

Archives: Inactive items
  - Completed projects
  - Old resources
```
