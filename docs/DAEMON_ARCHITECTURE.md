# Plan: AIO Daemon Architecture - Unified Backend

## Goal
Create a persistent daemon that serves as the **single source of truth** for all clients:
- **CLI** (thin client, <20ms response)
- **Cursor/MCP** (AI tool integration)
- **Obsidian plugin** (UI in the vault)

Eliminate duplicate business logic across Python CLI and TypeScript plugin.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AIO Daemon (aio-daemon)                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │   ServiceRegistry + VaultCache (in-memory task index)          │ │
│  │   File watcher (watchdog) for cache invalidation               │ │
│  └──────────────────────────┬─────────────────────────────────────┘ │
│                             │                                        │
│  ┌──────────────────────────┴──────────────────────────────────┐    │
│  │                  Command Handlers (shared)                   │    │
│  └────────┬─────────────────┬─────────────────┬────────────────┘    │
│           │                 │                 │                      │
│  ┌────────┴────────┐ ┌──────┴──────┐ ┌────────┴────────┐            │
│  │ Unix Socket     │ │ HTTP API    │ │ stdio (MCP)     │            │
│  │ ~/.aio/daemon   │ │ localhost   │ │ for Cursor      │            │
│  │ .sock           │ │ :7432       │ │                 │            │
│  └────────┬────────┘ └──────┬──────┘ └────────┬────────┘            │
└───────────┼─────────────────┼─────────────────┼─────────────────────┘
            │                 │                 │
     ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐
     │  CLI (thin) │   │  Obsidian   │   │   Cursor    │
     │  aio add... │   │  Plugin     │   │   (MCP)     │
     └─────────────┘   └─────────────┘   └─────────────┘
```

## Key Design Decisions

1. **Three transports, one handler layer:**
   - Unix socket (JSON-RPC) for CLI - fastest, ~5ms
   - HTTP API for Obsidian plugin - works in browser context
   - stdio (MCP protocol) for Cursor - AI tool spec

2. **Single source of business logic** - Python daemon owns:
   - ID generation (no collisions across clients)
   - YAML frontmatter schema
   - Date parsing and formatting
   - Task state transitions
   - File I/O and atomic writes

3. **Obsidian plugin becomes thin UI:**
   - HTTP calls to daemon for all operations
   - Renders responses, handles user interaction
   - No direct file manipulation
   - Falls back to read-only mode if daemon unavailable

4. **Cross-platform daemon management:**
   - macOS: launchd (auto-start on login)
   - Linux: systemd user service (auto-start on login)

5. **Socket path:** `~/.aio/daemon.sock`
6. **HTTP port:** `localhost:7432` (configurable)
7. **Graceful fallback:** CLI works standalone if daemon not running

## Implementation Phases

### Phase 1: Daemon Foundation
Create daemon infrastructure without touching existing CLI or plugin.

**New files:**
- `aio/daemon/__init__.py`
- `aio/daemon/server.py` - Main daemon class, multi-transport
- `aio/daemon/cache.py` - VaultCache with file watching
- `aio/daemon/handlers.py` - Command handlers (extract from MCP server)
- `aio/daemon/protocol.py` - JSON-RPC message types
- `aio/daemon/transports/unix_socket.py` - Unix socket transport
- `aio/daemon/transports/http.py` - HTTP REST API transport

**Modify:**
- `pyproject.toml` - Add `aio-daemon` entry point, add dependencies

**New dependencies:**
```toml
"watchdog>=3.0.0",   # File system watching
"aiohttp>=3.9.0",    # Async HTTP server
```

**Tasks:**
1. Create `aio/daemon/cache.py` with VaultCache class
   - Task index: `dict[str, Task]` (ID -> Task)
   - Title search: `dict[str, list[str]]` (title_lower -> IDs)
   - File watcher using watchdog library
2. Create `aio/daemon/handlers.py` - Extract handler logic from `aio/mcp/server.py`
3. Create `aio/daemon/protocol.py` - JSON-RPC request/response types
4. Create `aio/daemon/transports/unix_socket.py` - Unix socket server
5. Create `aio/daemon/transports/http.py` - HTTP REST API server
6. Create `aio/daemon/server.py` - AioDaemon orchestration
7. Add entry points and dependencies to pyproject.toml

### Phase 2: Daemon Management CLI
Add commands to control the daemon on macOS and Linux.

**New files:**
- `aio/cli/daemon_cmd.py` - Daemon management commands
- `aio/daemon/service/launchd.py` - macOS launchd integration
- `aio/daemon/service/systemd.py` - Linux systemd integration
- `aio/daemon/service/templates/com.aio.daemon.plist` - launchd template
- `aio/daemon/service/templates/aio-daemon.service` - systemd template

**Modify:**
- `aio/cli/main.py` - Add daemon command group

**Commands:**
```bash
aio daemon start     # Start daemon (foreground or background)
aio daemon stop      # Stop daemon
aio daemon status    # Check if running, show PID, port
aio daemon restart   # Stop + start
aio daemon install   # Install service (launchd on macOS, systemd on Linux)
aio daemon uninstall # Remove service
aio daemon logs      # Tail daemon logs
```

**Service behavior (both platforms):**
- Auto-starts on login
- Restarts on crash
- Logs to `~/.aio/daemon.log`

### Phase 3: Thin CLI Client
Add client code and migrate commands one by one.

**New files:**
- `aio/cli/client.py` - DaemonClient class (socket communication)
- `aio/cli/fallback.py` - Direct execution when daemon unavailable

**Modify (one at a time):**
- `aio/cli/list.py` - First migration (read-only, simple)
- `aio/cli/done.py` - Simple mutation
- `aio/cli/status.py` - start/defer/wait commands
- `aio/cli/add.py` - Complex (project/person lookup)
- `aio/cli/dashboard.py`
- `aio/cli/archive.py`
- `aio/cli/file.py`
- `aio/cli/config.py`

**Pattern for each command:**
```python
def list_tasks(...):
    client = DaemonClient()
    if client.is_daemon_running():
        response = client.call("list_tasks", {...})
        render_response(response)  # Keep exact same Rich output
    else:
        # Graceful fallback: works but slower (~300ms)
        # Lazy imports keep CLI startup fast even in fallback
        list_tasks_direct(...)
