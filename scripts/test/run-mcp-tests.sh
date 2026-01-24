#!/usr/bin/env bash
#
# run-mcp-tests.sh - Test MCP server protocol communication
#
# This script:
# 1. Spawns the MCP server as a subprocess
# 2. Sends JSON-RPC requests via stdio
# 3. Verifies responses
# 4. Outputs results as JSON
#
# Usage:
#   ./scripts/test/run-mcp-tests.sh [options]
#
# Options:
#   --vault PATH      Path to test vault (required)
#   --output FILE     Output JSON results to FILE
#   --verbose         Verbose output
#

set -euo pipefail

# Work around macOS UV issues
export UV_NATIVE_TLS=1
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/claude/uv-cache}"

VAULT_PATH=""
OUTPUT_FILE=""
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vault)
            VAULT_PATH="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Ensure test-results directory exists
mkdir -p "$PROJECT_ROOT/test-results"

# Set default output path
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/test-results/mcp-results.json"
fi

# Use temp vault if not provided
if [ -z "$VAULT_PATH" ]; then
    echo "Creating temporary vault for MCP tests..."
    VAULT_PATH=$("$SCRIPT_DIR/setup-test-vault.sh")
    CLEANUP_VAULT=true
else
    CLEANUP_VAULT=false
fi

# Cleanup function
cleanup() {
    if [ "$CLEANUP_VAULT" = true ] && [ -n "$VAULT_PATH" ] && [ -d "$VAULT_PATH" ]; then
        rm -rf "$(dirname "$VAULT_PATH")"
    fi
}
trap cleanup EXIT

# Export vault path for the Python script
export AIO_VAULT_PATH="$VAULT_PATH"
export MCP_OUTPUT_FILE="$OUTPUT_FILE"
export MCP_VERBOSE="$VERBOSE"

echo "Running MCP server tests..."
if [ "$VERBOSE" = true ]; then
    echo "Vault path: $VAULT_PATH"
    echo "Output file: $OUTPUT_FILE"
fi

# Determine Python executable - prefer venv if available
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON_CMD="uv run python"
fi

# Export for the embedded script to use for subprocess
export MCP_PYTHON_CMD="$PYTHON_CMD"
export MCP_PROJECT_ROOT="$PROJECT_ROOT"

# Run MCP protocol tests via embedded Python script
$PYTHON_CMD << 'PYTHON_SCRIPT'
import asyncio
import json
import os
import signal
import subprocess
import sys
import time

