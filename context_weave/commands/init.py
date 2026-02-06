"""
Init Command - Initialize ContextWeave in a repository

Usage:
    context-weave init [--mode local|github|hybrid] [--force]
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import click

from context_weave.config import Config
from context_weave.scaffolds import get_scaffolds_dir
from context_weave.state import State

# Git hook scripts
PREPARE_COMMIT_MSG_HOOK = '''#!/bin/bash
# ContextWeave: Auto-add issue reference from branch name

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Skip if message already has issue reference or is a merge/squash
if [ "$COMMIT_SOURCE" = "merge" ] || [ "$COMMIT_SOURCE" = "squash" ]; then
    exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Extract issue number from branch name (e.g., issue-456-jwt -> 456)
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
# ContextWeave: Pre-commit validation

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only validate on issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0
fi

ISSUE_NUM="${BASH_REMATCH[1]}"
CONTEXT_FILE=".context-weave/context-$ISSUE_NUM.md"

# Check if context file exists (warning only, don't block)
if [ ! -f "$CONTEXT_FILE" ]; then
    echo "[WARNING] Context file not found: $CONTEXT_FILE"
    echo "   Consider running: context-weave context generate $ISSUE_NUM"
fi

# Run standard checks (if available)
if command -v ruff &> /dev/null; then
    git diff --cached --name-only --diff-filter=ACM | grep '\\.py$' | xargs -r ruff check --fix
fi

exit 0
'''

POST_COMMIT_HOOK = '''#!/bin/bash
# ContextWeave: Post-commit activity tracking

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
# ContextWeave: Pre-push DoD validation

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only validate on issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0
fi

ISSUE_NUM="${BASH_REMATCH[1]}"

# Run DoD validation if context-weave is available
if command -v context-weave &> /dev/null; then
    context-weave validate $ISSUE_NUM --dod --quiet
    if [ $? -ne 0 ]; then
        echo ""
        echo "[FAIL] Definition of Done validation failed!"
        echo "   Run: context-weave validate $ISSUE_NUM --dod --verbose"
        echo ""
        echo "   To bypass (not recommended): git push --no-verify"
        exit 1
    fi
    echo "[OK] DoD validation passed"
fi

exit 0
'''

POST_MERGE_HOOK = '''#!/bin/bash
# ContextWeave: Post-merge cleanup and certificate generation

# Get the merged branch (if available from reflog)
MERGED_BRANCH=$(git reflog -1 | grep -oP "merge \\K[^:]+")

if [[ $MERGED_BRANCH =~ ^issue-([0-9]+) ]]; then
    ISSUE_NUM="${BASH_REMATCH[1]}"

    # Generate completion certificate if context-weave is available
    if command -v context-weave &> /dev/null; then
        context-weave validate $ISSUE_NUM --certificate --quiet 2>/dev/null || true
    fi

    echo "[OK] Issue #$ISSUE_NUM merged successfully"
fi

exit 0
'''

# PowerShell versions for Windows
PREPARE_COMMIT_MSG_HOOK_PS = r'''#!/usr/bin/env pwsh
# ContextWeave: Auto-add issue reference from branch name

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
    """Initialize ContextWeave in the current Git repository.

    This command:
    - Creates .context-weave/ directory
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

    context_dir = repo_root / ".context-weave"

    # Check existing installation
    if context_dir.exists() and not force:
        if not quiet:
            click.echo("ContextWeave is already initialized in this repository.")
            click.echo("Use --force to reinitialize.")
        return

    if not quiet:
        click.secho("Initializing ContextWeave...", fg="cyan")

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

    # Deploy .github scaffolds (agents, instructions, prompts, templates)
    scaffolds_deployed = deploy_github_scaffolds(repo_root, force, verbose, quiet)

    # Install Git hooks
    hooks_installed = install_hooks(repo_root, config, verbose, quiet)

    # Update .gitignore
    update_gitignore(repo_root, verbose, quiet)

    # Initialize Git notes ref
    init_git_notes(repo_root, verbose)

    if not quiet:
        click.echo("")
        click.secho("Done! ContextWeave initialized successfully!", fg="green")
        click.echo("")
        click.echo(f"   Mode: {mode}")
        click.echo("   Config: .context-weave/config.json")
        click.echo("   State: .context-weave/state.json")
        click.echo(f"   Hooks: {hooks_installed} installed")
        click.echo(f"   Agents: {scaffolds_deployed} files deployed to .github/")
        click.echo("   Worktrees: ../worktrees/")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Create an issue: context-weave issue create --title 'My task'")
        click.echo("  2. Spawn a SubAgent: context-weave subagent spawn <issue>")
        click.echo("  3. Generate context: context-weave context generate <issue>")


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


