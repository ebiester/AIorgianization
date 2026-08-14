"""Task-centred context assembly and durable knowledge promotion."""

from pathlib import Path

from aio.models.task import Task
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.services.vault_index import VaultIndex
from aio.utils import get_slug
from aio.utils.frontmatter import read_frontmatter, write_frontmatter


class OpenBrainService:
    """Compose work context while keeping Markdown the canonical store."""

    CATEGORY_FOLDERS = {
        "adr": "AIO/ADRs",
        "project": "AIO/Projects",
        "area": "AIO/Areas",
        "context-pack": "AIO/Context-Packs/Operating",
        "person": "AIO/People",
    }

    def __init__(self, vault: VaultService, tasks: TaskService) -> None:
        self.vault = vault
        self.tasks = tasks
        self.index = VaultIndex(vault)

    def resume(self, query: str, max_chars: int = 20000) -> dict[str, object]:
        """Assemble bounded context for one explicit task without global state."""
        task = self.tasks.find(query)
        self.index.reconcile()
        task_path = self._task_path(task)
        related_paths = [*self._task_links(task), *self.index.backlinks(task_path)]
        documents: list[dict[str, str]] = []
        for path in dict.fromkeys(related_paths):
            document = self._read_document(path)
            if document:
                documents.append(document)
        search_terms = " ".join([task.title, *task.tags])
        related = self.index.search(search_terms, limit=10)
        used = len(task.body)
        bounded: list[dict[str, str]] = []
        for document in documents:
            content = document["content"]
            remaining = max_chars - used
            if remaining <= 0:
                break
            document["content"] = content[:remaining]
            bounded.append(document)
            used += len(document["content"])
        return {
            "task": self._task_data(task, task_path),
            "linked_context": bounded,
            "related": related,
            "truncated": used >= max_chars,
        }

    def promote(
        self,
        query: str,
        target: str,
        category: str,
        content: str,
        section: str | None,
        provenance: str | None,
    ) -> str:
        """Atomically update or create one explicit canonical artifact with provenance."""
        if category not in self.CATEGORY_FOLDERS:
            raise ValueError(f"Unsupported knowledge category: {category}")
        task = self.tasks.find(query)
        path = self._promotion_path(target, category)
        path.parent.mkdir(parents=True, exist_ok=True)
        provenance_text = provenance.strip() if provenance else ""
        source = f"\n\n> Provenance: [[{self._task_path(task).removesuffix('.md')}]] ({task.id})"
        addition = (
            content.strip() + source + (f" — {provenance_text}" if provenance_text else "") + "\n"
        )
        if path.exists():
            metadata, body = read_frontmatter(path)
            if section:
                heading = f"## {section.strip()}"
                if heading not in body:
                    body = body.rstrip() + f"\n\n{heading}\n"
                body = body.rstrip() + "\n\n" + addition
            else:
                body = body.rstrip() + "\n\n" + addition
            write_frontmatter(path, metadata, body)
        else:
            title = target.replace("-", " ").replace("/", " ").title()
            body = f"# {title}\n\n"
            if section:
                body += f"## {section.strip()}\n\n"
            body += addition
            write_frontmatter(path, {"type": category, "sourceTask": task.id}, body)
        self.tasks.link_context(task.id, [str(path.relative_to(self.vault.vault_path))])
        self.index.reconcile()
        return path.relative_to(self.vault.vault_path).as_posix()

    def _promotion_path(self, target: str, category: str) -> Path:
        cleaned = target.strip().removeprefix("[[").removesuffix("]]").split("|")[0].strip()
        if not cleaned:
            raise ValueError("Promotion target cannot be empty")
        candidate = Path(cleaned)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Promotion target must be a relative vault path or title")
        base = Path(self.CATEGORY_FOLDERS[category])
        if len(candidate.parts) == 1:
            candidate = base / f"{get_slug(cleaned)}.md"
        elif not str(candidate).startswith("AIO/"):
            candidate = base / candidate
        if candidate.suffix != ".md":
            candidate = candidate.with_suffix(".md")
        path = (self.vault.vault_path / candidate).resolve()
        if not str(path).startswith(str((self.vault.vault_path / base).resolve())):
            raise ValueError("Promotion target is outside the selected category")
        return path

    def _task_path(self, task: Task) -> str:
        for path in self.vault.aio_path.joinpath("Tasks").rglob("*.md"):
            metadata, _ = read_frontmatter(path)
            if str(metadata.get("id", "")).upper() == task.id.upper():
                return path.relative_to(self.vault.vault_path).as_posix()
        raise FileNotFoundError(f"Task file not found: {task.id}")

    def _task_links(self, task: Task) -> list[str]:
        links = [
            task.project,
            task.assigned_to,
            task.waiting_on,
            *task.context,
            *task.blocked_by,
            *task.blocks,
        ]
        return [
            link[2:-2].split("|")[0] + ".md" for link in links if link and link.startswith("[[")
        ]

    def _read_document(self, path: str) -> dict[str, str] | None:
        candidate = self.vault.vault_path / path
        if not candidate.exists():
            return None
        _, body = read_frontmatter(candidate)
        return {"path": path, "content": body}

    @staticmethod
    def _task_data(task: Task, path: str) -> dict[str, object]:
        return {
            "id": task.id,
            "title": task.title,
            "path": path,
            "body": task.body,
            "context": task.context,
            "last_worked": task.last_worked.isoformat() if task.last_worked else None,
        }
