"""In-memory vault cache with file watching for the AIO daemon."""

import asyncio
import logging
import threading
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

from aio.models.task import Task, TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService

logger = logging.getLogger(__name__)


class VaultCache:
    """In-memory cache of vault data with file watching for invalidation.

    Provides fast lookups for tasks by ID, status, and other criteria.
    Automatically refreshes when files change in the vault.
    """

    # Debounce time in seconds for file change events
    DEBOUNCE_SECONDS = 0.1

    def __init__(
        self,
        vault_service: VaultService,
        task_service: TaskService,
    ) -> None:
        """Initialize the cache.

        Args:
            vault_service: The vault service for path operations.
            task_service: The task service for reading tasks.
        """
        self._vault_service = vault_service
        self._task_service = task_service

        # Cache storage
        self._tasks: dict[str, Task] = {}  # id -> Task
        self._tasks_by_status: dict[TaskStatus, list[str]] = {}  # status -> [ids]

        # File watching - use Any to avoid type issues with watchdog's Observer
        self._observer: BaseObserver | None = None
        self._event_handler: _CacheEventHandler | None = None

        # Debouncing for file events
        self._pending_paths: set[Path] = set()
        self._debounce_timer: threading.Timer | None = None
        self._debounce_lock = threading.Lock()

        # Track cache state
        self._is_populated = False
        self._last_refresh: float = 0
        self._task_count = 0

        # Callback for cache updates (for HTTP/socket notification)
        self._on_update_callbacks: list[Callable[[], None]] = []

    @property
    def is_populated(self) -> bool:
        """Check if the cache has been populated."""
        return self._is_populated

    @property
    def task_count(self) -> int:
        """Get the number of cached tasks."""
        return self._task_count

    def add_update_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when cache is updated.

        Args:
            callback: Function to call on cache update.
        """
        self._on_update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable[[], None]) -> None:
        """Remove an update callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._on_update_callbacks:
            self._on_update_callbacks.remove(callback)

    def _notify_update(self) -> None:
        """Notify all registered callbacks of a cache update."""
        for callback in self._on_update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error("Error in cache update callback: %s", e)

    def start(self) -> None:
        """Start file watching for cache invalidation."""
        if self._observer is not None:
            return  # Already running

        # Create event handler
        self._event_handler = _CacheEventHandler(self._on_file_change)

        # Create and start observer
        self._observer = Observer()
        tasks_path = self._vault_service.aio_path / "Tasks"

        if tasks_path.exists():
            self._observer.schedule(
                self._event_handler,
                str(tasks_path),
                recursive=True,
            )
            self._observer.start()
            logger.info("File watcher started for %s", tasks_path)
        else:
            logger.warning("Tasks folder does not exist: %s", tasks_path)

    def stop(self) -> None:
        """Stop file watching."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._event_handler = None
            logger.info("File watcher stopped")

        # Cancel any pending debounce timer
        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

    def _on_file_change(self, path: Path) -> None:
        """Handle a file change event with debouncing.

        Args:
            path: Path to the changed file.
        """
        # Only care about .md files
        if path.suffix != ".md":
            return

        with self._debounce_lock:
            self._pending_paths.add(path)

            # Cancel existing timer if any
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()

            # Start new debounce timer
            self._debounce_timer = threading.Timer(
                self.DEBOUNCE_SECONDS,
                self._process_pending_changes,
            )
            self._debounce_timer.start()

    def _process_pending_changes(self) -> None:
        """Process all pending file changes after debounce period."""
        with self._debounce_lock:
            paths = self._pending_paths.copy()
            self._pending_paths.clear()
            self._debounce_timer = None

        if paths:
            logger.debug("Processing %d file changes", len(paths))
            # For simplicity, just do a full refresh
            # A more sophisticated approach would invalidate only affected tasks
            self.refresh_sync()

    def refresh_sync(self) -> None:
        """Synchronously refresh the cache from disk."""
        logger.debug("Refreshing cache from disk")

        # Clear existing cache
        self._tasks.clear()
        self._tasks_by_status.clear()

        # Initialize status buckets
        for status in TaskStatus:
            self._tasks_by_status[status] = []

        # Load all tasks
        try:
            for status in TaskStatus:
                tasks = self._task_service.list_tasks(
                    status=status,
                    include_completed=(status == TaskStatus.COMPLETED),
                )
                for task in tasks:
                    self._tasks[task.id.upper()] = task
                    self._tasks_by_status[status].append(task.id.upper())
        except Exception as e:
            logger.error("Error refreshing cache: %s", e)
            raise

        self._task_count = len(self._tasks)
        self._is_populated = True
        try:
            loop = asyncio.get_event_loop()
            self._last_refresh = loop.time() if loop.is_running() else 0
        except RuntimeError:
            self._last_refresh = 0

        logger.info("Cache refreshed: %d tasks loaded", self._task_count)
        self._notify_update()

    async def refresh(self) -> None:
        """Asynchronously refresh the cache from disk.

        Runs the sync refresh in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.refresh_sync)

    def invalidate_task(self, task_id: str) -> None:
        """Invalidate a specific task in the cache.

        Args:
            task_id: The task ID to invalidate.
        """
        task_id = task_id.upper()

        # Remove from main cache
        old_task = self._tasks.pop(task_id, None)

        # Remove from status index
        if old_task:
            status = old_task.status
            if task_id in self._tasks_by_status.get(status, []):
                self._tasks_by_status[status].remove(task_id)

        # Try to reload the task
        try:
            task = self._task_service.get(task_id)
            self._tasks[task_id] = task
            self._tasks_by_status[task.status].append(task_id)
        except Exception:
            # Task may have been deleted
            pass

        self._task_count = len(self._tasks)
        self._notify_update()

    # Fast lookup methods

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID from the cache.

        Args:
            task_id: The task ID to look up.

        Returns:
            The task, or None if not found.
        """
        return self._tasks.get(task_id.upper())

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """List tasks, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of matching tasks.
        """
        if status is not None:
            task_ids = self._tasks_by_status.get(status, [])
            return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

        # Return all tasks except completed and someday by default
        # (matches TaskService.list_tasks() behavior)
        result: list[Task] = []
        for s in TaskStatus:
            if s not in (TaskStatus.COMPLETED, TaskStatus.SOMEDAY):
                task_ids = self._tasks_by_status.get(s, [])
                result.extend(self._tasks[tid] for tid in task_ids if tid in self._tasks)
        return result

    def list_tasks_today(self) -> list[Task]:
        """List tasks due today or overdue.

        Returns:
            List of tasks due today or overdue.
        """
        today = date.today()
        result = []
        for task in self._tasks.values():
            if task.status != TaskStatus.COMPLETED and task.due and task.due <= today:
                result.append(task)
        return sorted(result, key=lambda t: (t.due or date.max, t.created))

    def list_tasks_overdue(self) -> list[Task]:
        """List overdue tasks.

        Returns:
            List of overdue tasks.
        """
        today = date.today()
        result = []
        for task in self._tasks.values():
            if task.status != TaskStatus.COMPLETED and task.due and task.due < today:
                result.append(task)
        return sorted(result, key=lambda t: (t.due or date.max, t.created))

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        status_counts = {
            status.value: len(ids)
            for status, ids in self._tasks_by_status.items()
        }
        return {
            "total_tasks": self._task_count,
            "is_populated": self._is_populated,
            "watching": self._observer is not None,
            "by_status": status_counts,
        }


class _CacheEventHandler(FileSystemEventHandler):
    """Watchdog event handler for cache invalidation."""

    def __init__(self, callback: Callable[[Path], None]) -> None:
        """Initialize the event handler.

        Args:
            callback: Function to call with the path of changed files.
        """
        super().__init__()
        self._callback = callback

    def _to_path(self, src_path: bytes | str) -> Path:
        """Convert src_path to Path, handling bytes or str."""
        if isinstance(src_path, bytes):
            return Path(src_path.decode("utf-8"))
        return Path(src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if not event.is_directory:
            self._callback(self._to_path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if not event.is_directory:
            self._callback(self._to_path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if not event.is_directory:
            self._callback(self._to_path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename."""
        if not event.is_directory:
            self._callback(self._to_path(event.src_path))
            if hasattr(event, "dest_path"):
                self._callback(self._to_path(event.dest_path))
