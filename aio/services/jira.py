"""Jira synchronization service.

Handles syncing Jira issues to local task files in the vault.
"""

import contextlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from aio.exceptions import JiraAuthError, JiraConfigError, JiraSyncError
from aio.models.jira import JiraConfig, JiraIssue, JiraSyncState, SyncResult
from aio.models.task import Task, TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService

# Status mapping from Jira to local task folders
# Maps common Jira status names (case-insensitive) to TaskStatus
JIRA_STATUS_MAP: dict[str, TaskStatus] = {
    # To Do statuses
    "to do": TaskStatus.INBOX,
    "backlog": TaskStatus.INBOX,
    "open": TaskStatus.INBOX,
    "new": TaskStatus.INBOX,
    # In Progress statuses
    "in progress": TaskStatus.NEXT,
    "in development": TaskStatus.NEXT,
    "started": TaskStatus.NEXT,
    "active": TaskStatus.NEXT,
    # Review/Waiting statuses
    "in review": TaskStatus.WAITING,
    "code review": TaskStatus.WAITING,
    "review": TaskStatus.WAITING,
    "blocked": TaskStatus.WAITING,
    "waiting": TaskStatus.WAITING,
    "waiting for info": TaskStatus.WAITING,
    "pending": TaskStatus.WAITING,
    # Done statuses
    "done": TaskStatus.COMPLETED,
    "closed": TaskStatus.COMPLETED,
    "resolved": TaskStatus.COMPLETED,
    "complete": TaskStatus.COMPLETED,
    "completed": TaskStatus.COMPLETED,
}


