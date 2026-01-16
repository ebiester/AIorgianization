# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
pnpm install              # Install dependencies
pnpm build                # Build all packages
pnpm db:generate          # Generate database migrations (after schema changes)
pnpm db:migrate           # Apply database migrations

# Run CLI directly
node packages/cli/dist/index.js <command>

# Or after linking
pnpm --filter @aio/cli link --global
aio <command>
```

## Project Architecture

AIorgianization is a personal task/deadline management tool for engineering managers, built with GTD and BASB methodologies.

### Monorepo Structure (PNPM + Turborepo)

```
packages/
├── core/           # Shared: Drizzle schema, SQLite, services
├── cli/            # Commander.js CLI (primary interface)
├── api/            # Express REST API (planned)
├── web/            # React dashboard (planned)
├── obsidian/       # Vault reader (planned)
├── jira/           # Jira sync (planned)
└── mcp/            # MCP server for Claude (planned)
```

### Data Model (GTD-inspired)

**Tasks** have statuses: `inbox` → `next_action` | `waiting_for` | `scheduled` | `someday_maybe` → `in_progress` → `completed`

**Task types**: `personal` (own work), `delegated` (given to others), `team` (team-level)

**Priority**: P1-P4 (Eisenhower matrix)

**Projects** follow PARA: `project` | `area` | `resource` | `archive`

### Key Files

- `packages/core/src/schema/index.ts` - Drizzle table definitions
- `packages/core/src/services/TaskService.ts` - Task CRUD operations
- `packages/cli/src/commands/` - CLI command implementations

### Database

SQLite stored at `~/.aio/aio.db`. Uses Drizzle ORM with better-sqlite3.

## CLI Commands

```bash
aio add "Task" [-d due] [-P priority] [-p project]
aio list [inbox|next|waiting|someday|today|overdue|all]
aio done <id>           # Complete task
aio start <id>          # Move to in_progress
aio activate <id>       # Move to next_action
aio defer <id>          # Move to someday_maybe
aio wait <id> [person]  # Move to waiting_for
```

Task IDs can be the full ULID or just the last 6 characters.

## Conventions

- ESM modules with `.js` extensions in imports (TypeScript compiles to ESM)
- ULIDs for all primary keys (sortable, URL-safe)
- Dates stored as timestamps in SQLite
- Natural language date parsing via chrono-node