class MCPTestRunner:
    """Runs MCP protocol tests against the server."""

    def __init__(self, vault_path: str, verbose: bool = False):
        self.vault_path = vault_path
        self.verbose = verbose
        self.results = []
        self.process = None
        self.request_id = 0

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [MCP] {msg}", file=sys.stderr)

    async def start_server(self) -> bool:
        """Start the MCP server subprocess."""
        self.log("Starting MCP server...")
        env = {
            **os.environ,
            "AIO_VAULT_PATH": self.vault_path,
        }

        try:
            # Use venv aio-mcp if available, otherwise fall back to uv run
            project_root = os.environ.get("MCP_PROJECT_ROOT", ".")
            aio_mcp_path = os.path.join(project_root, ".venv", "bin", "aio-mcp")

            if os.path.exists(aio_mcp_path):
                cmd = [aio_mcp_path]
            else:
                cmd = ["uv", "run", "aio-mcp"]

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            # Wait for server to be ready
            await asyncio.sleep(1.5)

            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                self.log(f"Server exited with code {self.process.returncode}")
                self.log(f"Stderr: {stderr.decode()}")
                return False

            self.log("Server started successfully")
            return True
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            return False

    async def send_request(self, method: str, params: dict = None) -> dict | None:
        """Send JSON-RPC request and get response."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        request_line = json.dumps(request) + "\n"
        self.log(f"Sending: {method}")

        try:
            self.process.stdin.write(request_line.encode())
            await self.process.stdin.drain()

            # Read response with timeout
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0
            )

            if not response_line:
                self.log("Empty response")
                return None

            response = json.loads(response_line.decode())
            self.log(f"Received response for request {response.get('id')}")
            return response
        except asyncio.TimeoutError:
            self.log("Request timed out")
            return None
        except Exception as e:
            self.log(f"Request failed: {e}")
            return None

    async def run_test(
        self,
        name: str,
        method: str,
        params: dict = None,
        validate: callable = None
    ) -> dict:
        """Run a single MCP test."""
        test_result = {
            "name": name,
            "method": method,
            "passed": False,
            "error": None,
        }

        self.log(f"Running test: {name}")

        response = await self.send_request(method, params)

        if response is None:
            test_result["error"] = "No response received"
        elif "error" in response:
            test_result["error"] = str(response["error"])
        elif validate:
            try:
                validate(response.get("result"))
                test_result["passed"] = True
            except AssertionError as e:
                test_result["error"] = str(e)
            except Exception as e:
                test_result["error"] = f"Validation error: {e}"
        else:
            test_result["passed"] = True

        self.results.append(test_result)
        status = "PASS" if test_result["passed"] else "FAIL"
        print(f"  [{status}] {name}")
        if test_result["error"]:
            print(f"         Error: {test_result['error']}")

        return test_result

    async def stop_server(self) -> None:
        """Gracefully stop the MCP server."""
        if self.process:
            self.log("Stopping server...")
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            self.log("Server stopped")


async def main():
    vault_path = os.environ.get("AIO_VAULT_PATH", "")
    output_file = os.environ.get("MCP_OUTPUT_FILE", "test-results/mcp-results.json")
    verbose = os.environ.get("MCP_VERBOSE", "false").lower() == "true"

    if not vault_path:
        print("Error: AIO_VAULT_PATH not set", file=sys.stderr)
        sys.exit(1)

    runner = MCPTestRunner(vault_path, verbose)

    # Start server
    if not await runner.start_server():
        print("Failed to start MCP server")
        output = {
            "total": 0,
            "passed": 0,
            "failed": 1,
            "tests": [{"name": "Server startup", "passed": False, "error": "Server failed to start"}],
        }
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        sys.exit(1)

    print("Running MCP protocol tests...")
    print("")

    # Run tests
    try:
        # Test: Initialize (this primes the server)
        await runner.run_test(
            "Server responds to initialize",
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            },
            validate=lambda r: r is not None
        )

        # Test: List tools
        await runner.run_test(
            "List tools returns AIO tools",
            "tools/list",
            validate=lambda r: (
                r is not None and
                "tools" in r and
                len(r["tools"]) > 0 and
                any("aio_" in t.get("name", "") for t in r["tools"])
            )
        )

        # Test: List resources
        await runner.run_test(
            "List resources returns AIO resources",
            "resources/list",
            validate=lambda r: (
                r is not None and
                "resources" in r and
                len(r["resources"]) > 0 and
                any("aio://" in str(res.get("uri", "")) for res in r["resources"])
            )
        )

        # Test: Add task
        await runner.run_test(
            "Add task creates task",
            "tools/call",
            {"name": "aio_add_task", "arguments": {"title": "MCP Test Task"}},
            validate=lambda r: (
                r is not None and
                len(r) > 0 and
                "Created task" in str(r)
            )
        )

        # Test: List tasks
        await runner.run_test(
            "List tasks returns tasks",
            "tools/call",
            {"name": "aio_list_tasks", "arguments": {}},
            validate=lambda r: r is not None
        )

        # Test: Get dashboard
        await runner.run_test(
            "Get dashboard returns content",
            "tools/call",
            {"name": "aio_get_dashboard", "arguments": {}},
            validate=lambda r: r is not None and len(str(r)) > 0
        )

        # Test: Read resource
        await runner.run_test(
            "Read tasks/inbox resource",
            "resources/read",
            {"uri": "aio://tasks/inbox"},
            validate=lambda r: r is not None
        )

    finally:
        await runner.stop_server()

    # Output results
    output = {
        "total": len(runner.results),
        "passed": sum(1 for r in runner.results if r["passed"]),
        "failed": sum(1 for r in runner.results if not r["passed"]),
        "tests": runner.results,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print("")
    print(f"Results: {output['passed']}/{output['total']} passed")
    print(f"Output saved to: {output_file}")

    # Exit with error code if any tests failed
    sys.exit(0 if output["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
PYTHON_SCRIPT

exit_code=$?
exit $exit_code
