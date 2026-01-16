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
6. **Visual dashboard**: Web UI for daily/weekly planning and reviews

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
| Quick add | `aio add "Task" -d tomorrow -P P1` | Done |
| Task listing | Filter by status, project, context, due date | Done |
| Status transitions | inbox → next_action → in_progress → completed | Done |
| Waiting-for | Track tasks delegated to others | Done |
| Someday/maybe | Defer non-urgent items | Done |
| Natural dates | "tomorrow", "next monday", "in 3 days" | Done |
| Priority levels | P1-P4 (Eisenhower matrix) | Done |

### P0: Project & Team Structure (Phase 2)

| Feature | Description | Status |
|---------|-------------|--------|
| Projects | Group tasks under projects with outcomes | Planned |
| Teams | Define teams and members | Planned |
| People | Track who you delegate to | Planned |
| Contexts | GTD contexts (@work, @1on1, @deep-work) | Planned |
| Delegated view | See all tasks you've given to others | Planned |

### P1: Obsidian Plugin (Phase 3)

| Feature | Description | Status |
|---------|-------------|--------|
| Task list view | Custom pane showing tasks by status | Planned |
| Quick add modal | Fast task entry via command palette | Planned |
| Inbox processing | GTD clarify/organize workflow | Planned |
| Waiting-for view | Delegated items grouped by person | Planned |
| Weekly review | Guided review wizard | Planned |
| Task editing | Modal to edit all task fields | Planned |
| Status commands | Complete, start, defer via commands | Planned |
| Jira sync | Background sync with status bar indicator | Planned |

#### Obsidian Plugin Detailed Requirements

**Purpose:** Provide visual interface for viewing, editing, and organizing tasks within Obsidian. Tasks stored as markdown files in the vault. CLI available for quick capture when not in Obsidian.

**Views (Custom Panes):**

| View | Purpose |
|------|---------|
| Task List | Main view showing tasks, filterable by status/project/context |
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
- Shows preview: "Due: tomorrow, Priority: P1"
- Keyboard: Enter to save, Esc to cancel
- Optional fields expandable (project, context, notes)

**Task Edit Modal:**
- All frontmatter fields editable
- Wikilink pickers for project and person
- Context multi-select (existing + new)
- Due date with natural language
- Delete with confirmation

**Task Display (in views):**
- Checkbox for completion
- Title (click to open file)
- Priority badge (colored)
- Due date (relative, red if overdue)
- Project link
- Person link (if delegated)
- Context tags

**Right-Click Context Menu:**
- Complete
- Start working
- Defer to someday
- Move to waiting...
- Edit details...
- Open in editor

**Settings Tab:**
- Folder paths (Tasks, Projects, People, etc.)
- Default priority and context
- Jira configuration (URL, email, projects)
- Sync interval
- Completed task archiving (by month/year)

### P1: Jira Integration (Phase 4)

| Feature | Description | Status |
|---------|-------------|--------|
| Jira import | Sync assigned issues to vault as task files | Planned |
| Status mapping | Map Jira statuses to task folders | Planned |
| Automatic sync | Background sync at configurable interval | Planned |
| Manual sync | Command to trigger immediate sync | Planned |
| Conflict handling | Jira wins (team system of record) | Planned |

### P2: AI Features (Phase 5)

| Feature | Description | Status |
|---------|-------------|--------|
| Claude skill | Add tasks via Claude Code | Planned |
| MCP server | Structured API for Claude | Planned |
| Task breakdown | Decompose projects into actions | Planned |
| Context injection | Use Obsidian notes in breakdown | Planned |
| Priority suggestions | AI-assisted daily planning | Planned |

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
- Web UI walks through: inbox → projects → waiting-for → someday
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

**Preconditions:** Database initialized, CLI available

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Review PR #123"` | Task created with status=inbox, taskType=personal |
| 2 | Run `aio add "Call vendor" -d tomorrow` | Task created with dueDate=tomorrow 00:00:00 |
| 3 | Run `aio add "Urgent fix" -P P1 -d today` | Task created with priority=P1, dueDate=today |
| 4 | Run `aio list inbox` | All three tasks appear in inbox list |

**Test assertions:**
- Task ID is valid ULID
- createdAt and updatedAt are set to current timestamp
- Default status is "inbox"
- Default taskType is "personal"

### UC-002: Task Status Transitions

**Preconditions:** Task exists in inbox

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio activate <id>` | status changes to "next_action" |
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
| 4 | Run `aio activate <id>` | status changes to "next_action" |

**Test assertions:**
- Deferred tasks hidden from default view
- Can reactivate deferred tasks

### UC-004: Waiting-For Delegation

**Preconditions:** Task exists, Person "Sarah" exists in database

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

### UC-006: Task Lookup by Partial ID

**Preconditions:** Task exists with ID `01KF1TFK2QQ33H2FS3KBGVVZKM`

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio done GVVZKM` | Task found and completed |
| 2 | Run `aio done 01KF1TFK2QQ33H2FS3KBGVVZKM` | Task found (full ID) |
| 3 | Run `aio done "Review PR"` | Task found by title match |
| 4 | Run `aio done XXXXXX` | Error: "Task not found" |

**Test assertions:**
- 6-character suffix match works
- Full ULID match works
- Title substring match works (case-insensitive)
- No match returns clear error

### UC-007: Project Task Organization

**Preconditions:** Project "Q4 Migration" exists

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Design API" -p "Q4 Migration"` | Task linked to project |
| 2 | Run `aio list "Q4 Migration"` | Task appears under project |
| 3 | Run `aio project show "Q4 Migration"` | Project details + all tasks shown |

