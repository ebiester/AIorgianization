# Assumptions

This document lists assumptions made during implementation of the AIorgianization system.

## Environment Assumptions

1. **Python Version**: Python 3.12+ is available. The project uses modern Python features like type hints with `|` union syntax.

2. **Package Manager**: `uv` is the preferred package manager, but standard `pip` will also work with the generated `pyproject.toml`.

3. **Obsidian Vault**: Users have an existing Obsidian vault with a `.obsidian` directory. The CLI validates this before initialization.

## Design Assumptions

### Task Management

1. **Single User**: The system is designed for a single user (Eric). No multi-user authentication or permissions are implemented.

2. **Task IDs**: 4-character alphanumeric IDs are sufficient. With 32^4 (~1 million) combinations, collisions are unlikely with <10,000 active tasks.

3. **Status Flow**: Tasks follow a GTD-inspired workflow:
   - `inbox` → `next` | `waiting` | `scheduled` | `someday`
   - Any status → `completed`
   - No backwards transitions from `completed` are implemented

4. **File Naming**: Task files are named `YYYY-MM-DD-slug.md` where the date is the creation date. This provides natural chronological ordering.

5. **Completed Tasks**: Completed tasks are organized by year/month (`Completed/2024/01/`) for better long-term organization.

### Vault Structure

1. **AIO Directory**: All AIorgianization content lives under `AIO/` in the vault. This keeps it separate from other vault content.

2. **Archive Structure**: The archive mirrors the main structure (`Archive/Tasks/Inbox/`, etc.) to preserve organizational context.

3. **Config Location**: Configuration lives in `.aio/config.yaml` which is excluded from git by default (users should add to `.gitignore`).

### Date Handling

1. **Natural Language**: The `dateparser` library handles natural language date parsing. It prefers future dates for ambiguous inputs like "Monday".

2. **Time Zones**: All dates are stored in local timezone without explicit timezone info. The system assumes users work in a single timezone.

3. **ISO Format**: Dates in frontmatter are stored as ISO 8601 strings (`YYYY-MM-DD` for dates, full ISO for datetimes).

### CLI Behavior

1. **Interactive Terminal**: The CLI assumes an interactive terminal with color support. Rich formatting may not display correctly in non-TTY environments.

2. **Error Handling**: Errors are displayed user-friendly without stack traces in normal mode. Use `--debug` for full traces.

3. **Exit Codes**:
   - `0` = success
   - `1` = error
   - `2` = usage error (handled by Click)

### MCP Server

1. **Stdio Transport**: The MCP server uses stdio transport, which is the standard for local MCP servers with Cursor/Claude Code.

2. **Lazy Initialization**: Services are lazily initialized to avoid vault discovery issues at import time.

3. **No Authentication**: The MCP server has no authentication as it's designed for local use only.

### Jira Integration (Future)

1. **Import Only**: Initial implementation only imports from Jira, not bidirectional sync. Jira is treated as the source of truth.

2. **API Token**: Jira authentication uses API tokens, stored in environment variables (`JIRA_API_TOKEN`).

## Data Format Assumptions

### Frontmatter

1. **YAML Standard**: Frontmatter uses standard YAML. Complex values like wikilinks are stored as strings.

2. **Wikilinks**: Project and person references use Obsidian wikilink syntax (`[[Projects/Name]]`). These are stored as literal strings.

3. **Optional Fields**: Optional frontmatter fields are omitted entirely when not set (not set to `null`).

### Markdown Content

1. **Title from H1**: Task titles are extracted from the first H1 heading (`# Title`). If absent, the filename is used.

2. **Body Structure**: The body typically contains `## Notes` and `## Subtasks` sections, but any markdown is valid.

3. **Subtasks**: Subtasks are standard markdown checkboxes (`- [ ]`). No special parsing is implemented for tracking completion.

## Dependencies

1. **MCP SDK**: Uses the official `mcp` Python SDK. The API is expected to be stable.

2. **Pydantic v2**: Uses Pydantic v2 for data validation. V1 syntax is not supported.

3. **Frontmatter Library**: Uses `python-frontmatter` for YAML frontmatter parsing, not the `pyyaml` library directly.

## Testing

1. **Temporary Vaults**: Tests create temporary vaults using pytest's `tmp_path` fixture. No real vaults are modified.

2. **No Network**: Tests don't require network access. Jira integration tests would need mocking (not implemented).

3. **Coverage Target**: 90%+ coverage is the goal for `services/` and `utils/`, but not enforced by CI.

## Obsidian Plugin Assumptions

### Architecture

1. **TypeScript Only**: The plugin is written in TypeScript, compiled to a single `main.js` bundle. No runtime TypeScript dependencies.

2. **Obsidian API**: Uses the official Obsidian Plugin API (`obsidian` npm package). Targets Obsidian 1.0.0+ for broad compatibility.

