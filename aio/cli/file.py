"""CLI commands for file operations with backup."""

import sys
from pathlib import Path

import click
from rich.console import Console

from aio.exceptions import AmbiguousMatchError, FileOutsideVaultError
from aio.services.file import FileService
from aio.services.vault import VaultService

console = Console()


@click.group()
def file() -> None:
    """File operations with automatic backup."""
    pass


@file.command("get")
@click.argument("query")
@click.pass_context
def file_get(ctx: click.Context, query: str) -> None:
    """Get the contents of a file in the vault.

    QUERY can be a file ID (4-char), title substring, or path relative to vault.

    \b
    Examples:
      aio file get AB2C                    # Get file by ID
      aio file get "Review PR"             # Get file by title
      aio file get AIO/Tasks/Inbox/task.md # Get file by path
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    file_service = FileService(vault_service)

    try:
        content = file_service.get(query)
        # Print to stdout without Rich formatting so it can be piped
        print(content, end="")
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {query}")
        raise click.Abort() from None
    except FileOutsideVaultError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Error:[/red] Multiple files match '{e.query}':")
        for match in e.matches:
            console.print(f"  - {match}")
        console.print("\nUse a more specific query or the full path.")
        raise click.Abort() from None


@file.command("set")
@click.argument("query")
@click.option("-c", "--content", help="Content to write")
@click.option(
    "-f",
    "--file",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="Read content from file",
)
@click.pass_context
def file_set(
    ctx: click.Context,
    query: str,
    content: str | None,
    input_file: Path | None,
) -> None:
    """Set file contents with automatic backup.

    QUERY can be a file ID (4-char), title substring, or path relative to vault.
    For existing files, you can use ID or title. For new files, use a path.

    Content can be provided via --content, --file, or stdin.
    Creates a timestamped backup before overwriting existing files.

    \b
    Examples:
      aio file set AB2C -c "new content"           # Update file by ID
      aio file set "Review PR" -f updated.md       # Update file by title
      aio file set AIO/new-file.md -c "content"    # Create new file by path
      cat file.md | aio file set AB2C              # Update from stdin
    """
    vault_path: Path | None = ctx.obj.get("vault_path")
    vault_service = VaultService(vault_path)
    file_service = FileService(vault_service)

    # Determine content source
    if content is not None:
        file_content = content
    elif input_file is not None:
        file_content = input_file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        file_content = sys.stdin.read()
    else:
        console.print(
            "[red]Error:[/red] No content provided. "
            "Use --content, --file, or pipe content via stdin."
        )
        raise click.Abort()

    try:
        resolved_path, backup_path = file_service.set(query, file_content)
        # Show relative paths from vault root for cleaner output
        try:
            relative_file = resolved_path.relative_to(vault_service.vault_path)
        except ValueError:
            relative_file = resolved_path

        if backup_path:
            try:
                relative_backup = backup_path.relative_to(vault_service.vault_path)
                console.print(f"[green]Backup created:[/green] {relative_backup}")
            except ValueError:
                console.print(f"[green]Backup created:[/green] {backup_path}")
        console.print(f"[green]File updated:[/green] {relative_file}")
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {query}")
        raise click.Abort() from None
    except FileOutsideVaultError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from None
    except AmbiguousMatchError as e:
        console.print(f"[red]Error:[/red] Multiple files match '{e.query}':")
        for match in e.matches:
            console.print(f"  - {match}")
        console.print("\nUse a more specific query or the full path.")
        raise click.Abort() from None
