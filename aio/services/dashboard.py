"""Dashboard generation service."""

from datetime import date, datetime, timedelta
from pathlib import Path

from aio.models.task import Task, TaskStatus
from aio.services.task import TaskService
from aio.services.vault import VaultService
from aio.utils.dates import format_relative_date


class DashboardService:
    """Service for generating daily dashboards."""

    def __init__(self, vault_service: VaultService, task_service: TaskService) -> None:
        """Initialize the dashboard service.

        Args:
            vault_service: The vault service.
            task_service: The task service.
        """
        self.vault = vault_service
        self.tasks = task_service

    def generate(self, for_date: date | None = None) -> str:
        """Generate dashboard content for a date.

        Args:
            for_date: Date to generate for (default: today).

        Returns:
            Markdown content for the dashboard.
        """
        if for_date is None:
            for_date = date.today()

        # Get all active tasks
        all_tasks = self.tasks.list_tasks(include_completed=False)

        # Categorize tasks
        overdue = [t for t in all_tasks if t.due and t.due < for_date]
        due_today = [t for t in all_tasks if t.due and t.due == for_date]
        due_this_week = [
            t
            for t in all_tasks
            if t.due and for_date < t.due <= for_date + timedelta(days=7)
        ]
        waiting = [t for t in all_tasks if t.status == TaskStatus.WAITING]
        blocked = [t for t in all_tasks if t.blocked_by]

        # Group waiting by person
        waiting_by_person: dict[str, list[Task]] = {}
        for task in waiting:
            person = task.waiting_on or "Unknown"
            if person not in waiting_by_person:
                waiting_by_person[person] = []
            waiting_by_person[person].append(task)

        # Build markdown
        lines = [
            "---",
            "type: dashboard",
            f"date: {for_date.isoformat()}",
            f"generated: {datetime.now().isoformat()}",
            "---",
            "",
            f"# {for_date.strftime('%A, %B %d')}",
            "",
        ]

        # Overdue section
        if overdue:
            lines.extend(
                [
                    "## Overdue",
                    "",
                    "| Task | Due | ID |",
                    "|------|-----|------|",
                ]
            )
            for task in overdue:
                due_str = format_relative_date(task.due) if task.due else ""
                lines.append(f"| {task.title} | {due_str} | {task.id} |")
            lines.append("")

        # Due Today section
        if due_today:
            lines.extend(
                [
                    "## Due Today",
                    "",
                    "| Task | Project | ID |",
                    "|------|---------|------|",
                ]
            )
            for task in due_today:
                project = self._format_project(task.project)
                lines.append(f"| {task.title} | {project} | {task.id} |")
            lines.append("")

        # Due This Week section
        if due_this_week:
            lines.extend(
                [
                    "## Due This Week",
                    "",
                    "| Task | Due | Project | ID |",
                    "|------|-----|---------|------|",
                ]
            )
            for task in due_this_week:
                due_str = format_relative_date(task.due) if task.due else ""
                project = self._format_project(task.project)
                lines.append(f"| {task.title} | {due_str} | {project} | {task.id} |")
            lines.append("")

        # Blocked section
        if blocked:
            lines.extend(
                [
                    "## Blocked",
                    "",
                    "| Task | Blocked By | ID |",
                    "|------|------------|------|",
                ]
            )
            for task in blocked:
                blockers = ", ".join(task.blocked_by)
                lines.append(f"| {task.title} | {blockers} | {task.id} |")
            lines.append("")

        # Waiting For section
        if waiting:
            lines.extend(["---", "", "## Waiting For", ""])
            for person, tasks in waiting_by_person.items():
                person_name = self._format_person(person)
                lines.append(f"### {person_name} ({len(tasks)} items)")
                lines.append("")
                for task in tasks:
                    days = self._days_since_updated(task)
                    stale = " [STALE]" if days > 7 else ""
                    lines.append(f"- [{task.id}] {task.title} ({days}d){stale}")
                lines.append("")

        # Quick Links section
        lines.extend(
            [
                "---",
                "",
                "## Quick Links",
                "",
                "| View | Link |",
                "|------|------|",
                "| Inbox | [[AIO/Tasks/Inbox/]] |",
                "| Next Actions | [[AIO/Tasks/Next/]] |",
                "| All Projects | [[AIO/Projects/]] |",
            ]
        )

        return "\n".join(lines)

    def save(self, for_date: date | None = None) -> Path:
        """Generate and save a dashboard file.

        Args:
            for_date: Date to generate for (default: today).

        Returns:
            Path to the saved dashboard file.
        """
        if for_date is None:
            for_date = date.today()

        content = self.generate(for_date)

        folder = self.vault.dashboard_folder()
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"{for_date.isoformat()}.md"
        filepath = folder / filename
        filepath.write_text(content, encoding="utf-8")

        return filepath

    def _format_project(self, project: str | None) -> str:
        """Format a project wikilink for display."""
        if not project:
            return ""
        # Strip brackets and path
        name = project.replace("[[", "").replace("]]", "")
        if "/" in name:
            name = name.split("/")[-1]
        return name

    def _format_person(self, person: str | None) -> str:
        """Format a person wikilink for display."""
        if not person:
            return "Unknown"
        name = person.replace("[[", "").replace("]]", "")
        if "/" in name:
            name = name.split("/")[-1]
        return name

    def _days_since_updated(self, task: Task) -> int:
        """Calculate days since task was last updated."""
        delta = datetime.now() - task.updated
        return delta.days