def deploy_github_scaffolds(
    repo_root: Path, force: bool, verbose: bool, quiet: bool
) -> int:
    """Deploy .github scaffold files (agents, instructions, prompts, templates).

    Copies bundled scaffold files from the installed package into the target
    repository's .github/ directory. This enables VS Code Copilot to discover
    sub-agents from .github/agents/*.agent.md files.

    Args:
        repo_root: Root of the target Git repository.
        force: If True, overwrite existing files.
        verbose: If True, print detailed progress.
        quiet: If True, suppress output.

    Returns:
        Number of scaffold files deployed.
    """
    scaffolds_dir = get_scaffolds_dir() / "github"
    if not scaffolds_dir.exists():
        if verbose:
            click.echo("  [WARNING] Scaffolds directory not found in package.")
        return 0

    target_github_dir = repo_root / ".github"
    deployed = 0

    # Directories to deploy: agents, instructions, prompts, templates
    scaffold_dirs = ["agents", "instructions", "prompts", "templates"]

    for subdir in scaffold_dirs:
        src_dir = scaffolds_dir / subdir
        if not src_dir.exists():
            continue

        dst_dir = target_github_dir / subdir
        dst_dir.mkdir(parents=True, exist_ok=True)

        for src_file in src_dir.iterdir():
            if not src_file.is_file():
                continue
            dst_file = dst_dir / src_file.name
            if dst_file.exists() and not force:
                if verbose:
                    click.echo(f"  Skipped (exists): .github/{subdir}/{src_file.name}")
                continue
            shutil.copy2(src_file, dst_file)
            deployed += 1
            if verbose:
                click.echo(f"  Deployed: .github/{subdir}/{src_file.name}")

    # Deploy copilot-instructions.md at .github/ root
    copilot_src = scaffolds_dir / "copilot-instructions.md"
    if copilot_src.exists():
        target_github_dir.mkdir(parents=True, exist_ok=True)
        copilot_dst = target_github_dir / "copilot-instructions.md"
        if not copilot_dst.exists() or force:
            shutil.copy2(copilot_src, copilot_dst)
            deployed += 1
            if verbose:
                click.echo("  Deployed: .github/copilot-instructions.md")
        elif verbose:
            click.echo("  Skipped (exists): .github/copilot-instructions.md")

    # Deploy AGENTS.md and Skills.md to repo root (referenced by agent definitions)
    scaffolds_root = get_scaffolds_dir()
    for root_file in ["AGENTS.md", "Skills.md"]:
        src = scaffolds_root / root_file
        if src.exists():
            dst = repo_root / root_file
            if not dst.exists() or force:
                shutil.copy2(src, dst)
                deployed += 1
                if verbose:
                    click.echo(f"  Deployed: {root_file}")
            elif verbose:
                click.echo(f"  Skipped (exists): {root_file}")

    if not quiet and deployed > 0:
        click.echo(f"  Deployed {deployed} scaffold files to .github/")

    return deployed


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
    """Update .gitignore to include ContextWeave files."""
    gitignore_path = repo_root / ".gitignore"

    entries = [
        "",
        "# ContextWeave runtime state",
        ".context-weave/state.json",
        ".context-weave/context-*.md",
    ]

    existing_content = ""
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()

    # Check if already added
    if "# ContextWeave" in existing_content:
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
