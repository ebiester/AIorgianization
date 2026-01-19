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
