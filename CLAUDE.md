# CLAUDE.md

This file provides guidance to AI assistants (Cursor, Claude Code, etc.) when working with code in this repository.

## Project Overview

AIorgianization is an Obsidian-native task and context management system for Eric, an engineering manager. Tasks are stored as markdown files in the Obsidian vault, with a CLI for quick capture and an MCP server for Cursor/Claude integration.

**Key principle:** The Obsidian vault is the single source of truth. No separate database.

**Target integration:** Cursor CLI with MCP tools and skills.

## Architecture

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
    │  (UI)   │          │(Python) │          │(Python) │
    └─────────┘          └─────────┘          └─────────┘
```

### Codebase Structure

```
AIorgianization/
├── aio/                    # Python package (CLI + MCP)
│   ├── __init__.py
│   ├── cli/                # CLI commands (Click)
│   │   ├── __init__.py
│   │   ├── main.py         # Entry point
│   │   ├── add.py
│   │   ├── list.py
│   │   ├── done.py
│   │   ├── archive.py
│   │   └── dashboard.py
│   ├── mcp/                # MCP server
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── tools.py
│   ├── services/           # Core business logic
│   │   ├── __init__.py
│   │   ├── vault.py        # Vault discovery & file operations
│   │   ├── task.py         # Task CRUD (markdown files)
│   │   ├── project.py      # Project file operations
│   │   └── dashboard.py    # Dashboard generation
│   ├── models/             # Data models (Pydantic)
│   │   ├── __init__.py
│   │   ├── task.py
│   │   ├── project.py
│   │   └── person.py
│   └── utils/
│       ├── __init__.py
│       ├── frontmatter.py  # YAML frontmatter parsing
│       ├── dates.py        # Natural language date parsing
│       └── ids.py          # 4-char ID generation
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── unit/               # Unit tests
│   │   ├── test_vault.py
│   │   ├── test_task.py
│   │   ├── test_dates.py
│   │   └── test_ids.py
│   ├── integration/        # Integration tests
│   │   ├── test_cli.py
│   │   └── test_mcp.py
│   └── e2e/                # End-to-end tests
│       ├── test_workflows.py
│       └── fixtures/       # Test vault fixtures
├── obsidian-aio/           # Obsidian plugin (TypeScript)
│   ├── src/                # Plugin source code
│   └── tests/              # Vitest tests with mocked Obsidian API
├── scripts/
│   └── test/               # Comprehensive test runner
│       ├── run-tests.sh    # Main orchestrator
│       ├── run-python-tests.sh
│       ├── run-typescript-tests.sh
│       ├── run-mcp-tests.sh
│       ├── setup-test-vault.sh
│       └── generate-report.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   ├── PROJECT_PLAN.md
│   └── USER_MANUAL.md
├── pyproject.toml          # Python project config (uv/poetry)
├── .python-version         # Python version (3.12+)
└── CLAUDE.md               # This file
```

## Build & Development Commands

```bash
# Python environment (using uv)
uv sync                           # Install dependencies
uv run aio --help                 # Run CLI directly
uv run pytest                     # Run all tests
uv run pytest tests/unit          # Run unit tests only
uv run pytest tests/e2e           # Run end-to-end tests
uv run pytest -x                  # Stop on first failure
uv run pytest -v                  # Verbose output
uv run pytest --cov=aio           # With coverage

# Type checking and linting
uv run mypy aio                   # Type check
uv run ruff check .               # Lint
uv run ruff format .              # Format

# MCP server
uv run aio-mcp                    # Start MCP server

# CLI after installation
aio init <vault-path>             # Initialize AIO structure
aio add "Task" -d tomorrow        # Quick add
aio list inbox                    # List inbox tasks
aio done <id>                     # Complete task
aio dashboard                     # Generate dashboard

# Comprehensive test runner (Python + TypeScript + MCP)
./scripts/test/run-tests.sh                    # Run all tests
./scripts/test/run-tests.sh --python-only      # Python tests only
./scripts/test/run-tests.sh --typescript-only  # TypeScript tests only
./scripts/test/run-tests.sh --mcp-only         # MCP server tests only
./scripts/test/run-tests.sh --skip-coverage    # Skip coverage generation
./scripts/test/run-tests.sh --verbose          # Verbose output
```

## CLI Commands Reference

```bash
# Initialization
aio init <vault-path>             # Create AIO directory structure in vault