3. **esbuild Bundler**: Uses esbuild for fast bundling, following Obsidian's recommended plugin setup.

4. **No External Dependencies**: Avoids heavy npm dependencies. YAML parsing uses Obsidian's built-in `parseYaml`/`stringifyYaml` methods.

### File Operations

1. **Obsidian Vault Adapter**: All file operations use Obsidian's `Vault` API (`vault.read()`, `vault.create()`, `vault.modify()`) rather than Node.js `fs`. This ensures compatibility with Obsidian Sync and mobile.

2. **Atomic Writes**: File updates use Obsidian's atomic write operations. The plugin doesn't implement its own temp-file-rename pattern.

3. **File Events**: The plugin listens to Obsidian's file change events to refresh views when files are modified externally (e.g., by the CLI or Obsidian Sync).

### Date Handling

1. **No dateparser Library**: Unlike the Python CLI, the plugin uses simpler date parsing. Natural language dates are limited to relative terms ("today", "tomorrow", "+3d") and ISO dates.

2. **Browser Date API**: Uses native JavaScript `Date` for date manipulation. No moment.js or date-fns dependency.

### UI Components

1. **Native Obsidian Components**: Uses Obsidian's built-in UI components (`Modal`, `ItemView`, `Setting`) for consistent look and feel.

2. **No React/Vue**: The plugin uses vanilla TypeScript with Obsidian's native component system, not a UI framework.

3. **Mobile Support**: Views are responsive but optimized for desktop. Mobile Obsidian support is secondary.

### ID Generation

1. **Same Algorithm**: Uses the same ID generation algorithm as the Python CLI (4 chars from 32-char set: `23456789ABCDEFGHJKLMNPQRSTUVWXYZ`).

2. **Collision Check**: Scans existing task files to avoid ID collisions, same as CLI behavior.

### Settings Storage

1. **Obsidian Data**: Plugin settings use Obsidian's `loadData()`/`saveData()` API, stored in `.obsidian/plugins/aio/data.json`.

2. **No Shared Config**: Plugin settings are separate from CLI's `.aio/config.yaml`. Both tools discover the vault structure independently.

### Views

1. **ItemView Extension**: Task List and Inbox views extend Obsidian's `ItemView` class and appear in leaf panes.

2. **Auto-Refresh**: Views refresh automatically when task files change, using Obsidian's `metadataCache` events.

3. **Single Instance**: Only one instance of each view type is allowed at a time.

### Modals

1. **Modal Extension**: Quick Add and Task Edit modals extend Obsidian's `Modal` class.

2. **Form Validation**: Basic client-side validation (required fields, date format) with inline error messages.

3. **No Autosave**: Changes in modals require explicit save. No autosave or debounced saving.

### Commands

1. **Command Palette**: All commands are registered with Obsidian's command palette (`addCommand()`).

2. **No Default Hotkeys**: Commands are registered without default hotkeys. Users can assign hotkeys in Obsidian settings.

3. **Context Awareness**: Some commands (like "complete task") operate on the currently open file if it's a task.

### Performance

1. **Lazy Loading**: Task lists are loaded on-demand when views are opened, not at plugin startup.

2. **No Caching**: No custom caching layer. Relies on Obsidian's `metadataCache` for frontmatter access.

3. **Reasonable Scale**: Optimized for hundreds of active tasks, not tens of thousands.

## Not Implemented (Deferred)

The following features mentioned in the PRD are not implemented in this initial version:

1. **Jira Sync**: Jira integration is stubbed but not fully implemented. Would require additional configuration.

2. **Weekly Review**: The guided review wizard is deferred to a later plugin release.

3. **Recurring Tasks**: No recurrence support is implemented.

4. **Time Tracking**: Time estimates are stored but not tracked or reported on.

5. **Full-text Search**: Search is by ID or title substring only, not full content search.

6. **Context Packs**: The structure exists but no special handling for context pack content is implemented beyond file reading.

7. **Kanban View**: Visual board view is deferred to a later plugin release.

8. **Dependency Graph**: Visual dependency visualization is deferred.

9. **Drag and Drop**: Drag-and-drop reordering and status changes are deferred.

## Configuration Defaults

1. **Default Vault**: If `AIO_VAULT_PATH` is not set, the CLI walks up from CWD looking for `.obsidian/`.

2. **Default Status**: New tasks default to `inbox` status.

3. **No Default Project**: Tasks are not assigned to a project unless explicitly specified.

## Platform Support

1. **macOS/Linux**: Primary development and testing is on macOS. Linux should work but is less tested.

2. **Windows**: Not explicitly tested. Path handling uses `pathlib` which should be cross-platform.

3. **Obsidian Sync**: Compatible with Obsidian Sync since all data is in standard markdown files.
