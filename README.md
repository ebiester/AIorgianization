# AIorgianization

An Obsidian-native task and context management system for engineering managers. This is built for my needs and is not likely to work for yours but serves as an example of building personal software through AI coding and chat tools.

I have used a lot of todo systems, including the Obsidian Tasks plugin by Clare Macrae, Ilyas Landikov, and Martin Schenck; Todoist, LogSeq and a set of systems I created for it; and Everdo. Each has some great advantages but none of them integrate exactly like I want, especially in 2026 as I start managing more work through AI chat interfaces—and with the cost to create personal software going down, I decided to work on this.

There will be a blog post coming on this if anyone is interested. That said, for this use case I would suggest that you take the project plan and tweak it for how you think and rebuild from there; the hardest part will be in verification and getting it to work the way you need, but that will also teach you your own tool. 

## Features

- **CLI for people and agents**: Add tasks quickly, with stable JSON commands for chat skills
- **Obsidian-native storage**: All data is markdown files in your vault
- **GTD workflow**: Inbox, Next, Waiting, Someday status tracking
- **Chat-first integration**: Use the `manage-aio` skill in ChatGPT Desktop, Codex, or a Remote Connection
- **Daily dashboards**: Generated overviews of overdue, due today, and waiting items
- **Task-centred open brain**: Resume a task with linked context, record work, and promote durable knowledge while keeping Markdown canonical
- **Local retrieval**: A rebuildable SQLite full-text index for vault search and backlinks

## Quick Start

Create or open an Obsidian vault, initialise AIO, then capture a task:

```bash
uv run aio init /path/to/your/vault
uv run aio --vault /path/to/your/vault add "Review the rollout plan" --notes \
  "- Why: launch approval is pending\n- Next action: send the updated plan"
uv run aio --vault /path/to/your/vault index rebuild
```

The vault's Markdown files are the source of truth. The index at `.aio/index.sqlite` is derived and can always be deleted and rebuilt.

### Work a Task in Chat

Install or link `skills/manage-aio/` on the desktop host, then use this loop locally or through ChatGPT Remote Connections:

1. List or select a task with `aio agent list` or `aio agent dashboard`.
2. Run `aio agent resume <id>` to retrieve its body, explicit links, backlinks, and related search results.
3. Perform the work using the returned source paths as context.
4. Run `aio agent record-work <id>` before ending the session.
5. Create substantive follow-ups with `aio agent add --notes ...` and promote durable evidence with `aio agent promote-knowledge`.

There is deliberately no global active-task state: every session explicitly supplies the task it is working on.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design
- [PRD](docs/PRD.md) - Product requirements
- [Project Plan](docs/PROJECT_PLAN.md) - Implementation phases
- [User Manual](docs/USER_MANUAL.md) - End-user documentation
- [Open Brain Evolution Plan](docs/OPEN_BRAIN_EVOLUTION_PLAN.md) - Task-centred architecture and scope
- [Open Brain Test Plan](docs/OPEN_BRAIN_TEST_PLAN.md) - Implementable acceptance tests and test setup
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
