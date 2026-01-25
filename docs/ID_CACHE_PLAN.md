# ID Cache + Read-Only Fallback Plan

## Findings (From Architectural + Code Review)

| # | Finding | Status | Priority |
|---|---------|--------|----------|
| 1 | IDs not unique across completed/archive | **FIXED** | - |
| 2 | File overwrite risk with identical slugs | **FIXED** | Critical |
| 3 | Daemon/CLI list defaults differ (Someday) | **FIXED** | Medium |
| 4 | Dataview queries use raw names vs slugged paths | **FIXED** | High |
| 5 | waitingOn link format inconsistent | **FIXED** | High |
| 6 | Title search ignores completed subfolders | **FIXED** | Medium |
| 7 | MCP cache never refreshes | **CONFIRMED (by design)** | Low |
| 8 | Archive metadata not written | **FIXED** | Medium |
| 9 | Daemon endpoint mismatch in docs | **FIXED** | Low |
| 10 | Plugin writes files in fallback mode | **CONFIRMED** | Medium |

### Finding Details

#### #1 - ID Uniqueness (FIXED)
- **Problem:** ID discovery ignored Completed/YYYY/MM and Archive trees, risking collisions over time.
- **Solution:** Implemented `IdIndexService` that scans all locations including completed subfolders and archive.
- **Files:** `aio/services/id_index.py`, `aio/services/id_service.py`

#### #2 - File Overwrite Risk (FIXED)
- **Problem:** `TaskService.create()`, `ProjectService.create()`, `PersonService.create()` don't check if file exists before writing.
- **Impact:** Creating two tasks with same title on same day silently overwrites the first.
- **Solution:** Added `if filepath.exists(): raise FileExistsError(...)` before `write_frontmatter()` in all three services.
- **Files fixed:**
  - `aio/services/task.py`
  - `aio/services/project.py`
  - `aio/services/person.py`
- **Test:** `tests/unit/test_task.py::test_create_task_duplicate_raises_error`

#### #3 - Daemon vs CLI List Defaults (FIXED)
- **Problem:** `VaultCache.list_tasks()` includes Someday tasks, but `TaskService.list_tasks()` excludes them.
- **Impact:** `aio list` shows different results depending on whether daemon is running.
- **Solution:** Updated `VaultCache.list_tasks()` to exclude both COMPLETED and SOMEDAY, matching TaskService.
- **Files fixed:** `aio/daemon/cache.py`

#### #4 - Dataview Query Format Mismatch (FIXED)
- **Problem:** Project/person templates generate Dataview queries using raw names, but tasks store slugified links.
- **Example:**
  - Query expects: `link("AIO/Projects/Q4 Migration")`
  - Task stores: `[[AIO/Projects/Q4-Migration]]`
- **Solution:** Added `get_slug()` utility to `aio/utils/__init__.py` and updated Dataview queries in project and person templates to use slugified names.
- **Files fixed:**
  - `aio/utils/__init__.py` - added shared `get_slug()` function
  - `aio/services/project.py` - Dataview queries now use `get_slug(name)`
  - `aio/services/person.py` - Dataview queries now use `get_slug(name)`

#### #5 - waitingOn Link Format Inconsistent (FIXED)
- **Problem:** Multiple formats used for person links:
  - `TaskService.wait()` creates: `[[People/{name}]]`
  - CLI/daemon creates: `[[AIO/People/{slug}]]`
  - Dataview queries expect: `[[AIO/People/{name}]]`
- **Solution:** Updated `TaskService.wait()` to use canonical format `[[AIO/People/{slug}]]`.
- **Files fixed:**
  - `aio/services/task.py` - wait() now emits `[[AIO/People/{slug}]]`
- **Test:** `tests/unit/test_task.py::test_wait_task` updated to verify format
- **Note:** Obsidian plugin (`obsidian-aio/src/modals/TaskEditModal.ts`) still needs updating for full consistency

#### #6 - Title Search Ignores Completed Subfolders (FIXED)
- **Problem:** `_find_tasks_by_title()` only searches base Completed folder, not YYYY/MM subfolders.
- **Contrast:** `_find_task_file_by_id()` correctly searches subfolders.
- **Solution:** Added subfolder iteration logic to `_find_tasks_by_title()` matching `_find_task_file_by_id()`.
- **Files fixed:** `aio/services/task.py`

#### #7 - MCP Cache Staleness (By Design)
- **Problem:** MCP server doesn't call `cache.start()`, so file watching is disabled.
- **Impact:** MCP returns stale data after external vault edits.
- **Note:** This is documented behavior ("non-watching cache since each request is stateless").
- **Potential fix:** Add optional `refresh()` call per request, or document limitation clearly.

#### #8 - Archive Metadata Not Written (FIXED)
- **Problem:** `ARCHITECTURE.md` promises `archived`, `archivedAt`, `archivedFrom` fields, but they're not written.
- **Solution:** Added archive metadata fields to Task model and populated them in `archive()` method.
- **Files fixed:**
  - `aio/models/task.py` - added `archived`, `archived_at`, `archived_from` fields and frontmatter serialization
  - `aio/services/task.py` - set fields in `archive()` method, read fields in `_read_task_file()`
