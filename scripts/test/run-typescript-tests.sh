#!/usr/bin/env bash
#
# run-typescript-tests.sh - Run TypeScript tests for Obsidian plugin
#
# Usage:
#   ./scripts/test/run-typescript-tests.sh [options]
#
# Options:
#   --output FILE     Output JSON results to FILE
#   --verbose         Verbose output
#

set -euo pipefail

# Error handling helper
die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Check for required commands
if ! command -v npm &> /dev/null; then
    die "npm is not installed. Install Node.js to get npm."
fi

OUTPUT_FILE=""
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
PLUGIN_DIR="$PROJECT_ROOT/obsidian-aio"

# Check plugin directory exists
if [ ! -d "$PLUGIN_DIR" ]; then
    die "Obsidian plugin directory not found: $PLUGIN_DIR"
fi

cd "$PLUGIN_DIR" || die "Failed to change to plugin directory: $PLUGIN_DIR"

# Ensure test-results directory exists
mkdir -p "$PROJECT_ROOT/test-results" || die "Failed to create test-results directory"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    die "package.json not found in $PLUGIN_DIR"
fi

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo "Installing TypeScript dependencies..."
    if ! npm install; then
        die "Failed to install npm dependencies. Check package.json and network connection."
    fi
fi

# Check test script exists in package.json
if ! grep -q '"test"' package.json; then
    die "No 'test' script found in package.json"
fi

# Run vitest
echo "Running TypeScript tests..."
set +e  # Temporarily allow command failure to capture exit code
if [ "$VERBOSE" = true ]; then
    npm run test -- --reporter=verbose
else
    npm run test
fi
exit_code=$?
set -e  # Re-enable strict mode

# Distinguish between vitest not found and test failures
if [ $exit_code -eq 127 ]; then
    die "Test runner not found. Run 'npm install' in $PLUGIN_DIR"
fi

# Copy results to output location if specified and different from default
if [ -n "$OUTPUT_FILE" ]; then
    DEFAULT_OUTPUT="$PROJECT_ROOT/test-results/typescript-results.json"
    if [ -f "$DEFAULT_OUTPUT" ] && [ "$OUTPUT_FILE" != "$DEFAULT_OUTPUT" ]; then
        cp "$DEFAULT_OUTPUT" "$OUTPUT_FILE"
    fi
fi

echo ""
echo "TypeScript tests completed"
if [ -f "$PROJECT_ROOT/test-results/typescript-results.json" ]; then
    echo "Results saved to: $PROJECT_ROOT/test-results/typescript-results.json"
fi

exit $exit_code
