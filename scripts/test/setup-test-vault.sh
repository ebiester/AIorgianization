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

# Create temp directory
TEMP_DIR=$(mktemp -d)
VAULT_PATH="$TEMP_DIR/test-vault"

# Create vault structure
mkdir -p "$VAULT_PATH/.obsidian"

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Initialize AIO structure - prefer venv if available
if [ -f "$PROJECT_ROOT/.venv/bin/aio" ]; then
    "$PROJECT_ROOT/.venv/bin/aio" init "$VAULT_PATH" >/dev/null 2>&1
else
    uv run aio init "$VAULT_PATH" >/dev/null 2>&1
fi

# Output the path (to be captured by caller)
echo "$VAULT_PATH"
