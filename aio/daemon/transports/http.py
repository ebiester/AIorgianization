"""HTTP REST API transport for the AIO daemon.

Provides a REST API for the Obsidian plugin and other HTTP clients.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import web

from aio.daemon.protocol import ErrorCode, JsonRpcRequest, JsonRpcResponse

logger = logging.getLogger(__name__)


class HttpTransport:
    """HTTP REST API transport using aiohttp.

    Provides REST endpoints that map to JSON-RPC methods:
    - GET /api/v1/health -> daemon health check
    - GET /api/v1/tasks -> list_tasks
    - POST /api/v1/tasks -> add_task
    - GET /api/v1/tasks/{id} -> get_task
    - POST /api/v1/tasks/{id}/complete -> complete_task
    - POST /api/v1/tasks/{id}/start -> start_task
    - POST /api/v1/tasks/{id}/defer -> defer_task
    - POST /api/v1/tasks/{id}/delegate -> delegate_task
    - GET /api/v1/projects -> list_projects
    - POST /api/v1/projects -> create_project
    - GET /api/v1/people -> list_people
    - POST /api/v1/people -> create_person
    - GET /api/v1/dashboard -> get_dashboard
    - GET /api/v1/context-packs -> list_context_packs
    - POST /api/v1/context-packs -> create_context_pack
    - POST /api/v1/rpc -> raw JSON-RPC endpoint

    Response format:
    - Success: {"ok": true, "data": {...}}
    - Error: {"ok": false, "error": {"code": "ERROR_CODE", "message": "..."}}
    """

    def __init__(
        self,
        host: str,
        port: int,
        handler: Callable[[JsonRpcRequest], Awaitable[JsonRpcResponse]],
        health_check: Callable[[], dict[str, Any]],
    ) -> None:
        """Initialize the HTTP transport.

        Args:
            host: Host to bind to.
            port: Port to listen on.
            handler: Async function to handle JSON-RPC requests.
            health_check: Function to get health status.
        """
        self._host = host
        self._port = port
        self._handler = handler
        self._health_check = health_check
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def url(self) -> str:
        """Get the base URL of the server."""
        return f"http://{self._host}:{self._port}"

    @property
    def is_running(self) -> bool:
        """Check if the transport is running."""
        return self._site is not None

    async def start(self) -> None:
        """Start the HTTP server."""
        # Create application
        self._app = web.Application()
        self._setup_routes()

        # Start server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        logger.info("HTTP API listening at %s", self.url)

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner:
            await self._runner.cleanup()
        self._site = None
        self._runner = None
        self._app = None
        logger.info("HTTP server stopped")

    def _setup_routes(self) -> None:
        """Set up API routes."""
        if self._app is None:
            return

        router = self._app.router

        # Health check
        router.add_get("/api/v1/health", self._handle_health)

        # Tasks
        router.add_get("/api/v1/tasks", self._handle_list_tasks)
        router.add_post("/api/v1/tasks", self._handle_add_task)
        router.add_get("/api/v1/tasks/{id}", self._handle_get_task)
        router.add_post("/api/v1/tasks/{id}/complete", self._handle_complete_task)
        router.add_post("/api/v1/tasks/{id}/start", self._handle_start_task)
        router.add_post("/api/v1/tasks/{id}/defer", self._handle_defer_task)
        router.add_post("/api/v1/tasks/{id}/delegate", self._handle_delegate_task)

        # Projects
        router.add_get("/api/v1/projects", self._handle_list_projects)
        router.add_post("/api/v1/projects", self._handle_create_project)

        # People
        router.add_get("/api/v1/people", self._handle_list_people)
        router.add_post("/api/v1/people", self._handle_create_person)

        # Dashboard
        router.add_get("/api/v1/dashboard", self._handle_get_dashboard)

        # Context packs
        router.add_get("/api/v1/context-packs", self._handle_list_context_packs)
        router.add_post("/api/v1/context-packs", self._handle_create_context_pack)
        router.add_post("/api/v1/context-packs/{id}/content", self._handle_add_to_context_pack)

        # Files
        router.add_get("/api/v1/files", self._handle_file_get)
        router.add_post("/api/v1/files", self._handle_file_set)

        # Raw JSON-RPC endpoint
        router.add_post("/api/v1/rpc", self._handle_rpc)

    # Response helpers

    def _success_response(self, data: Any) -> web.Response:
        """Create a success response."""
        return web.json_response({"ok": True, "data": data})

    def _error_response(
        self,
        code: str,
        message: str,
        status: int = 400,
    ) -> web.Response:
        """Create an error response."""
        return web.json_response(
            {"ok": False, "error": {"code": code, "message": message}},
            status=status,
        )

    def _rpc_error_to_response(self, response: JsonRpcResponse) -> web.Response:
        """Convert a JSON-RPC error response to an HTTP error response."""
        if response.error is None:
            return self._success_response(response.result)

        # Map error codes to HTTP status codes
        code = response.error.code
        if code == ErrorCode.METHOD_NOT_FOUND:
            status = 404
        elif code == ErrorCode.INVALID_PARAMS or code == ErrorCode.INVALID_REQUEST:
            status = 400
        elif code in (ErrorCode.TASK_NOT_FOUND, ErrorCode.PROJECT_NOT_FOUND,
                      ErrorCode.PERSON_NOT_FOUND, ErrorCode.CONTEXT_PACK_NOT_FOUND):
            status = 404
        elif code == ErrorCode.AMBIGUOUS_MATCH:
            status = 409
        else:
            status = 500

        # Map error code to string name
        code_name = ErrorCode(code).name if code in ErrorCode.__members__.values() else str(code)

        return self._error_response(code_name, response.error.message, status)

    async def _call_handler(self, method: str, params: dict[str, Any]) -> web.Response:
        """Call a JSON-RPC method and return an HTTP response."""
        request = JsonRpcRequest(method=method, params=params)
        response = await self._handler(request)

        if response.error:
            return self._rpc_error_to_response(response)
        return self._success_response(response.result)

    # Route handlers

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/health."""
        status = self._health_check()
        return self._success_response(status)

    async def _handle_list_tasks(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/tasks."""
        params: dict[str, Any] = {}
        if status := request.query.get("status"):
            params["status"] = status
        if project := request.query.get("project"):
            params["project"] = project
        return await self._call_handler("list_tasks", params)

    async def _handle_add_task(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/tasks."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "title" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: title")

        return await self._call_handler("add_task", body)

    async def _handle_get_task(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/tasks/{id}."""
        task_id = request.match_info["id"]
        return await self._call_handler("get_task", {"query": task_id})

    async def _handle_complete_task(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/tasks/{id}/complete."""
        task_id = request.match_info["id"]
        return await self._call_handler("complete_task", {"query": task_id})

    async def _handle_start_task(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/tasks/{id}/start."""
        task_id = request.match_info["id"]
        return await self._call_handler("start_task", {"query": task_id})

    async def _handle_defer_task(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/tasks/{id}/defer."""
        task_id = request.match_info["id"]
        return await self._call_handler("defer_task", {"query": task_id})

    async def _handle_delegate_task(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/tasks/{id}/delegate."""
        task_id = request.match_info["id"]
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "person" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: person")

        params = {"query": task_id, "person": body["person"]}
        return await self._call_handler("delegate_task", params)

    async def _handle_list_projects(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/projects."""
        params: dict[str, Any] = {}
        if status := request.query.get("status"):
            params["status"] = status
        return await self._call_handler("list_projects", params)

    async def _handle_create_project(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/projects."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "name" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: name")

        return await self._call_handler("create_project", body)

    async def _handle_list_people(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/people."""
        return await self._call_handler("list_people", {})

    async def _handle_create_person(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/people."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "name" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: name")

        return await self._call_handler("create_person", body)

    async def _handle_get_dashboard(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/dashboard."""
        params: dict[str, Any] = {}
        if date := request.query.get("date"):
            params["date"] = date
        return await self._call_handler("get_dashboard", params)

    async def _handle_list_context_packs(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/context-packs."""
        params: dict[str, Any] = {}
        if category := request.query.get("category"):
            params["category"] = category
        return await self._call_handler("list_context_packs", params)

    async def _handle_create_context_pack(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/context-packs."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "title" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: title")
        if "category" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: category")

        return await self._call_handler("create_context_pack", body)

    async def _handle_add_to_context_pack(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/context-packs/{id}/content."""
        pack_id = request.match_info["id"]
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "content" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: content")

        params = {
            "pack": pack_id,
            "content": body["content"],
        }
        if section := body.get("section"):
            params["section"] = section

        return await self._call_handler("add_to_context_pack", params)

    async def _handle_file_get(self, request: web.Request) -> web.Response:
        """Handle GET /api/v1/files?query=..."""
        query = request.query.get("query")
        if not query:
            return self._error_response("MISSING_FIELD", "Missing required query parameter: query")
        return await self._call_handler("file_get", {"query": query})

    async def _handle_file_set(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/files."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return self._error_response("INVALID_JSON", "Invalid JSON body")

        if "query" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: query")
        if "content" not in body:
            return self._error_response("MISSING_FIELD", "Missing required field: content")

        return await self._call_handler("file_set", body)

    async def _handle_rpc(self, request: web.Request) -> web.Response:
        """Handle POST /api/v1/rpc - raw JSON-RPC endpoint."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                JsonRpcResponse.error_response(
                    ErrorCode.PARSE_ERROR,
                    "Invalid JSON",
                ).to_dict()
            )

        try:
            rpc_request = JsonRpcRequest.from_dict(body)
        except ValueError as e:
            return web.json_response(
                JsonRpcResponse.error_response(
                    ErrorCode.INVALID_REQUEST,
                    str(e),
                    request_id=body.get("id"),
                ).to_dict()
            )

        response = await self._handler(rpc_request)
        return web.json_response(response.to_dict())
