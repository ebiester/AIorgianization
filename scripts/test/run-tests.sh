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

# Error handling helper
die() {
    echo "ERROR: $1" >&2
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || die "Failed to determine script directory"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || die "Failed to determine project root"
RESULTS_DIR="$PROJECT_ROOT/test-results"
TEMP_VAULT=""

# Check for required commands
if ! command -v uv &> /dev/null; then
    die "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh (or 'brew install uv')"
fi

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

# Cleanup function - runs on exit, error, or interrupt
cleanup() {
    local exit_code=$?
    if [ -n "$TEMP_VAULT" ] && [ -d "$TEMP_VAULT" ]; then
        local temp_dir
        temp_dir="$(dirname "$TEMP_VAULT")"
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

# Create results directory
mkdir -p "$RESULTS_DIR" || die "Failed to create results directory: $RESULTS_DIR"

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
    if [ ! -x "$SCRIPT_DIR/setup-test-vault.sh" ]; then
        die "setup-test-vault.sh not found or not executable at: $SCRIPT_DIR/setup-test-vault.sh"
    fi
    TEMP_VAULT=$("$SCRIPT_DIR/setup-test-vault.sh") || die "Failed to set up test vault. Run with --verbose for details."
    if [ -z "$TEMP_VAULT" ]; then
        die "setup-test-vault.sh returned empty path"
    fi
    if [ ! -d "$TEMP_VAULT" ]; then
        die "Test vault directory does not exist: $TEMP_VAULT"
    fi
    export AIO_VAULT_PATH="$TEMP_VAULT"
    if [ "$VERBOSE" = true ]; then
        echo "Temp vault: $TEMP_VAULT"
    fi
    echo ""
fi

# Phase 2: Run Python tests
if [ "$RUN_PYTHON" = true ]; then
    echo "=== Running Python tests ==="
    if [ ! -x "$SCRIPT_DIR/run-python-tests.sh" ]; then
        die "run-python-tests.sh not found or not executable at: $SCRIPT_DIR/run-python-tests.sh"
    fi
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
    if [ ! -x "$SCRIPT_DIR/run-typescript-tests.sh" ]; then
        die "run-typescript-tests.sh not found or not executable at: $SCRIPT_DIR/run-typescript-tests.sh"
    fi
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
    if [ ! -x "$SCRIPT_DIR/run-mcp-tests.sh" ]; then
        die "run-mcp-tests.sh not found or not executable at: $SCRIPT_DIR/run-mcp-tests.sh"
    fi
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
cd "$PROJECT_ROOT" || die "Failed to change to project root: $PROJECT_ROOT"

if [ ! -f "$SCRIPT_DIR/generate-report.py" ]; then
    die "generate-report.py not found at: $SCRIPT_DIR/generate-report.py"
fi

# Generate report using uv run
if ! uv run python "$SCRIPT_DIR/generate-report.py" \
    --results-dir "$RESULTS_DIR" \
    --output-dir "$RESULTS_DIR"; then
    die "Failed to generate combined report"
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
