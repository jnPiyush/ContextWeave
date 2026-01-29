"""
Init Command - Initialize Context.md in a repository

Usage:
    context-md init [--mode local|github|hybrid] [--force]
"""

import click
import subprocess
from pathlib import Path
from typing import Optional

from context_md.state import State
from context_md.config import Config


# Git hook scripts
PREPARE_COMMIT_MSG_HOOK = '''#!/bin/bash
# Context.md: Auto-add issue reference from branch name

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Skip if message already has issue reference or is a merge/squash
if [ "$COMMIT_SOURCE" = "merge" ] || [ "$COMMIT_SOURCE" = "squash" ]; then
    exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Extract issue number from branch name (e.g., issue-456-jwt → 456)
if [[ $BRANCH =~ ^issue-([0-9]+) ]]; then
    ISSUE_NUM="${BASH_REMATCH[1]}"
    # Only add if not already present
    if ! grep -q "#$ISSUE_NUM" "$COMMIT_MSG_FILE"; then
        # Append issue reference to first line
        sed -i.bak "1s/$/ (#$ISSUE_NUM)/" "$COMMIT_MSG_FILE"
        rm -f "$COMMIT_MSG_FILE.bak"
    fi
fi

exit 0
'''

PRE_COMMIT_HOOK = '''#!/bin/bash
# Context.md: Pre-commit validation

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only validate on issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0
fi

ISSUE_NUM="${BASH_REMATCH[1]}"
CONTEXT_FILE=".agent-context/context-$ISSUE_NUM.md"

# Check if context file exists (warning only, don't block)
if [ ! -f "$CONTEXT_FILE" ]; then
    echo "⚠️  Context file not found: $CONTEXT_FILE"
    echo "   Consider running: context-md context generate $ISSUE_NUM"
fi

# Run standard checks (if available)
if command -v ruff &> /dev/null; then
    git diff --cached --name-only --diff-filter=ACM | grep '\\.py$' | xargs -r ruff check --fix
fi

exit 0
'''

POST_COMMIT_HOOK = '''#!/bin/bash
# Context.md: Post-commit activity tracking

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only track on issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0
fi

ISSUE_NUM="${BASH_REMATCH[1]}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Update Git note with last activity
# Get current note, update it, write back
CURRENT_NOTE=$(git notes --ref=context show "refs/heads/$BRANCH" 2>/dev/null || echo '{}')
echo "$CURRENT_NOTE" | python3 -c "
import json, sys
data = json.load(sys.stdin) if sys.stdin.readable() else {}
data['last_activity'] = '$TIMESTAMP'
data['commits'] = data.get('commits', 0) + 1
print(json.dumps(data))
" 2>/dev/null | git notes --ref=context add -f -F - "refs/heads/$BRANCH" 2>/dev/null || true

exit 0
'''

PRE_PUSH_HOOK = '''#!/bin/bash
# Context.md: Pre-push DoD validation

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only validate on issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0
fi

ISSUE_NUM="${BASH_REMATCH[1]}"

# Run DoD validation if context-md is available
if command -v context-md &> /dev/null; then
    context-md validate $ISSUE_NUM --dod --quiet
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Definition of Done validation failed!"
        echo "   Run: context-md validate $ISSUE_NUM --dod --verbose"
        echo ""
        echo "   To bypass (not recommended): git push --no-verify"
        exit 1
    fi
    echo "✅ DoD validation passed"
fi

exit 0
'''

POST_MERGE_HOOK = '''#!/bin/bash
# Context.md: Post-merge cleanup and certificate generation

# Get the merged branch (if available from reflog)
MERGED_BRANCH=$(git reflog -1 | grep -oP "merge \\K[^:]+")

if [[ $MERGED_BRANCH =~ ^issue-([0-9]+) ]]; then
    ISSUE_NUM="${BASH_REMATCH[1]}"
    
    # Generate completion certificate if context-md is available
    if command -v context-md &> /dev/null; then
        context-md validate $ISSUE_NUM --certificate --quiet 2>/dev/null || true
    fi
    
    echo "✅ Issue #$ISSUE_NUM merged successfully"
fi

exit 0
'''

# PowerShell versions for Windows
PREPARE_COMMIT_MSG_HOOK_PS = r'''#!/usr/bin/env pwsh
# Context.md: Auto-add issue reference from branch name

param($CommitMsgFile, $CommitSource)

if ($CommitSource -eq "merge" -or $CommitSource -eq "squash") { exit 0 }

$branch = git rev-parse --abbrev-ref HEAD 2>$null
if ($branch -match '^issue-(\d+)') {
    $issueNum = $Matches[1]
    $content = Get-Content $CommitMsgFile -Raw
    if ($content -notmatch "#$issueNum") {
        $firstLine = ($content -split "`n")[0]
        $rest = ($content -split "`n" | Select-Object -Skip 1) -join "`n"
        "$firstLine (#$issueNum)`n$rest" | Set-Content $CommitMsgFile -NoNewline
    }
}
exit 0
'''