# Task management
aio add "Task title" [-d due] [-p project] [-a person]
aio list [inbox|next|waiting|someday|today|overdue|all]
aio done <task-id-or-query>       # Complete task
aio start <task>                  # Move to Next status
aio defer <task>                  # Move to Someday
aio wait <task> [person]          # Move to Waiting

# The -a/--assign flag creates task and delegates immediately:
# aio add "Review API" --assign Sarah  # Creates in Waiting status

# Dashboard
aio dashboard                     # Generate/update today's dashboard
aio dashboard --date 2024-01-15   # Specific date

# Archiving
aio archive task <task>
aio archive project <project>
aio archive tasks --before "6 months ago"
aio archive tasks --before 2024-01-01 --dry-run
```

## Data Formats

### Task File Format

Tasks live in `AIO/Tasks/{Status}/YYYY-MM-DD-short-title.md`:

```markdown
---
id: AB2C                          # 4-char alphanumeric ID
type: task
status: next                      # inbox | next | waiting | scheduled | someday | completed
due: 2024-01-20
project: "[[Projects/Q4-Migration]]"
assignedTo: "[[People/Sarah]]"
waitingOn: null
blockedBy: []
blocks: []
location:
  file: "src/api/payments.ts"
  line: 142
  url: null
tags:
  - backend