class JiraSyncService:
    """Service for syncing Jira issues to local task files."""

    def __init__(self, vault_service: VaultService, task_service: TaskService) -> None:
        """Initialize the Jira sync service.

        Args:
            vault_service: The vault service for config and file operations.
            task_service: The task service for task CRUD operations.
        """
        self.vault = vault_service
        self.tasks = task_service
        self._jira_client: Any | None = None

    @property
    def config(self) -> JiraConfig:
        """Get the Jira configuration from vault config.

        Returns:
            JiraConfig instance.
        """
        vault_config = self.vault.get_config()
        jira_config = vault_config.get("jira", {})
        return JiraConfig(**jira_config)

    @property
    def cache_path(self) -> Path:
        """Get the path to the Jira sync cache file."""
        return self.vault.config_path / "jira-cache.json"

    def get_sync_state(self) -> JiraSyncState:
        """Load the sync state from cache.

        Returns:
            JiraSyncState instance.
        """
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return JiraSyncState(**data)
            except Exception:
                pass
        return JiraSyncState()

    def save_sync_state(self, state: JiraSyncState) -> None:
        """Save the sync state to cache.

        Args:
            state: The sync state to save.
        """
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(by_alias=True, mode="json"), f, indent=2, default=str)

    def get_jira_client(self) -> Any:
        """Get or create the Jira client.

        Returns:
            Configured JIRA client instance.

        Raises:
            JiraConfigError: If Jira is not configured.
            JiraAuthError: If authentication fails.
        """
        if self._jira_client is not None:
            return self._jira_client

        config = self.config
        if not config.is_configured():
            missing = []
            if not config.base_url:
                missing.append("baseUrl")
            if not config.email:
                missing.append("email")
            if not config.projects:
                missing.append("projects")
            raise JiraConfigError(
                f"Jira not configured. Missing: {', '.join(missing)}. "
                "Run 'aio config set jira.<field> <value>' to configure."
            )

        # Get API token from environment
        api_token = os.environ.get("JIRA_API_TOKEN")
        if not api_token:
            raise JiraConfigError(
                "JIRA_API_TOKEN environment variable not set. "
                "Set it with: export JIRA_API_TOKEN=your-token"
            )

        try:
            from jira import JIRA

            self._jira_client = JIRA(
                server=config.base_url,
                basic_auth=(config.email, api_token),
            )
            # Test the connection
            self._jira_client.myself()
            return self._jira_client
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise JiraAuthError(
                    "Jira authentication failed. Check your email and API token."
                ) from e
            if "404" in error_msg or "Not Found" in error_msg:
                raise JiraConfigError(
                    f"Jira server not found at {config.base_url}. Check the URL."
                ) from e
            raise JiraSyncError(f"Failed to connect to Jira: {error_msg}") from e

    def fetch_assigned_issues(self) -> list[JiraIssue]:
        """Fetch all issues assigned to the current user.

        Returns:
            List of JiraIssue objects.

        Raises:
            JiraSyncError: If fetching fails.
        """
        config = self.config
        jira = self.get_jira_client()

        # Build JQL query
        project_filter = ", ".join(f'"{p}"' for p in config.projects)
        jql = f"assignee = currentUser() AND project IN ({project_filter}) AND status != Done"

        try:
            issues = jira.search_issues(
                jql,
                maxResults=500,  # Reasonable limit
                fields="summary,status,issuetype,priority,assignee,duedate,project,"
                "description,labels,parent,updated",
            )

            return [
                JiraIssue.from_jira_issue(issue, config.base_url or "")
                for issue in issues
            ]
        except Exception as e:
            raise JiraSyncError(f"Failed to fetch issues: {e}") from e

    def map_jira_status(self, jira_status: str) -> TaskStatus:
        """Map a Jira status to a local TaskStatus.

        Args:
            jira_status: The Jira status name.

        Returns:
            Corresponding TaskStatus.
        """
        status_lower = jira_status.lower().strip()
        return JIRA_STATUS_MAP.get(status_lower, TaskStatus.INBOX)

    def find_task_by_jira_key(self, jira_key: str) -> Task | None:
        """Find a local task by its Jira key.

        Args:
            jira_key: The Jira issue key (e.g., PLAT-123).

        Returns:
            The Task if found, None otherwise.
        """
        # Search all task folders for matching jiraKey
        for status in TaskStatus:
            folder = self.vault.tasks_folder(status.value)
            if folder.exists():
                for filepath in folder.glob("*.md"):
                    try:
                        task = self.tasks._read_task_file(filepath)
                        if task.jira_key and task.jira_key.upper() == jira_key.upper():
                            return task
                    except Exception:
                        continue

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
                                            task = self.tasks._read_task_file(filepath)
                                            if (
                                                task.jira_key
                                                and task.jira_key.upper() == jira_key.upper()
                                            ):
                                                return task
                                        except Exception:
                                            continue
        return None

    def create_task_from_issue(self, issue: JiraIssue) -> Task:
        """Create a new task from a Jira issue.

        Args:
            issue: The Jira issue to create a task from.

        Returns:
            The created Task.
        """
        # Parse due date
        due_date: date | None = None
        if issue.due_date:
            with contextlib.suppress(ValueError):
                due_date = date.fromisoformat(issue.due_date)

        # Determine status
        status = self.map_jira_status(issue.status)

        # Build task body
        body_parts = [f"# {issue.summary}", ""]

        if issue.description:
            body_parts.append("## Description")
            body_parts.append(issue.description)
            body_parts.append("")

        body_parts.append("## Jira Info")
        body_parts.append(f"- **Issue:** [{issue.key}]({issue.url})")
        body_parts.append(f"- **Type:** {issue.issue_type}")
        body_parts.append(f"- **Status:** {issue.status}")
        if issue.priority:
            body_parts.append(f"- **Priority:** {issue.priority}")
        if issue.epic_key:
            body_parts.append(f"- **Epic:** {issue.epic_key}")
        body_parts.append("")
        body_parts.append("## Notes")
        body_parts.append("")

        body = "\n".join(body_parts)

        # Create the task
        task = self.tasks.create(
            title=issue.summary,
            due=due_date,
            status=status,
            tags=issue.labels,
        )

        # Update with Jira-specific fields
        task.jira_key = issue.key
        task.body = body

        # Write the updated task
        folder = self.vault.tasks_folder(status.value)
        filepath = folder / task.generate_filename()
        from aio.utils.frontmatter import write_frontmatter

        write_frontmatter(filepath, task.frontmatter(), body)

        return task

    def update_task_from_issue(self, task: Task, issue: JiraIssue) -> tuple[Task, bool]:
        """Update an existing task from a Jira issue.

        Args:
            task: The existing task to update.
            issue: The Jira issue with updated data.

        Returns:
            Tuple of (updated task, whether status changed).
        """
        old_status = task.status
        new_status = self.map_jira_status(issue.status)

        # Update fields from Jira (Jira wins)
        old_title = task.title
        task.title = issue.summary

        # Update the H1 header in the body if title changed
        if old_title != task.title and task.body:
            lines = task.body.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("# "):
                    lines[i] = f"# {task.title}"
                    break
            task.body = "\n".join(lines)

        # Update due date
        if issue.due_date:
            with contextlib.suppress(ValueError):
                task.due = date.fromisoformat(issue.due_date)
        else:
            task.due = None

        # Update tags (merge with existing)
        existing_tags = set(task.tags)
        jira_tags = set(issue.labels)
        task.tags = list(existing_tags | jira_tags)

        task.updated = datetime.now()

        status_changed = old_status != new_status

        if status_changed:
            # Move the task to the new status folder
            task = self.tasks._update_status(task, new_status)
        else:
            # Just update in place
            filepath = self.tasks._find_task_file_by_id(task.id)
            if filepath:
                from aio.utils.frontmatter import write_frontmatter

                write_frontmatter(filepath, task.frontmatter(), task.body)

        return task, status_changed

    def sync(self, dry_run: bool = False) -> SyncResult:
        """Perform a full sync of Jira issues.

        Args:
            dry_run: If True, don't make any changes, just report what would happen.

        Returns:
            SyncResult with statistics.
        """
        self.vault.ensure_initialized()
        result = SyncResult()
        state = self.get_sync_state()

        try:
            issues = self.fetch_assigned_issues()
        except Exception as e:
            result.errors.append(str(e))
            return result

        for issue in issues:
            try:
                existing_task = self.find_task_by_jira_key(issue.key)

                if existing_task is None:
                    # Create new task
                    if not dry_run:
                        task = self.create_task_from_issue(issue)
                        result.created_tasks.append(task.id)
                        state.synced_issues[issue.key] = datetime.now()
                    result.created += 1
                else:
                    # Check if we need to update
                    last_sync = state.synced_issues.get(issue.key)
                    if last_sync is None or issue.updated > last_sync:
                        if not dry_run:
                            task, moved = self.update_task_from_issue(existing_task, issue)
                            result.updated_tasks.append(task.id)
                            state.synced_issues[issue.key] = datetime.now()
                            if moved:
                                result.moved += 1
                        result.updated += 1
                    else:
                        result.skipped += 1

            except Exception as e:
                result.errors.append(f"{issue.key}: {e}")

        # Update sync state
        if not dry_run:
            state.last_sync = datetime.now()
            state.errors = result.errors[-10:]  # Keep last 10 errors
            self.save_sync_state(state)

        return result

    def get_status(self) -> dict[str, Any]:
        """Get the current sync status.

        Returns:
            Dictionary with sync status information.
        """
        config = self.config
        state = self.get_sync_state()

        return {
            "enabled": config.enabled,
            "configured": config.is_configured(),
            "base_url": config.base_url,
            "email": config.email,
            "projects": config.projects,
            "last_sync": state.last_sync.isoformat() if state.last_sync else None,
            "synced_count": len(state.synced_issues),
            "recent_errors": state.errors,
        }
