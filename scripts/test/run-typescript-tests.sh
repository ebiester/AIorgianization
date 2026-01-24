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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_DIR="$PROJECT_ROOT/obsidian-aio"

cd "$PLUGIN_DIR"

# Ensure test-results directory exists
mkdir -p "$PROJECT_ROOT/test-results"

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo "Installing TypeScript dependencies..."
    npm install
fi

# Run vitest
echo "Running TypeScript tests..."
if [ "$VERBOSE" = true ]; then
    npm run test -- --reporter=verbose
else
    npm run test
fi

exit_code=$?

# Copy results to output location if specified
if [ -n "$OUTPUT_FILE" ]; then
    if [ -f "$PROJECT_ROOT/test-results/typescript-results.json" ]; then
        cp "$PROJECT_ROOT/test-results/typescript-results.json" "$OUTPUT_FILE"
    fi
fi

echo ""
echo "TypeScript tests completed"
if [ -f "$PROJECT_ROOT/test-results/typescript-results.json" ]; then
    echo "Results saved to: $PROJECT_ROOT/test-results/typescript-results.json"
fi

exit $exit_code