- **Test:** `tests/unit/test_task.py::test_archive_task_sets_metadata`

#### #9 - Daemon Endpoint Naming (FIXED)
- **Problem:** `DAEMON_ARCHITECTURE.md` line 198 says `/tasks/{id}/wait`, implementation is `/tasks/{id}/delegate`.
- **Solution:** Updated documentation to match implementation.
- **Files fixed:** `docs/DAEMON_ARCHITECTURE.md` (line 198) - `/wait` → `/delegate`

#### #10 - Plugin Writes in Fallback Mode
- **Problem:** Obsidian plugin has full file write and ID generation capability when daemon is offline.
- **Impact:** Two sources of truth; potential ID collisions if plugin and daemon both generate IDs.
- **Files involved:**
  - `obsidian-aio/src/services/TaskService.ts` (lines 341-398, 64-90)
- **Fix:** See "Obsidian Plugin: Read-Only Fallback" section below.

---

## Completed Work

### ID Cache Implementation (Finding #1 - DONE)

**New files created:**
- `aio/services/id_index.py` - Core ID index service
- `aio/cli/index.py` - CLI commands (`aio index rebuild`, `aio index status`)
- `tests/unit/test_id_index.py` - 29 unit tests
- `tests/unit/test_id_service.py` - 6 unit tests
- `tests/integration/test_id_index.py` - 8 integration tests

**Modified files:**
- `aio/services/id_service.py` - Now uses IdIndexService
- `aio/cli/main.py` - Added `index` command group

**Features implemented:**
- Index stored at `.aio/id-index.json` (syncs with vault)
- Scans all locations: Tasks/*, Completed/YYYY/MM, Archive/Tasks/*
- Fingerprint-based staleness detection using directory mtimes
- Atomic writes with temp file + rename
- CLI recovery: `aio index rebuild --check-collisions`

**Open questions resolved:**
- Archive included by default: **Yes** (required for collision prevention)
- Staleness detection: **Fingerprint/mtime** (safer than trust-only)
- Who updates index: **Both daemon and CLI** (CLI needs offline support)

---

## Remaining Work

### Phase 1: Critical Bug Fixes (DONE)

#### 1.1 File Overwrite Prevention (Finding #2) - DONE
Added existence checks to TaskService.create(), ProjectService.create(), PersonService.create().

#### 1.2 Canonical Wikilinks (Findings #4, #5) - DONE
- Updated `TaskService.wait()` to emit `[[AIO/People/{slug}]]`
- Updated project template Dataview query to use `get_slug(name)`
- Updated person template Dataview query to use `get_slug(name)`
- Added shared `get_slug()` utility function

### Phase 2: Behavioral Consistency

#### 2.1 Daemon/CLI List Defaults (Finding #3) - DONE
- Updated `VaultCache.list_tasks()` to exclude Someday by default

#### 2.2 Title Search Coverage (Finding #6) - DONE
- Added Completed/YYYY/MM subfolder iteration to `_find_tasks_by_title()`

#### 2.3 Archive Metadata (Finding #8) - DONE
- Added `archived`, `archived_at`, `archived_from` fields to Task model
- Populated fields in `TaskService.archive()` before write
- Added `_read_task_file()` support for reading archive metadata
- Added test: `test_archive_task_sets_metadata`

### Phase 3: Plugin Read-Only Fallback (Finding #10)

**Goal:** Keep daemon as the only write path.

**If daemon is unavailable:**
- Read-only mode with explicit banner (e.g., "Daemon offline - tasks are read-only")
- Provide a one-click action or instructions to restart (`aio daemon start`)
- Show connection status in the UI (e.g., status pill + last error)

**Changes needed in `obsidian-aio/src/`:**
- Remove/disable file writes in `TaskService.ts` fallback paths
- Remove ID generation in fallback mode
- Add UI banner component for offline status
- Update status bar to show "Read-only" instead of "Offline"

### Phase 4: Documentation

#### 4.1 Fix Endpoint Documentation (Finding #9) - DONE
- Updated `DAEMON_ARCHITECTURE.md` line 198: `/wait` → `/delegate`

#### 4.2 Document MCP Cache Behavior (Finding #7) - DONE
- Added troubleshooting note to `docs/USER_MANUAL.md` under "MCP Issues" section
- Documented workaround: restart MCP server to refresh cache

---

## Test Coverage

### Existing Tests (43 total)
- `tests/unit/test_id_index.py` - 29 tests for IdIndexService
- `tests/unit/test_id_service.py` - 6 tests for IdService integration
- `tests/integration/test_id_index.py` - 8 tests for collision detection

### Tests Needed
- File overwrite prevention tests
- Canonical wikilink format tests
- Title search with completed subfolders tests
- Archive metadata tests
- Plugin read-only mode tests (TypeScript/Vitest)