**Test assertions:**
- projectId correctly set
- Project filter returns only project tasks
- Project view shows task count and statuses

### UC-008: Priority Filtering

**Preconditions:** Tasks exist with P1, P2, P3, P4 priorities

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio list --priority P1` | Only P1 tasks shown |
| 2 | Run `aio list today` | Tasks sorted by priority (P1 first) |

**Test assertions:**
- Priority filter exact match
- Default sort order: priority → due date → created date

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

### UC-010: Context Assignment

**Preconditions:** Contexts "@work", "@1on1" exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run `aio add "Discuss promotion" -c @1on1` | Task linked to @1on1 context |
| 2 | Run `aio list @1on1` | Task appears |
| 3 | Run `aio list @work` | Task does not appear |

**Test assertions:**
- Multiple contexts can be assigned to one task
- Context filter is exact match on context name

### UC-011: Jira Sync (Import)

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

### UC-012: Obsidian Note Linking

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

### UC-013: Weekly Review Workflow

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

### UC-014: AI Task Breakdown

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

### UC-015: MCP Tool Invocation

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

### UC-016: Database Initialization

**Preconditions:** ~/.aio directory does not exist

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run any `aio` command | ~/.aio directory created |
| 2 | Check ~/.aio/aio.db | Database file exists |
| 3 | Check tables | All schema tables present |

**Test assertions:**
- Directory created with correct permissions
- Migrations applied automatically
- Idempotent (running again doesn't break)

### UC-017: Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Invalid date format | Error message, task not created |
| Non-existent task ID | "Task not found" error |
| Invalid priority value | "Invalid priority, use P1-P4" error |
| Database locked | Retry with backoff, then error |
| Jira auth failure | Clear error with remediation steps |

**Test assertions:**
- All errors are user-friendly (no stack traces in normal use)
- Exit codes: 0=success, 1=error
- Errors written to stderr

### UC-018: Obsidian Plugin - View Tasks

**Preconditions:** API server running, tasks exist in database

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/` | Dashboard loads with summary counts |
| 2 | Click "Inbox (5)" | Navigate to `/inbox`, 5 tasks shown |
| 3 | Click a task card | Task detail modal opens |
| 4 | Click outside modal | Modal closes |

**Test assertions:**
- Summary counts match database
- Task list renders within 500ms
- Modal opens/closes without page reload
- Task data matches database record

### UC-019: Obsidian Plugin - Edit Task Inline

**Preconditions:** Task exists, web UI loaded

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click task title | Title becomes editable input |
| 2 | Change title, press Enter | Title saved, input closes |
| 3 | Click priority badge | Priority dropdown appears |
| 4 | Select P1 | Priority updates immediately |
| 5 | Click due date | Date picker appears |
| 6 | Select new date | Due date updates |

**Test assertions:**
- Changes persist to database
- UI updates optimistically (before API response)
- Rollback on API error with error message
- updatedAt timestamp changes

### UC-020: Obsidian Plugin - Edit Task Modal

**Preconditions:** Task exists with all fields populated

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click task to open modal | Modal shows all task fields |
| 2 | Edit description | Textarea accepts multiline text |
| 3 | Change project dropdown | Project selection updates |
| 4 | Add context tag | Tag appears in list |
| 5 | Click Save (or Cmd+Enter) | Modal closes, task updated |
| 6 | Reopen task | All changes persisted |

**Test assertions:**
- All fields editable
- Validation errors shown inline
- Save disabled while submitting
- Keyboard shortcuts work (Esc=close, Cmd+Enter=save)

### UC-021: Obsidian Plugin - Quick Add

**Preconditions:** Web UI loaded on any page

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Press `/` or click quick add bar | Input focused |
| 2 | Type "Review PR -d tomorrow -P P1" | Preview shows parsed task |
| 3 | Press Enter | Task created, appears in list |
| 4 | Type invalid syntax | Preview shows error, submit disabled |

**Test assertions:**
- Same parsing as CLI
- Preview updates as user types
- New task appears without page reload
- Input clears after successful add

### UC-022: Obsidian Plugin - Status Transitions

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

### UC-023: Obsidian Plugin - Bulk Actions

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

### UC-024: Obsidian Plugin - Filtering

**Preconditions:** Tasks exist with various priorities, projects, dates

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click "Priority: P1" filter | Only P1 tasks shown |
| 2 | Add "Project: Migration" filter | P1 tasks in Migration project |
| 3 | Check URL | URL contains filter params |
| 4 | Copy URL, open in new tab | Same filtered view loads |
| 5 | Click "Clear filters" | All tasks shown again |

**Test assertions:**
- Filters are AND-combined
- URL is bookmarkable
- Filter state persists on navigation
- Count updates to show "5 of 23 tasks"

### UC-025: Obsidian Plugin - Drag and Drop

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

### UC-026: Obsidian Plugin - Weekly Review Flow

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

### UC-027: Obsidian Plugin - Responsive Layout

**Preconditions:** Web UI loaded

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

### UC-028: Obsidian Plugin - Keyboard Navigation

**Preconditions:** Web UI loaded with task list

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

1. **Local-first**: All data in SQLite on user's machine
2. **CLI primary**: Must work entirely from terminal
3. **TypeScript**: Maintainable by user long-term
4. **No account required**: No cloud services, no login
5. **Portable**: Single database file, easy backup

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
