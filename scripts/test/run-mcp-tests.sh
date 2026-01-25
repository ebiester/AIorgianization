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

# Work around macOS hidden flag issue on .pth files
# Add project root to PYTHONPATH to ensure aio module is found
SCRIPT_DIR_TEMP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_TEMP="$(cd "$SCRIPT_DIR_TEMP/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$PROJECT_ROOT_TEMP"

# Error handling helper
die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Check for required commands
if ! command -v uv &> /dev/null; then
    die "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh (or 'brew install uv')"
fi

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || die "Failed to determine script directory"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || die "Failed to determine project root"

cd "$PROJECT_ROOT" || die "Failed to change to project root: $PROJECT_ROOT"

# Ensure test-results directory exists
mkdir -p "$PROJECT_ROOT/test-results" || die "Failed to create test-results directory"

# Set default output path
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/test-results/mcp-results.json"
fi

# Use temp vault if not provided
if [ -z "$VAULT_PATH" ]; then
    echo "Creating temporary vault for MCP tests..."
    if [ ! -x "$SCRIPT_DIR/setup-test-vault.sh" ]; then
        die "setup-test-vault.sh not found or not executable at: $SCRIPT_DIR/setup-test-vault.sh"
    fi
    VAULT_PATH=$("$SCRIPT_DIR/setup-test-vault.sh") || die "Failed to create test vault"
    if [ -z "$VAULT_PATH" ]; then
        die "setup-test-vault.sh returned empty vault path"
    fi
    CLEANUP_VAULT=true
else
    if [ ! -d "$VAULT_PATH" ]; then
        die "Specified vault path does not exist: $VAULT_PATH"
    fi
    CLEANUP_VAULT=false
fi

# Cleanup function - runs on exit, error, or interrupt
cleanup() {
    local exit_code=$?
    if [ "$CLEANUP_VAULT" = true ] && [ -n "$VAULT_PATH" ] && [ -d "$VAULT_PATH" ]; then
        local temp_dir
        temp_dir="$(dirname "$VAULT_PATH")"
        if [ "$VERBOSE" = true ]; then
            echo "Cleaning up test vault: $temp_dir" >&2
        fi
        rm -rf "$temp_dir" 2>/dev/null || true
    fi
    return $exit_code
}
# Trap EXIT covers normal exit, errors (with set -e), and most signals
trap cleanup EXIT
# Also trap common signals explicitly for robustness
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

# Ensure dependencies are installed
if [ "$VERBOSE" = true ]; then
    echo "Ensuring dependencies are installed..."
fi
uv sync --all-extras --quiet || die "Failed to sync dependencies with uv"

# Export vault path for the Python script
export AIO_VAULT_PATH="$VAULT_PATH"
export MCP_OUTPUT_FILE="$OUTPUT_FILE"
export MCP_VERBOSE="$VERBOSE"
export MCP_PROJECT_ROOT="$PROJECT_ROOT"

echo "Running MCP server tests..."
if [ "$VERBOSE" = true ]; then
    echo "Vault path: $VAULT_PATH"
    echo "Output file: $OUTPUT_FILE"
fi

# Run MCP protocol tests via embedded Python script
set +e  # Temporarily allow command failure to capture exit code
uv run python << 'PYTHON_SCRIPT'
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

    async def start_server(self) -> tuple[bool, str]:
        """Start the MCP server subprocess.

        Returns:
            Tuple of (success, error_message)
        """
        self.log("Starting MCP server...")
        env = {
            **os.environ,
            "AIO_VAULT_PATH": self.vault_path,
        }

        try:
            # Always use uv run for consistency (dependencies already synced)
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
                stderr_text = stderr.decode()
                self.log(f"Server exited with code {self.process.returncode}")
                self.log(f"Stderr: {stderr_text}")

                # Check for common error conditions
                if "Failed to spawn" in stderr_text or "No such file" in stderr_text:
                    return False, "aio-mcp not found. Run 'uv sync' to install dependencies first."
                return False, f"Server exited with code {self.process.returncode}: {stderr_text[:200]}"

            self.log("Server started successfully")
            return True, ""
        except FileNotFoundError as e:
            return False, f"Command not found: {e}. Run 'uv sync' to install dependencies first."
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            return False, str(e)

    async def send_request(self, method: str, params: dict = None) -> dict | None:
        """Send JSON-RPC request and get response using newline-delimited JSON."""
        # Check if process is still running
        if self.process.returncode is not None:
            self.log(f"Server process has exited with code {self.process.returncode}")
            return None

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        # Simple newline-delimited JSON
        message = json.dumps(request) + "\n"
        self.log(f"Sending: {method}")

        try:
            self.process.stdin.write(message.encode())
            await self.process.stdin.drain()

            # Read response lines until we get one with our request id
            while True:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=3.0
                )

                if not response_line:
                    self.log("Empty response (EOF)")
                    return None

                try:
                    response = json.loads(response_line.decode())
                    # Skip notifications (no id field) and wait for our response
                    if "id" in response:
                        self.log(f"Received response for request {response.get('id')}")
                        return response
                    else:
                        # Log notifications but continue waiting
                        self.log(f"Notification: {response.get('method', 'unknown')}")
                except json.JSONDecodeError as e:
                    self.log(f"JSON decode error: {e}")
                    continue

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
            # Close stdin to signal EOF to the server
            if self.process.stdin:
                self.process.stdin.close()
                try:
                    await self.process.stdin.wait_closed()
                except Exception:
                    pass
            # Terminate and wait
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.log("Server didn't stop gracefully, killing...")
                self.process.kill()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self.log("Server kill also timed out")
            self.log("Server stopped")


async def run_tests(runner: MCPTestRunner) -> None:
    """Run all MCP protocol tests."""
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


async def main():
    vault_path = os.environ.get("AIO_VAULT_PATH", "")
    output_file = os.environ.get("MCP_OUTPUT_FILE", "test-results/mcp-results.json")
    verbose = os.environ.get("MCP_VERBOSE", "false").lower() == "true"

    if not vault_path:
        print("Error: AIO_VAULT_PATH not set", file=sys.stderr)
        sys.exit(1)

    runner = MCPTestRunner(vault_path, verbose)

    # Start server
    success, error_msg = await runner.start_server()
    if not success:
        print(f"ERROR: Failed to start MCP server: {error_msg}", file=sys.stderr)
        output = {
            "total": 0,
            "passed": 0,
            "failed": 1,
            "tests": [{"name": "Server startup", "passed": False, "error": error_msg}],
        }
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        sys.exit(1)

    print("Running MCP protocol tests...")
    print("")

    # Run tests with global timeout
    try:
        await asyncio.wait_for(run_tests(runner), timeout=60.0)
    except asyncio.TimeoutError:
        print("\nERROR: Test suite timed out after 60 seconds", file=sys.stderr)
        runner.results.append({
            "name": "Global timeout",
            "method": "N/A",
            "passed": False,
            "error": "Test suite timed out after 60 seconds"
        })
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
set -e  # Re-enable strict mode

# Check for Python not found error
if [ $exit_code -eq 127 ]; then
    die "Python not found. Run 'uv sync' to install dependencies."
fi

# Check if output file was created
if [ $exit_code -ne 0 ] && [ ! -f "$OUTPUT_FILE" ]; then
    echo "MCP tests failed and no results file was created."
fi

exit $exit_code
