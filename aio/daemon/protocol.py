"""JSON-RPC 2.0 protocol types and error codes for the AIO daemon."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """JSON-RPC 2.0 error codes.

    Standard codes (-32700 to -32600) plus application-specific codes (-32001 to -32099).
    """

    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = -32700  # Invalid JSON
    INVALID_REQUEST = -32600  # Not a valid request object
    METHOD_NOT_FOUND = -32601  # Method does not exist
    INVALID_PARAMS = -32602  # Invalid method parameters
    INTERNAL_ERROR = -32603  # Internal JSON-RPC error

    # Application-specific errors
    TASK_NOT_FOUND = -32001
    AMBIGUOUS_MATCH = -32002
    VAULT_NOT_FOUND = -32003
    INVALID_DATE = -32004
    VAULT_NOT_INITIALIZED = -32005
    PROJECT_NOT_FOUND = -32006
    PERSON_NOT_FOUND = -32007
    CONTEXT_PACK_NOT_FOUND = -32008
    CONTEXT_PACK_EXISTS = -32009
    FILE_OUTSIDE_VAULT = -32010


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 request object."""

    method: str
    jsonrpc: str = "2.0"
    id: int | str | None = None
    params: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcRequest":
        """Parse a request from a dictionary.

        Args:
            data: Dictionary containing request data.

        Returns:
            Parsed JsonRpcRequest.

        Raises:
            ValueError: If required fields are missing.
        """
        if "method" not in data:
            raise ValueError("Missing required field: method")

        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data["method"],
            params=data.get("params"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.id is not None:
            result["id"] = self.id
        if self.params is not None:
            result["params"] = self.params
        return result


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 response object."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: Any = None
    error: JsonRpcError | None = None

    @classmethod
    def success(cls, result: Any, request_id: int | str | None = None) -> "JsonRpcResponse":
        """Create a success response.

        Args:
            result: The result data.
            request_id: The request ID to echo back.

        Returns:
            Success response.
        """
        return cls(id=request_id, result=result)

    @classmethod
    def error_response(
        cls,
        code: int | ErrorCode,
        message: str,
        data: Any = None,
        request_id: int | str | None = None,
    ) -> "JsonRpcResponse":
        """Create an error response.

        Args:
            code: Error code.
            message: Error message.
            data: Optional additional data.
            request_id: The request ID to echo back.

        Returns:
            Error response.
        """
        error = JsonRpcError(
            code=int(code),
            message=message,
            data=data,
        )
        return cls(id=request_id, error=error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            result["error"] = self.error.to_dict()
        else:
            result["result"] = self.result
        return result


# Map exception types to error codes
EXCEPTION_TO_ERROR_CODE: dict[str, ErrorCode] = {
    "TaskNotFoundError": ErrorCode.TASK_NOT_FOUND,
    "AmbiguousMatchError": ErrorCode.AMBIGUOUS_MATCH,
    "VaultNotFoundError": ErrorCode.VAULT_NOT_FOUND,
    "InvalidDateError": ErrorCode.INVALID_DATE,
    "VaultNotInitializedError": ErrorCode.VAULT_NOT_INITIALIZED,
    "ProjectNotFoundError": ErrorCode.PROJECT_NOT_FOUND,
    "PersonNotFoundError": ErrorCode.PERSON_NOT_FOUND,
    "ContextPackNotFoundError": ErrorCode.CONTEXT_PACK_NOT_FOUND,
    "ContextPackExistsError": ErrorCode.CONTEXT_PACK_EXISTS,
    "FileOutsideVaultError": ErrorCode.FILE_OUTSIDE_VAULT,
}


def exception_to_error_code(exc: Exception) -> ErrorCode:
    """Map an exception to its corresponding error code.

    Args:
        exc: The exception to map.

    Returns:
        The corresponding error code.
    """
    exc_type = type(exc).__name__
    return EXCEPTION_TO_ERROR_CODE.get(exc_type, ErrorCode.INTERNAL_ERROR)
