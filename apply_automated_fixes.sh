#!/bin/bash
# Automated Low-Hanging Fruit Fixes for /home/coolhand/shared
# Author: Luke Steuber
# Date: 2025-11-19
#
# This script applies zero-risk automated improvements identified in
# LOW_HANGING_FRUIT_ANALYSIS.md
#
# SAFE TO RUN: All changes are formatting-only and preserve functionality

set -e  # Exit on error

SHARED_DIR="/home/coolhand/shared"
cd "$SHARED_DIR"

echo "========================================"
echo "Shared Library - Automated Code Cleanup"
echo "========================================"
echo ""

# Check if git repo is clean
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  Warning: You have uncommitted changes."
    echo "   Recommendation: Commit current state first."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting."
        exit 1
    fi
fi

# Create backup
BACKUP_BRANCH="backup-before-automated-fixes-$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating safety backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"
echo "   (You can restore with: git checkout $BACKUP_BRANCH)"
echo ""

# Check for required tools
echo "🔍 Checking for required tools..."

if ! command -v black &> /dev/null; then
    echo "   Installing black..."
    pip install black -q
fi

if ! command -v isort &> /dev/null; then
    echo "   Installing isort..."
    pip install isort -q
fi

echo "   ✓ Tools ready"
echo ""

# Phase 1: Import sorting
echo "📋 Phase 1: Organizing imports with isort..."
isort --profile black \
      --line-length 100 \
      --skip venv \
      --skip mcp/venv \
      "$SHARED_DIR"
echo "   ✓ Imports organized"
echo ""

# Phase 2: Code formatting
echo "✨ Phase 2: Formatting code with black..."
black --line-length 100 \
      --exclude '/(venv|mcp/venv)/' \
      "$SHARED_DIR"
echo "   ✓ Code formatted"
echo ""

# Phase 3: Trailing whitespace cleanup
echo "🧹 Phase 3: Removing trailing whitespace..."
find "$SHARED_DIR" -name "*.py" -type f \
    ! -path "*/venv/*" \
    ! -path "*/mcp/venv/*" \
    -exec sed -i 's/[[:space:]]*$//' {} \;
echo "   ✓ Whitespace cleaned"
echo ""

# Phase 4: Ensure newline at EOF
echo "📝 Phase 4: Ensuring newlines at end of files..."
find "$SHARED_DIR" -name "*.py" -type f \
    ! -path "*/venv/*" \
    ! -path "*/mcp/venv/*" \
    -exec sh -c 'tail -c1 "$1" | read -r _ || echo "" >> "$1"' _ {} \;
echo "   ✓ Files normalized"
echo ""

# Show git diff summary
echo "========================================"
echo "Changes Summary"
echo "========================================"
git diff --stat

echo ""
echo "✅ Automated fixes complete!"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Run tests: pytest tests/"
echo "  3. Type check: mypy shared/ --ignore-missing-imports"
echo "  4. Commit: git add . && git commit -m 'refactor: apply automated code quality fixes'"
echo ""
echo "To undo: git checkout $BACKUP_BRANCH"