```

### Phase 4: MCP Server Consolidation
Remove duplication between MCP server and daemon.

**Modify:**
- `aio/mcp/server.py` - Import handlers from `aio/daemon/handlers.py`

### Phase 5: Obsidian Plugin Refactor
Convert plugin from direct file ops to HTTP API calls.

**Modify (in obsidian-aio/):**
- `src/services/TaskService.ts` - Replace vault.read/write with HTTP calls
- `src/services/VaultService.ts` - Remove file operations, keep path helpers
- Add `src/services/DaemonClient.ts` - HTTP client for daemon API

**Plugin behavior:**
- Check daemon availability on load
- All task CRUD via HTTP API
- Show status indicator (connected/disconnected)
- Fallback: read-only mode (can view tasks via direct file read, but no mutations)

**Delete (eventually):**
- YAML parsing logic in plugin (daemon handles this)
- ID generation in plugin (daemon handles this)
- File write operations (daemon handles this)

## HTTP API Design

**Base URL:** `http://localhost:7432/api/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks` | GET | List tasks (query params: status, project) |
| `/tasks` | POST | Create task |
| `/tasks/{id}` | GET | Get single task |
| `/tasks/{id}` | PATCH | Update task |
| `/tasks/{id}/complete` | POST | Mark complete |
| `/tasks/{id}/start` | POST | Move to Next |
| `/tasks/{id}/defer` | POST | Move to Someday |
| `/tasks/{id}/wait` | POST | Move to Waiting |
| `/projects` | GET | List projects |
| `/people` | GET | List people |
| `/dashboard` | GET | Get today's dashboard |
| `/health` | GET | Daemon health check |

**Response format:**
```json
{
  "ok": true,
  "data": { ... }
}
```

**Error format:**
```json
{
  "ok": false,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task AB2C not found"
  }
}
```

## Critical Files

| File | Purpose |
|------|---------|
| `aio/daemon/server.py` | Main daemon, transport orchestration |
| `aio/daemon/cache.py` | In-memory task index, file watching |
| `aio/daemon/handlers.py` | Shared command handlers |
| `aio/daemon/transports/http.py` | HTTP API for Obsidian plugin |
| `aio/cli/client.py` | Unix socket client for CLI |
| `obsidian-aio/src/services/DaemonClient.ts` | HTTP client for plugin |

## Protocol: JSON-RPC 2.0 (Unix Socket)

**Request:**
```json
{"jsonrpc": "2.0", "id": 1, "method": "list_tasks", "params": {"status": "inbox"}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 1, "result": {"tasks": [...]}}
```

## Verification

After each phase:

1. **Phase 1:** `uv run aio-daemon` starts, logs "ready" on all transports
2. **Phase 2:** `aio daemon install` works on macOS (launchd) and Linux (systemd)
3. **Phase 3:** `aio list` returns in <20ms when daemon running
4. **Phase 4:** MCP tools still work via Cursor
5. **Phase 5:** Obsidian plugin creates tasks via HTTP API

**Performance benchmark:**
```bash
# Before (current)
time aio list inbox  # ~400ms

# After (with daemon)
time aio list inbox  # <20ms

# HTTP API
curl localhost:7432/api/v1/health  # <5ms
```

**Test commands:**
```bash
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/daemon/  # New daemon tests
uv run ruff check .
uv run mypy aio
```

## Migration Path

1. **Phase 1-4:** CLI and Cursor work with daemon, plugin unchanged
2. **Phase 5:** Plugin migrated, old file operations removed
3. **Cleanup:** Remove duplicate TypeScript logic from plugin

This creates a clean architecture where:
- All business logic lives in Python
- All clients are thin (CLI, Cursor, Obsidian)
- Single point for schema changes
- No ID collisions across clients
