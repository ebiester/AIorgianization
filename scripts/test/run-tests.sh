#!/usr/bin/env bash
#
# run-tests.sh - Main test runner for AIorgianization
#
# Orchestrates Python, TypeScript, and MCP server tests,
# generating a combined report with UAT coverage.
#
# Usage:
#   ./scripts/test/run-tests.sh [options]
#
# Options:
#   --python-only      Run only Python tests
#   --typescript-only  Run only TypeScript tests
#   --mcp-only         Run only MCP server tests
#   --skip-coverage    Skip coverage generation
#   --verbose          Verbose output
#   --help             Show this help
#

set -euo pipefail

# Work around macOS UV issues
export UV_NATIVE_TLS=1
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/claude/uv-cache}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/test-results"
TEMP_VAULT=""

# Default options
RUN_PYTHON=true
RUN_TYPESCRIPT=true
RUN_MCP=true
WITH_COVERAGE=true
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --python-only)
            RUN_PYTHON=true
            RUN_TYPESCRIPT=false
            RUN_MCP=false
            shift
            ;;
        --typescript-only)
            RUN_PYTHON=false
            RUN_TYPESCRIPT=true
            RUN_MCP=false
            shift
            ;;
        --mcp-only)
            RUN_PYTHON=false
            RUN_TYPESCRIPT=false
            RUN_MCP=true
            shift
            ;;
        --skip-coverage)
            WITH_COVERAGE=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            head -30 "$0" | tail -28
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Cleanup function
cleanup() {
    if [ -n "$TEMP_VAULT" ] && [ -d "$TEMP_VAULT" ]; then
        rm -rf "$(dirname "$TEMP_VAULT")"
    fi
}
trap cleanup EXIT

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "  AIorgianization Test Runner"
echo "========================================"
echo ""

# Track overall status
PYTHON_STATUS=0
TYPESCRIPT_STATUS=0
MCP_STATUS=0

# Phase 1: Setup test environment
if [ "$RUN_MCP" = true ]; then
    echo "=== Setting up test environment ==="
    TEMP_VAULT=$("$SCRIPT_DIR/setup-test-vault.sh")
    export AIO_VAULT_PATH="$TEMP_VAULT"
    if [ "$VERBOSE" = true ]; then
        echo "Temp vault: $TEMP_VAULT"
    fi
    echo ""
fi

# Phase 2: Run Python tests
if [ "$RUN_PYTHON" = true ]; then
    echo "=== Running Python tests ==="
    PYTHON_ARGS=("--output" "$RESULTS_DIR/python-results.json")
    if [ "$WITH_COVERAGE" = true ]; then
        PYTHON_ARGS+=("--with-coverage" "--coverage" "$RESULTS_DIR/python-coverage.xml")
    fi
    if [ "$VERBOSE" = true ]; then
        PYTHON_ARGS+=("--verbose")
    fi

    if "$SCRIPT_DIR/run-python-tests.sh" "${PYTHON_ARGS[@]}"; then
        echo "Python tests: PASSED"
    else
        PYTHON_STATUS=$?
        echo "Python tests: FAILED (exit code $PYTHON_STATUS)"
    fi
    echo ""
fi

# Phase 3: Run TypeScript tests
if [ "$RUN_TYPESCRIPT" = true ]; then
    echo "=== Running TypeScript tests ==="
    TS_ARGS=("--output" "$RESULTS_DIR/typescript-results.json")
    if [ "$VERBOSE" = true ]; then
        TS_ARGS+=("--verbose")
    fi

    if "$SCRIPT_DIR/run-typescript-tests.sh" "${TS_ARGS[@]}"; then
        echo "TypeScript tests: PASSED"
    else
        TYPESCRIPT_STATUS=$?
        echo "TypeScript tests: FAILED (exit code $TYPESCRIPT_STATUS)"
    fi
    echo ""
fi

# Phase 4: Run MCP server tests
if [ "$RUN_MCP" = true ]; then
    echo "=== Running MCP server tests ==="
    MCP_ARGS=("--vault" "$TEMP_VAULT" "--output" "$RESULTS_DIR/mcp-results.json")
    if [ "$VERBOSE" = true ]; then
        MCP_ARGS+=("--verbose")
    fi

    if "$SCRIPT_DIR/run-mcp-tests.sh" "${MCP_ARGS[@]}"; then
        echo "MCP tests: PASSED"
    else
        MCP_STATUS=$?
        echo "MCP tests: FAILED (exit code $MCP_STATUS)"
    fi
    echo ""
fi

# Phase 5: Generate combined report
echo "=== Generating combined report ==="
cd "$PROJECT_ROOT"

# Use venv python if available
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    "$PROJECT_ROOT/.venv/bin/python" "$SCRIPT_DIR/generate-report.py" \
        --results-dir "$RESULTS_DIR" \
        --output-dir "$RESULTS_DIR"
else
    uv run python "$SCRIPT_DIR/generate-report.py" \
        --results-dir "$RESULTS_DIR" \
        --output-dir "$RESULTS_DIR"
fi
echo ""

# Summary
echo "========================================"
echo "  Test Run Complete"
echo "========================================"
echo ""
echo "Results available in: $RESULTS_DIR"
echo ""
echo "Reports:"
echo "  - combined-report.md        (Summary + UAT coverage)"
echo "  - manual-test-checklist.md  (Manual tests for Obsidian plugin)"
echo "  - uat-coverage.json         (Machine-readable UAT mapping)"
echo ""

# Calculate overall status
OVERALL_STATUS=0
if [ $PYTHON_STATUS -ne 0 ]; then
    echo "WARNING: Python tests failed"
    OVERALL_STATUS=1
fi
if [ $TYPESCRIPT_STATUS -ne 0 ]; then
    echo "WARNING: TypeScript tests failed"
    OVERALL_STATUS=1
fi
if [ $MCP_STATUS -ne 0 ]; then
    echo "WARNING: MCP tests failed"
    OVERALL_STATUS=1
fi

if [ $OVERALL_STATUS -eq 0 ]; then
    echo "All tests PASSED!"
fi

exit $OVERALL_STATUS
