"""Custom exceptions for AIorgianization."""


class AioError(Exception):
    """Base exception for AIorgianization errors."""

    pass


class VaultNotFoundError(AioError):
    """Raised when the vault cannot be found."""

    pass


class VaultNotInitializedError(AioError):
    """Raised when the vault has not been initialized with AIO structure."""

    pass


class TaskNotFoundError(AioError):
    """Raised when a task cannot be found by ID or query."""

    pass


class AmbiguousMatchError(AioError):
    """Raised when a query matches multiple tasks."""

    def __init__(self, query: str, matches: list[str]) -> None:
        self.query = query
        self.matches = matches
        super().__init__(f"Query '{query}' matches multiple tasks: {', '.join(matches)}")


class InvalidTaskIdError(AioError):
    """Raised when an invalid task ID is provided."""

    pass


class InvalidDateError(AioError):
    """Raised when a date string cannot be parsed."""

    pass


class ProjectNotFoundError(AioError):
    """Raised when a project cannot be found."""

    def __init__(self, project: str, suggestions: list[str] | None = None) -> None:
        self.project = project
        self.suggestions = suggestions or []
        msg = f"Project not found: {project}"
        if self.suggestions:
            msg += "\n\nDid you mean?\n  - " + "\n  - ".join(self.suggestions)
        super().__init__(msg)


class PersonNotFoundError(AioError):
    """Raised when a person cannot be found."""

    pass


class JiraError(AioError):
    """Base exception for Jira-related errors."""

    pass


class JiraAuthError(JiraError):
    """Raised when Jira authentication fails."""

    pass


class JiraConfigError(JiraError):
    """Raised when Jira configuration is missing or invalid."""

    pass


class JiraSyncError(JiraError):
    """Raised when Jira sync fails."""

    def __init__(self, message: str, failed_issues: list[str] | None = None) -> None:
        self.failed_issues = failed_issues or []
        super().__init__(message)


class ContextPackNotFoundError(AioError):
    """Raised when a context pack cannot be found."""

    pass


class ContextPackExistsError(AioError):
    """Raised when trying to create a context pack that already exists."""

    pass
