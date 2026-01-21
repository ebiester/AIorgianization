"""Task service for CRUD operations on task markdown files."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from aio.exceptions import AmbiguousMatchError, TaskNotFoundError
from aio.models.task import Task, TaskLocation, TaskStatus
from aio.services.id_service import EntityType, IdService
from aio.services.vault import VaultService
from aio.utils.frontmatter import read_frontmatter, write_frontmatter
from aio.utils.ids import is_valid_id, normalize_id

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task CRUD operations."""

    def __init__(self, vault_service: VaultService) -> None:
        """Initialize the task service.

        Args:
            vault_service: The vault service for file operations.
        """
        self.vault = vault_service
        self._id_service = IdService(vault_service)

    def create(
        self,
        title: str,
        due: date | None = None,
        project: str | None = None,
        status: TaskStatus = TaskStatus.INBOX,
        tags: list[str] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title.
            due: Optional due date.
            project: Optional project wikilink.
            status: Initial status (default: inbox).
            tags: Optional list of tags.

        Returns:
            The created task.
        """
        self.vault.ensure_initialized()

        # Generate unique ID
        task_id = self._generate_unique_id()

        now = datetime.now()
        task = Task(
            id=task_id,
            title=title,
            status=status,
            due=due,
            project=project,
            tags=tags or [],
            created=now,
            updated=now,
        )

        # Generate content
        body = f"# {title}\n\n## Notes\n"
        task.body = body

        # Write file
        folder = self.vault.tasks_folder(status.value)
        filename = task.generate_filename()
        filepath = folder / filename

        write_frontmatter(filepath, task.frontmatter(), body)

        return task

    def get(self, task_id: str) -> Task:
        """Get a task by ID.

        Args:
            task_id: The 4-character task ID.

        Returns:
            The task.

        Raises:
            TaskNotFoundError: If the task is not found.
        """
        task_id = normalize_id(task_id)
        filepath = self._find_task_file_by_id(task_id)
        if not filepath:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return self._read_task_file(filepath)

    def find(self, query: str) -> Task:
        """Find a task by ID or title substring.

        Args:
            query: Task ID (4 chars) or title substring.

        Returns:
            The matching task.

        Raises:
            TaskNotFoundError: If no task matches.
            AmbiguousMatchError: If multiple tasks match.
        """
        # If it looks like an ID, try ID lookup first
        if is_valid_id(query):
            try:
                return self.get(query)
            except TaskNotFoundError:
                pass  # Fall through to title search

        # Search by title
        matches = self._find_tasks_by_title(query)
        if not matches:
            raise TaskNotFoundError(f"No task found matching: {query}")
        if len(matches) > 1:
            raise AmbiguousMatchError(query, [t.id for t in matches])
        return matches[0]

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        project: str | None = None,
        include_completed: bool = False,
    ) -> list[Task]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status.
            project: Filter by project (wikilink or path).
            include_completed: Include completed tasks.

        Returns:
            List of matching tasks.
        """
        self.vault.ensure_initialized()
        tasks: list[Task] = []

        # Determine which status folders to search
        if status:
            statuses = [status]
        else:
            # Default view excludes completed and someday (deferred) tasks
            statuses = list(TaskStatus)
            statuses = [s for s in statuses if s not in (TaskStatus.COMPLETED, TaskStatus.SOMEDAY)]
            if include_completed:
                statuses.append(TaskStatus.COMPLETED)

        for s in statuses:
            folder = self.vault.tasks_folder(s.value)
            if folder.exists():
                tasks.extend(self._read_tasks_from_folder(folder))

            # For completed, also search year/month subfolders
            if s == TaskStatus.COMPLETED and include_completed:
                completed_base = folder
                if completed_base.exists():
                    for year_dir in completed_base.iterdir():
                        if year_dir.is_dir() and year_dir.name.isdigit():
                            for month_dir in year_dir.iterdir():
                                if month_dir.is_dir():
                                    tasks.extend(self._read_tasks_from_folder(month_dir))

        # Filter by project if specified
        if project:
            tasks = [t for t in tasks if self._matches_project(t, project)]

        # Sort by due date (None last), then by created
        def sort_key(t: Task) -> tuple[int, date, datetime]:
            due_sort = t.due if t.due else date.max
            return (0 if t.due else 1, due_sort, t.created)

        tasks.sort(key=sort_key)
        return tasks

    def list_today(self) -> list[Task]:
        """List tasks due today or overdue.

        Returns:
            List of tasks due today or overdue.
        """
        tasks = self.list_tasks(include_completed=False)
        today = date.today()
        return [t for t in tasks if t.due and t.due <= today]

    def list_overdue(self) -> list[Task]:
        """List overdue tasks.

        Returns:
            List of overdue tasks.
        """
        tasks = self.list_tasks(include_completed=False)
        today = date.today()
        return [t for t in tasks if t.due and t.due < today]

    def complete(self, query: str) -> Task:
        """Mark a task as completed.

        Args:
            query: Task ID or title substring.

        Returns:
            The updated task.
        """
        task = self.find(query)
        return self._update_status(task, TaskStatus.COMPLETED)

    def start(self, query: str) -> Task:
        """Move a task to Next status.

        Args:
            query: Task ID or title substring.

        Returns:
            The updated task.
        """
        task = self.find(query)
        return self._update_status(task, TaskStatus.NEXT)

    def defer(self, query: str) -> Task:
        """Move a task to Someday status.

        Args:
            query: Task ID or title substring.

        Returns:
            The updated task.
        """
        task = self.find(query)
        return self._update_status(task, TaskStatus.SOMEDAY)

    def wait(self, query: str, person: str | None = None) -> Task:
        """Move a task to Waiting status.

        Args:
            query: Task ID or title substring.
            person: Optional person wikilink to set as waitingOn.

        Returns:
            The updated task.
        """
        task = self.find(query)
        if person:
            # Format as wikilink if not already
            if not person.startswith("[["):
                person = f"[[People/{person}]]"
            task.waiting_on = person
        return self._update_status(task, TaskStatus.WAITING)

    def archive(self, query: str) -> Task:
        """Archive a task.

        Args:
            query: Task ID or title substring.

        Returns:
            The archived task.
        """
        task = self.find(query)
        old_filepath = self._find_task_file_by_id(task.id)
        if not old_filepath:
            raise TaskNotFoundError(f"Task file not found: {task.id}")

        # Determine archive folder
        archive_folder = self.vault.archive_folder("Tasks", task.status)
        archive_folder.mkdir(parents=True, exist_ok=True)

        # Move file
        new_filepath = archive_folder / old_filepath.name

        # Update task with archive metadata
        task.updated = datetime.now()
        write_frontmatter(new_filepath, task.frontmatter(), task.body)
        old_filepath.unlink()

        return task

    def _update_status(self, task: Task, new_status: TaskStatus) -> Task:
        """Update a task's status and move its file.

        Args:
            task: The task to update.
            new_status: The new status.

        Returns:
            The updated task.
        """
        old_filepath = self._find_task_file_by_id(task.id)
        if not old_filepath:
            raise TaskNotFoundError(f"Task file not found: {task.id}")

        # Update task
        task.status = new_status
        task.updated = datetime.now()

        if new_status == TaskStatus.COMPLETED:
            task.completed = datetime.now()

        # Determine new folder
        if new_status == TaskStatus.COMPLETED:
            now = datetime.now()
            new_folder = self.vault.completed_folder(now.year, now.month)
        else:
            new_folder = self.vault.tasks_folder(new_status.value)

        new_folder.mkdir(parents=True, exist_ok=True)
        new_filepath = new_folder / old_filepath.name

        # Write to new location and remove old
        write_frontmatter(new_filepath, task.frontmatter(), task.body)
        if old_filepath != new_filepath:
            old_filepath.unlink()

        return task

    def _generate_unique_id(self) -> str:
        """Generate a unique task ID.

        Delegates to IdService for collision detection.

        Returns:
            A unique 4-character ID.
        """
        return self._id_service.generate_unique_id(EntityType.TASK)

    def _find_task_file_by_id(self, task_id: str) -> Path | None:
        """Find a task file by its ID.

        Args:
            task_id: The task ID to find.

        Returns:
            Path to the task file, or None if not found.
        """
        task_id = task_id.upper()

        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    try:
                        metadata, _ = read_frontmatter(filepath)
                        if metadata.get("id", "").upper() == task_id:
                            return filepath
                    except Exception as e:
                        logger.debug("Failed to read task file %s: %s", filepath, e)

            # Also search completed subfolders
            if status == TaskStatus.COMPLETED:
                completed_base = folder
                if completed_base.exists():
                    for year_dir in completed_base.iterdir():
                        if year_dir.is_dir() and year_dir.name.isdigit():
                            for month_dir in year_dir.iterdir():
                                if month_dir.is_dir():
                                    for filepath in month_dir.glob("*.md"):
                                        try:
                                            metadata, _ = read_frontmatter(filepath)
                                            if metadata.get("id", "").upper() == task_id:
                                                return filepath
                                        except Exception as e:
                                            logger.debug(
                                                "Failed to read task file %s: %s", filepath, e
                                            )

        return None

    def _find_tasks_by_title(self, query: str) -> list[Task]:
        """Find tasks by title substring.

        Args:
            query: Title substring to search for.

        Returns:
            List of matching tasks.
        """
        query_lower = query.lower()
        matches: list[Task] = []

        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    try:
                        task = self._read_task_file(filepath)
                        if query_lower in task.title.lower():
                            matches.append(task)
                    except Exception as e:
                        logger.debug("Failed to read task file %s: %s", filepath, e)

        return matches

    def _read_task_file(self, filepath: Path) -> Task:
        """Read a task from a markdown file.

        Args:
            filepath: Path to the task file.

        Returns:
            The parsed task.
        """
        metadata, content = read_frontmatter(filepath)

        # Extract title from first H1 heading or filename
        title = self._extract_title(content, filepath)

        # Parse location if present
        location = None
        if "location" in metadata and metadata["location"]:
            location = TaskLocation(**metadata["location"])

        # Parse dates
        due = None
        if "due" in metadata and metadata["due"]:
            due_val = metadata["due"]
            if isinstance(due_val, date):
                due = due_val
            elif isinstance(due_val, str):
                due = date.fromisoformat(due_val)

        created = self._parse_datetime(metadata.get("created"), datetime.now())
        updated = self._parse_datetime(metadata.get("updated"), datetime.now())
        completed = self._parse_datetime(metadata.get("completed"), None)

        return Task(
            id=metadata.get("id", "????"),
            type=metadata.get("type", "task"),
            status=TaskStatus(metadata.get("status", "inbox")),
            title=title,
            body=content,
            due=due,
            project=metadata.get("project"),
            assigned_to=metadata.get("assignedTo"),
            waiting_on=metadata.get("waitingOn"),
            blocked_by=metadata.get("blockedBy", []),
            blocks=metadata.get("blocks", []),
            location=location,
            tags=metadata.get("tags", []),
            time_estimate=metadata.get("timeEstimate"),
            jira_key=metadata.get("jiraKey"),
            created=created,
            updated=updated,
            completed=completed,
        )

    def _extract_title(self, content: str, filepath: Path) -> str:
        """Extract title from content or filename.

        Args:
            content: Markdown content.
            filepath: Path to use as fallback.

        Returns:
            The task title.
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fall back to filename
        name = filepath.stem
        # Remove date prefix if present (YYYY-MM-DD-)
        if len(name) > 11 and name[4] == "-" and name[7] == "-":
            name = name[11:]
        return name.replace("-", " ").title()

    def _read_tasks_from_folder(self, folder: Path) -> list[Task]:
        """Read all tasks from a folder.

        Args:
            folder: Folder to read from.

        Returns:
            List of tasks.
        """
        tasks: list[Task] = []
        for filepath in folder.glob("*.md"):
            try:
                tasks.append(self._read_task_file(filepath))
            except Exception as e:
                logger.debug("Failed to read task file %s: %s", filepath, e)
        return tasks

    def _matches_project(self, task: Task, project: str) -> bool:
        """Check if a task matches a project filter.

        Args:
            task: The task to check.
            project: Project name or wikilink.

        Returns:
            True if the task matches.
        """
        if not task.project:
            return False

        project_lower = project.lower()
        task_project_lower = task.project.lower()

        # Match wikilink or plain name
        return project_lower in task_project_lower

    def _parse_datetime(
        self, value: Any, default: datetime | None
    ) -> datetime | None:
        """Parse a datetime value, ensuring it's naive (no timezone).

        Args:
            value: The value to parse (datetime, str, or None).
            default: Default value if parsing fails or value is None.

        Returns:
            Naive datetime or None.
        """
        if value is None:
            return default

        result: datetime | None = None
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            # Handle 'Z' suffix for UTC
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if result is not None and result.tzinfo is not None:
            # Convert to naive datetime for consistent comparison
            result = result.replace(tzinfo=None)

        return result if result is not None else default