@click.command("init")
@click.option("--mode", type=click.Choice(["local", "github", "hybrid"]), default="local",
              help="Operating mode (default: local)")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init_cmd(ctx: click.Context, mode: str, force: bool) -> None:
    """Initialize Context.md in the current Git repository.
    
    This command:
    - Creates .agent-context/ directory
    - Installs Git hooks for automation
    - Sets up configuration with selected mode
    - Initializes state tracking
    
    Modes:
    - local: Works offline, no GitHub required
    - github: Full GitHub Issues/Projects sync
    - hybrid: Local work + periodic GitHub sync
    """
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    
    # Check if we're in a Git repository
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        repo_root = find_git_root()
        if not repo_root:
            raise click.ClickException("Not in a Git repository. Run 'git init' first.")
    
    context_dir = repo_root / ".agent-context"
    
    # Check existing installation
    if context_dir.exists() and not force:
        if not quiet:
            click.echo("Context.md is already initialized in this repository.")
            click.echo("Use --force to reinitialize.")
        return
    
    if not quiet:
        click.secho("Initializing Context.md...", fg="cyan")
    
    # Create directory structure
    context_dir.mkdir(parents=True, exist_ok=True)
    
    # Create worktrees directory
    worktree_base = repo_root / ".." / "worktrees"
    worktree_base.mkdir(parents=True, exist_ok=True)
    
    # Initialize configuration
    config = Config(repo_root)
    config.mode = mode
    config.save()
    
    if verbose:
        click.echo(f"  Created config: {config.config_file}")
    
    # Initialize state
    state = State(repo_root)
    state.mode = mode
    state.save()
    
    if verbose:
        click.echo(f"  Created state: {state.state_file}")
    
    # Install Git hooks
    hooks_installed = install_hooks(repo_root, config, verbose, quiet)
    
    # Update .gitignore
    update_gitignore(repo_root, verbose, quiet)
    
    # Initialize Git notes ref
    init_git_notes(repo_root, verbose)
    
    if not quiet:
        click.echo("")
        click.secho("✅ Context.md initialized successfully!", fg="green")
        click.echo("")
        click.echo(f"   Mode: {mode}")
        click.echo(f"   Config: .agent-context/config.json")
        click.echo(f"   State: .agent-context/state.json")
        click.echo(f"   Hooks: {hooks_installed} installed")
        click.echo(f"   Worktrees: ../worktrees/")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Create an issue: context-md issue create --title 'My task'")
        click.echo("  2. Spawn a SubAgent: context-md subagent spawn <issue>")
        click.echo("  3. Generate context: context-md context generate <issue>")


def find_git_root() -> Optional[Path]:
    """Find Git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def install_hooks(repo_root: Path, config: Config, verbose: bool, quiet: bool) -> int:
    """Install Git hooks."""
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    hooks = {
        "prepare-commit-msg": PREPARE_COMMIT_MSG_HOOK,
        "pre-commit": PRE_COMMIT_HOOK,
        "post-commit": POST_COMMIT_HOOK,
        "pre-push": PRE_PUSH_HOOK,
        "post-merge": POST_MERGE_HOOK,
    }
    
    installed = 0
    for hook_name, hook_content in hooks.items():
        config_key = hook_name.replace("-", "_")
        if not config.is_hook_enabled(config_key):
            if verbose:
                click.echo(f"  Skipped hook (disabled): {hook_name}")
            continue
        
        hook_path = hooks_dir / hook_name
        
        # Backup existing hook
        if hook_path.exists():
            backup_path = hook_path.with_suffix(".backup")
            hook_path.rename(backup_path)
            if verbose:
                click.echo(f"  Backed up existing hook: {hook_name}")
        
        # Write new hook
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
        installed += 1
        
        if verbose:
            click.echo(f"  Installed hook: {hook_name}")
    
    return installed


def update_gitignore(repo_root: Path, verbose: bool, quiet: bool) -> None:
    """Update .gitignore to include Context.md files."""
    gitignore_path = repo_root / ".gitignore"
    
    entries = [
        "",
        "# Context.md runtime state",
        ".agent-context/state.json",
        ".agent-context/context-*.md",
    ]
    
    existing_content = ""
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
    
    # Check if already added
    if "# Context.md" in existing_content:
        if verbose:
            click.echo("  .gitignore already updated")
        return
    
    # Append entries
    with open(gitignore_path, "a") as f:
        f.write("\n".join(entries) + "\n")
    
    if verbose:
        click.echo("  Updated .gitignore")


def init_git_notes(repo_root: Path, verbose: bool) -> None:
    """Initialize Git notes ref for context metadata."""
    try:
        # Create the notes ref if it doesn't exist
        subprocess.run(
            ["git", "notes", "--ref=context", "list"],
            cwd=repo_root,
            capture_output=True,
            check=False
        )
        if verbose:
            click.echo("  Initialized Git notes ref: refs/notes/context")
    except subprocess.CalledProcessError:
        pass
