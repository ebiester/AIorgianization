#!/usr/bin/env bash
#
# run-python-tests.sh - Run Python tests with pytest and JSON output
#
# Usage:
#   ./scripts/test/run-python-tests.sh [options]
#
# Options:
#   --output FILE      Output JSON results to FILE
#   --coverage FILE    Output coverage XML to FILE
#   --with-coverage    Enable coverage reporting
#   --verbose          Verbose output
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

# Check for required commands
if ! command -v uv &> /dev/null; then
    die "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh (or 'brew install uv')"
fi

OUTPUT_FILE=""
COVERAGE_FILE=""
WITH_COVERAGE=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE_FILE="$2"
            shift 2
            ;;
        --with-coverage)
            WITH_COVERAGE=true
            shift
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

# Check tests directory exists
if [ ! -d "$PROJECT_ROOT/tests" ]; then
    die "Tests directory not found: $PROJECT_ROOT/tests"
fi

# Ensure dependencies are installed
if [ "$VERBOSE" = true ]; then
    echo "Ensuring dependencies are installed..."
fi
uv sync --all-extras --quiet || die "Failed to sync dependencies with uv"

# Ensure test-results directory exists
mkdir -p "$PROJECT_ROOT/test-results" || die "Failed to create test-results directory"

# Set default output paths
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$PROJECT_ROOT/test-results/python-results.json"
fi

if [ -z "$COVERAGE_FILE" ]; then
    COVERAGE_FILE="$PROJECT_ROOT/test-results/python-coverage.xml"
fi

# Build pytest command
PYTEST_ARGS=(
    "--tb=short"
    "--json-report"
    "--json-report-file=$OUTPUT_FILE"
)

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
fi

if [ "$WITH_COVERAGE" = true ]; then
    PYTEST_ARGS+=(
        "--cov=aio"
        "--cov-report=xml:$COVERAGE_FILE"
        "--cov-report=term-missing"
    )
fi

# Run pytest using uv run (dependencies already synced above)
echo "Running Python tests..."

if [ "$VERBOSE" = true ]; then
    echo "Command: uv run pytest ${PYTEST_ARGS[*]} tests/"
fi

set +e  # Temporarily allow command failure to capture exit code
uv run pytest "${PYTEST_ARGS[@]}" tests/
exit_code=$?
set -e  # Re-enable strict mode

# Output summary
echo ""
echo "Python test results saved to: $OUTPUT_FILE"
if [ "$WITH_COVERAGE" = true ]; then
    echo "Coverage report saved to: $COVERAGE_FILE"
fi

exit $exit_code
