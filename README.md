# AIorgianization

An Obsidian-native task and context management system for engineering managers. This is built for my needs and is not likely to work for yours but serves as an example of building personal software with Claude Code. 

I have used a lot of todo systems, including the Obsidian Tasks plugin by Clare Macrae, Ilyas Landikov, and Martin Schenck; Todoist, LogSeq and a set of systems I created for it; and Everdo. Each has some great advantages but none of them integrate exactly like I want, especially in 2026 as I start integrating more with Cursor CLI and Claude Code (and possibly Cowork) - and with the cost to create personal software going down, I decided to work on this.

There will be a blog post coming on this if anyone is interested. That said, for this use case I would suggest that you take the project plan and tweak it for how you think and rebuild from there; the hardest part will be in verification and getting it to work the way you need, but that will also teach you your own tool. 

## Features

- **CLI for quick capture**: Add tasks in seconds with natural language dates
- **Obsidian-native storage**: All data is markdown files in your vault
- **GTD workflow**: Inbox, Next, Waiting, Someday status tracking
- **MCP integration**: Use with Claude Code / Cursor for AI assistance
- **Daily dashboards**: Generated overviews of overdue, due today, and waiting items

## Installation

```bash
# Install with uv
uv tool install .

# Or install in development mode
uv sync
```

## Quick Start

```bash
# Initialize AIO structure in your Obsidian vault
aio init /path/to/your/vault

# Add tasks
aio add "Review PR #123" -d tomorrow
aio add "Design API" -p "Q4 Migration"

# List tasks
aio list inbox
aio list today

# Update status
aio start "Review PR"
aio done "Review PR"
aio wait "Design" Sarah
aio defer "Refactor"

# Generate dashboard
aio dashboard
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `aio init <vault>` | Initialize AIO structure |
| `aio add <title>` | Add a new task |
| `aio list [filter]` | List tasks (inbox, next, waiting, someday, today, overdue) |
| `aio done <query>` | Mark task as completed |
| `aio start <query>` | Move task to Next status |
| `aio defer <query>` | Move task to Someday |
| `aio wait <query> [person]` | Move task to Waiting |
| `aio dashboard` | Generate daily dashboard |
| `aio archive tasks --before <date>` | Archive old completed tasks |

## MCP Server

For Claude Code / Cursor integration, add to your MCP config:

```json
{
  "mcpServers": {
    "aio": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/AIorgianization", "aio-mcp"],
      "env": {
        "AIO_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design
- [PRD](docs/PRD.md) - Product requirements
- [Project Plan](docs/PROJECT_PLAN.md) - Implementation phases
- [User Manual](docs/USER_MANUAL.md) - End-user documentation
- [Assumptions](assumptions.md) - Implementation assumptions

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Type check
uv run mypy aio

# Lint and format
uv run ruff check .
uv run ruff format .
```

## License

MIT