timeEstimate: 2h
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
```

### Task IDs

- 4 characters from: `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` (32 chars)
- Excludes ambiguous: `0`, `1`, `I`, `O`
- Case-insensitive matching
- Generate with retry on collision

### Vault Structure

```
Vault/
├── .aio/                         # Config (not in git)
│   └── config.yaml
├── AIO/
│   ├── Dashboard/
│   ├── Tasks/
│   │   ├── Inbox/
│   │   ├── Next/
│   │   ├── Waiting/
│   │   ├── Scheduled/
│   │   ├── Someday/
│   │   └── Completed/YYYY/MM/
│   ├── Projects/
│   ├── Areas/
│   ├── People/
│   ├── Context-Packs/
│   ├── ADRs/
│   └── Archive/                  # Parallel structure
```

## Testing Requirements

### Test Organization

- **Unit tests (`tests/unit/`)**: Test individual functions/classes in isolation. Mock external dependencies.
- **Integration tests (`tests/integration/`)**: Test component interactions (CLI parsing, service layer).
- **End-to-end tests (`tests/e2e/`)**: Test full workflows with real vault fixtures.

### Test Conventions

```python
# Use pytest fixtures for common setup
@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault with AIO structure."""
    vault = tmp_path / "TestVault"
    # Create structure...
    return vault

# Descriptive test names
def test_add_task_creates_file_in_inbox(temp_vault):
    """aio add should create a task file in Tasks/Inbox/."""
    ...

# Test edge cases explicitly
def test_add_task_with_duplicate_id_retries(temp_vault):
    """ID generation should retry on collision."""
    ...
```

### What to Test

1. **Happy paths**: Normal usage flows
2. **Edge cases**: Empty inputs, boundary conditions
3. **Error handling**: Invalid inputs, missing files, permissions
4. **Date parsing**: All natural language formats
5. **ID generation**: Collision handling, case insensitivity
6. **File operations**: Create, read, move, archive

### Coverage Targets

- Unit tests: 90%+ coverage on services/ and utils/
- Integration tests: All CLI commands
- E2E tests: Core workflows (add → list → done, archive, dashboard)

### Comprehensive Test Runner

The `scripts/test/` directory contains a language-agnostic test orchestrator that runs Python, TypeScript, and MCP server tests together:

```bash
./scripts/test/run-tests.sh                    # Run all tests
./scripts/test/run-tests.sh --python-only      # Python tests only
./scripts/test/run-tests.sh --typescript-only  # TypeScript tests only
./scripts/test/run-tests.sh --mcp-only         # MCP server tests only
./scripts/test/run-tests.sh --verbose          # Verbose output
```

**Scripts:**
- `run-tests.sh` - Main orchestrator
- `run-python-tests.sh` - Runs pytest with JSON report and coverage
- `run-typescript-tests.sh` - Runs vitest for Obsidian plugin
- `run-mcp-tests.sh` - Spawns MCP server and tests JSON-RPC protocol
- `setup-test-vault.sh` - Creates isolated test vault with .obsidian structure
- `generate-report.py` - Aggregates results, extracts UAT coverage

**Generated Reports** (`test-results/`):
- `combined-report.md` - Human-readable summary with UAT coverage
- `uat-coverage.json` - Machine-readable UAT mapping
- `manual-test-checklist.md` - Checklist for Obsidian plugin manual tests

### UAT Markers

Use pytest markers to map tests to UAT cases:

```python
@pytest.mark.uat("UAT-003")
def test_add_task(runner, initialized_vault):
    """add should create a task."""
    result = runner.invoke(cli, ["--vault", str(initialized_vault), "add", "Test Task"])
    assert result.exit_code == 0
```

The report generator extracts these markers from source files to produce UAT coverage reports.

## Coding Conventions

### Work in Small Pieces

- Make incremental changes and commit frequently
- Each commit should be a single logical unit (one feature, one fix, one refactor)
- Prefer multiple small PRs over one large PR
- Test each piece before moving to the next
- If a task feels too big, break it down further

### Exit Criteria / Verification

Before considering a task complete, verify the expected behavior:

- **CLI changes**: Run the actual command and confirm the output matches expectations
  - After modifying entry points or dependencies, run `uv pip install -e . --force-reinstall` to ensure changes are picked up
  - Test both success and error cases
  - For error handling changes, trigger the error condition and verify user-friendly output (no tracebacks unless `--debug`)
- **Service/model changes**: Run relevant unit tests with `uv run pytest tests/unit/test_<module>.py`
- **Integration changes**: Run `uv run pytest tests/integration/`
- **Linting (REQUIRED)**: Run `uv run ruff check .` and confirm **zero errors**. Fix any linting issues before considering the task complete.
- **Type checking**: Run `uv run mypy aio` and ensure it passes

A task is not complete until:
1. The expected output is observed
2. Linting passes with no errors (`uv run ruff check .` shows "All checks passed!")
3. Type checking passes
4. Documentation is updated (see below)

If verification fails, continue debugging until it passes.

### Documentation Requirements

**After completing any feature or significant change, update the following:**

1. **Project Plan (`docs/PROJECT_PLAN.md`)**:
   - Mark completed tasks/milestones as done
   - Add new tasks if the feature revealed additional work needed

2. **PRD (`docs/PRD.md`)**:
   - Add new features or capabilities to the appropriate section
   - Update use cases if behavior changed

3. **User Manual (`docs/USER_MANUAL.md`)**:
   - Document new CLI commands, flags, or options
   - Add examples showing the new functionality
   - Update MCP tools table if MCP tools changed
   - Add troubleshooting entries if relevant

4. **UAT Plan (`docs/UAT_PLAN.md`)**:
   - Add acceptance test cases for the new feature
   - Include both happy path and error scenarios

5. **CLAUDE.md** (this file):
   - Update CLI Commands Reference if commands changed
   - Update MCP Available Tools if tools changed

**Example checklist for a new CLI flag:**
- [ ] Feature implemented and tested
- [ ] `docs/USER_MANUAL.md` - Added flag to CLI Reference with examples
- [ ] `docs/UAT_PLAN.md` - Added test case for the new flag
- [ ] `CLAUDE.md` - Updated CLI Commands Reference
- [ ] `docs/PROJECT_PLAN.md` - Marked task complete (if applicable)

### Python Style

- Python 3.12+
- Type hints on all public functions
- Pydantic models for data validation
- Click for CLI (not argparse)
- Use `pathlib.Path` for all file paths
- f-strings for string formatting
- Docstrings on public functions (Google style)

```python
def find_task(vault: Path, query: str) -> Task | None:
    """Find a task by ID or title substring.

    Args:
        vault: Path to the Obsidian vault root.
        query: Task ID (4 chars) or title substring.

    Returns:
        The matching Task, or None if not found.

    Raises:
        MultipleMatchError: If query matches multiple tasks.
    """
    ...
```

### Error Handling

- Use custom exceptions for domain errors
- CLI should catch and display user-friendly messages
- Never show stack traces in normal usage (use `--debug` flag)
- Exit codes: 0=success, 1=error, 2=usage error

```python
class TaskNotFoundError(AioError):
    """Raised when a task cannot be found by ID or query."""
    pass

class AmbiguousMatchError(AioError):
    """Raised when a query matches multiple tasks."""
    pass
```

### File Operations

- Always use atomic writes (write to temp, then rename)
- Preserve file permissions
- Handle encoding as UTF-8
- Use `python-frontmatter` for YAML frontmatter

```python
import frontmatter

def write_task(path: Path, task: Task) -> None:
    """Atomically write a task file."""
    post = frontmatter.Post(task.body, **task.frontmatter())
    content = frontmatter.dumps(post)

    temp = path.with_suffix('.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.rename(path)
```

### Date Parsing

- Use `dateparser` for natural language
- Store dates as ISO 8601 in frontmatter
- Display dates relative ("tomorrow", "in 3 days", "overdue")

## MCP Server (Cursor Integration)

The MCP server exposes vault operations to Cursor CLI and other MCP-compatible tools:

### Configuration

Add to your Cursor MCP config (`~/.cursor/mcp.json` or project-level):

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

### Available Tools

```python
# Task Management
aio_add_task(title, due?, project?, assign?)  → task_id  # assign delegates immediately
aio_list_tasks(status?, project?)             → Task[]
aio_complete_task(id)                         → success
aio_start_task(id)                            → success
aio_defer_task(id)                            → success

# Context
aio_get_context(packs)               → content
aio_get_project(name)                → project_content

# Dashboard
aio_get_dashboard()                  → dashboard_content
```

### Available Resources

```
aio://tasks/inbox      # Current inbox tasks
aio://tasks/next       # Next actions
aio://tasks/waiting    # Waiting-for items
aio://tasks/today      # Due today + overdue
aio://projects         # Active projects list
aio://dashboard        # Today's dashboard
```

### Cursor Skills

Create `.cursor/skills/aio.md` for natural language task management:

```markdown
# AIO Task Management Skill

When the user asks about tasks, deadlines, or project management:

1. Use `aio_list_tasks` to see current state
2. Use `aio_add_task` for quick capture
3. Use `aio_get_dashboard` for daily overview
4. Reference `aio://tasks/today` for urgent items

Example prompts:
- "What's on my plate today?" → aio_get_dashboard()
- "Add a task to review the PR by Friday" → aio_add_task("Review PR", due="friday")
- "Add a task for Sarah to update docs" → aio_add_task("Update docs", assign="Sarah")
- "Show my inbox" → aio_list_tasks(status="inbox")
```

## Assumptions for Single User (Eric)

Since this is built for one user:

- No multi-user auth/permissions
- Vault path can be hardcoded in config or env var
- CLI can assume interactive terminal (colors, prompts)
- No need for i18n
- Can use Eric's typical folder locations as defaults

## Key Files to Know

| File | Purpose |
|------|---------|
| `aio/services/vault.py` | Vault discovery and file operations |
| `aio/services/task.py` | Task CRUD (the core logic) |
| `aio/models/task.py` | Task Pydantic model |
| `aio/utils/ids.py` | 4-char ID generation |
| `aio/utils/dates.py` | Natural language date parsing |
| `aio/cli/main.py` | CLI entry point and command group |
| `tests/conftest.py` | Shared pytest fixtures |

## Common Tasks

### Adding a New CLI Command

1. Create `aio/cli/newcmd.py`
2. Implement Click command
3. Add to `aio/cli/main.py` command group
4. Add tests in `tests/unit/test_newcmd.py`
5. Add integration test in `tests/integration/test_cli.py`

### Adding a New MCP Tool

1. Add tool definition in `aio/mcp/tools.py`
2. Implement handler using services layer
3. Add tests in `tests/integration/test_mcp.py`

### Modifying Task Schema

1. Update `aio/models/task.py` Pydantic model
2. Update `aio/services/task.py` read/write logic
3. Update frontmatter parsing in `aio/utils/frontmatter.py`
4. Add migration if needed for existing files
5. Update tests
6. Update `docs/ARCHITECTURE.md`

## Dependencies

Core:
- `click` - CLI framework
- `pydantic` - Data validation
- `python-frontmatter` - YAML frontmatter
- `dateparser` - Natural language dates
- `mcp` - MCP server SDK
- `pyyaml` - YAML parsing
- `rich` - Terminal formatting

Dev:
- `pytest` - Testing
- `pytest-cov` - Coverage
- `mypy` - Type checking
- `ruff` - Linting and formatting

## Links

- [Architecture](docs/ARCHITECTURE.md) - Full system design
- [PRD](docs/PRD.md) - Product requirements and use cases
- [Project Plan](docs/PROJECT_PLAN.md) - Implementation phases
- [User Manual](docs/USER_MANUAL.md) - End-user documentation
