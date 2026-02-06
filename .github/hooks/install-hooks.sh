#!/bin/bash
# Context.md Git Hooks Installer
# Sets up Git hooks for automated validation and certificate generation
#
# Usage:
#   ./.github/hooks/install-hooks.sh
#   ./.github/hooks/install-hooks.sh --uninstall

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.github/hooks"
GIT_HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo ""
echo "========================================"
echo "  Context.md Git Hooks Installer"
echo "========================================"
echo ""

# Check if uninstall requested
if [ "$1" = "--uninstall" ]; then
    echo "Uninstalling Git hooks..."
    echo ""

    for hook in post-merge pre-commit pre-push; do
        hook_path="$GIT_HOOKS_DIR/$hook"
        if [ -L "$hook_path" ]; then
            rm "$hook_path"
            echo -e "${GREEN}[OK]${NC} Removed $hook hook"
        elif [ -f "$hook_path" ]; then
            echo -e "${YELLOW}[WARN]${NC} $hook exists but is not a symlink (skipped)"
        else
            echo -e "${BLUE}[INFO]${NC} $hook not installed"
        fi
    done

    echo ""
    echo -e "${GREEN}✓${NC} Git hooks uninstalled successfully"
    echo ""
    exit 0
fi

# Install hooks
echo "Installing Git hooks from .github/hooks/"
echo ""

# Ensure .git/hooks directory exists
mkdir -p "$GIT_HOOKS_DIR"

# Make hook scripts executable
chmod +x "$HOOKS_DIR/post-merge"
chmod +x "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-push"

HOOKS_INSTALLED=0
HOOKS_SKIPPED=0

for hook in post-merge pre-commit pre-push; do
    source_path="$HOOKS_DIR/$hook"
    target_path="$GIT_HOOKS_DIR/$hook"

    if [ -L "$target_path" ]; then
        # Symlink already exists
        current_target=$(readlink "$target_path")
        if [ "$current_target" = "$source_path" ]; then
            echo -e "${BLUE}[INFO]${NC} $hook already installed (up to date)"
            HOOKS_INSTALLED=$((HOOKS_INSTALLED + 1))
        else
            echo -e "${YELLOW}[WARN]${NC} $hook points to different location"
            echo "  Current: $current_target"
            echo "  Expected: $source_path"
            echo "  Run with --uninstall first to clean up"
            HOOKS_SKIPPED=$((HOOKS_SKIPPED + 1))
        fi
    elif [ -f "$target_path" ]; then
        # File exists but not symlink
        echo -e "${YELLOW}[WARN]${NC} $hook exists but is not a symlink"
        echo "  Backing up to $target_path.backup"
        mv "$target_path" "$target_path.backup"
        ln -s "$source_path" "$target_path"
        echo -e "${GREEN}[OK]${NC} Installed $hook (backed up existing)"
        HOOKS_INSTALLED=$((HOOKS_INSTALLED + 1))
    else
        # No hook exists, create symlink
        ln -s "$source_path" "$target_path"
        echo -e "${GREEN}[OK]${NC} Installed $hook"
        HOOKS_INSTALLED=$((HOOKS_INSTALLED + 1))
    fi
done

echo ""
echo "========================================"
echo -e "${GREEN}✓${NC} Installation complete"
echo ""
echo "Summary:"
echo "  - Hooks installed: $HOOKS_INSTALLED"
echo "  - Hooks skipped: $HOOKS_SKIPPED"
echo ""
echo "Installed hooks:"
echo "  • post-merge  - Generate completion certificates"
echo "  • pre-commit  - Security checks and linting"
echo "  • pre-push    - Definition of Done validation"
echo ""
echo "To uninstall:"
echo "  ./.github/hooks/install-hooks.sh --uninstall"
echo ""
echo "To bypass hooks temporarily:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
echo "========================================"
echo ""
