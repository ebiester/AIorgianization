#!/usr/bin/env bash
#
# setup-test-vault.sh - Create an isolated test vault with Obsidian structure
#
# This script creates a temporary vault with the .obsidian directory
# required by the AIO CLI, then initializes the AIO structure.
#
# Usage:
#   ./scripts/test/setup-test-vault.sh
#
# Output:
#   Prints the path to the created vault on stdout
#

set -euo pipefail

# Work around macOS UV issues
export UV_NATIVE_TLS=1
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/claude/uv-cache}"

# Track temp directory for cleanup on failure
TEMP_DIR=""

# Error handling helper
die() {
    echo "ERROR: $1" >&2
    exit 1
}

# Cleanup on failure - only clean up if we exit with an error
# On success, the caller is responsible for cleanup
cleanup_on_failure() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        echo "Cleaning up partial test vault due to failure: $TEMP_DIR" >&2
        rm -rf "$TEMP_DIR" 2>/dev/null || true
    fi
}
trap cleanup_on_failure EXIT
trap 'cleanup_on_failure; exit 130' INT
trap 'cleanup_on_failure; exit 143' TERM

# Check for required commands
if ! command -v uv &> /dev/null; then
    die "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Create temp directory
TEMP_DIR=$(mktemp -d) || die "Failed to create temporary directory"
VAULT_PATH="$TEMP_DIR/test-vault"

# Create vault structure
mkdir -p "$VAULT_PATH/.obsidian" || die "Failed to create vault directory: $VAULT_PATH/.obsidian"

# Create minimal .obsidian config files (required for aio init validation)
cat > "$VAULT_PATH/.obsidian/app.json" << 'EOF'
{
  "alwaysUpdateLinks": true
}
EOF

cat > "$VAULT_PATH/.obsidian/appearance.json" << 'EOF'
{
  "baseFontSize": 16
}
EOF

# Initialize AIO structure using the CLI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || die "Failed to determine script directory"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || die "Failed to determine project root"

cd "$PROJECT_ROOT" || die "Failed to change to project root: $PROJECT_ROOT"

# Ensure dependencies are installed
uv sync --all-extras --quiet || die "Failed to sync dependencies with uv"

# Initialize AIO structure using uv run
# Note: stdout must be suppressed since this script returns the vault path via stdout
# On failure, we capture and display the output
INIT_OUTPUT=$(uv run aio init "$VAULT_PATH" 2>&1) || {
    echo "aio init output:" >&2
    echo "$INIT_OUTPUT" >&2
    die "Failed to initialize AIO structure using 'uv run aio init'. Check that the CLI is working correctly."
}

# Output the path (to be captured by caller)
echo "$VAULT_PATH"
