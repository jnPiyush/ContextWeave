"""
Doctor Command - Diagnose and fix common issues

Usage:
    context-weave doctor
    context-weave doctor --fix
"""

import shutil
import subprocess
from pathlib import Path

import click

from context_weave.config import Config
from context_weave.state import State


@click.command("doctor")
@click.option("--fix", is_flag=True, help="Auto-fix issues where possible")
@click.pass_context
def doctor_cmd(ctx: click.Context, fix: bool) -> None:
    """Diagnose and fix common ContextWeave issues.

    Checks:
    - Git hooks installed and intact
    - Worktrees in state match disk
    - Git notes ref exists
    - Required tools available
    - Config validity

    \b
    Examples:
        context-weave doctor
        context-weave doctor --fix
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository.")

    click.echo("")
    click.secho("ContextWeave Doctor", fg="cyan", bold=True)
    click.echo("")

    issues_found = 0
    issues_fixed = 0

    # Check 1: Initialization
    state_file = repo_root / ".context-weave" / "state.json"
    if not state_file.exists():
        click.echo("  [FAIL] ContextWeave not initialized")
        click.echo("         Run: context-weave init")
        issues_found += 1
        return  # Can't check anything else

    click.echo("  [OK] ContextWeave initialized")

    state = ctx.obj.get("state", State(repo_root))
    config = ctx.obj.get("config", Config(repo_root))

    # Check 2: Git hooks
    hooks_dir = repo_root / ".git" / "hooks"
    expected_hooks = ["prepare-commit-msg", "pre-commit", "post-commit", "pre-push", "post-merge"]
    for hook_name in expected_hooks:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            click.echo(f"  [FAIL] Missing hook: {hook_name}")
            issues_found += 1
            if fix:
                from context_weave.commands.init import install_hooks
                install_hooks(repo_root, config, verbose=False, quiet=True)
                click.echo("         Fixed: reinstalled hooks")
                issues_fixed += 1
                break  # install_hooks does all at once
        elif "ContextWeave" not in hook_path.read_text(encoding="utf-8", errors="ignore"):
            click.echo(f"  [WARN] Hook exists but not ContextWeave's: {hook_name}")
            issues_found += 1
        else:
            click.echo(f"  [OK] Hook: {hook_name}")

    # Check 3: Worktree state vs disk
    for wt in state.worktrees:
        wt_path = Path(wt.path)
        if wt_path.exists():
            click.echo(f"  [OK] Worktree #{wt.issue}: {wt.path}")
        else:
            click.echo(f"  [FAIL] Worktree #{wt.issue} missing on disk: {wt.path}")
            issues_found += 1
            if fix:
                # Try to recover
                try:
                    subprocess.run(
                        ["git", "worktree", "prune"],
                        cwd=repo_root, capture_output=True, check=False, timeout=10
                    )
                    branch_check = subprocess.run(
                        ["git", "branch", "--list", wt.branch],
                        cwd=repo_root, capture_output=True, text=True,
                        check=False, timeout=10
                    )
                    if branch_check.stdout.strip():
                        wt_path.parent.mkdir(parents=True, exist_ok=True)
                        subprocess.run(
                            ["git", "worktree", "add", str(wt_path), wt.branch],
                            cwd=repo_root, check=True, capture_output=True, timeout=30
                        )
                        click.echo("         Fixed: recovered worktree from branch")
                        issues_fixed += 1
                    else:
                        state.remove_worktree(wt.issue)
                        state.save()
                        click.echo("         Fixed: removed stale entry (branch gone)")
                        issues_fixed += 1
                except subprocess.CalledProcessError:
                    click.echo(f"         Could not auto-fix. Run: context-weave subagent recover {wt.issue}")

    # Check 4: Git notes ref
    try:
        subprocess.run(
            ["git", "notes", "--ref=context", "list"],
            cwd=repo_root, capture_output=True, check=True, timeout=10
        )
        click.echo("  [OK] Git notes ref: refs/notes/context")
    except subprocess.CalledProcessError:
        click.echo("  [WARN] Git notes ref not initialized")
        issues_found += 1
        if fix:
            from context_weave.commands.init import init_git_notes
            init_git_notes(repo_root, verbose=False)
            click.echo("         Fixed: initialized git notes ref")
            issues_fixed += 1

    # Check 5: Required tools
    for tool in ["git", "ruff", "pytest"]:
        if shutil.which(tool):
            click.echo(f"  [OK] Tool: {tool}")
        else:
            level = "FAIL" if tool == "git" else "WARN"
            click.echo(f"  [{level}] Tool not found: {tool}")
            if tool != "git":
                issues_found += 1

    # Check 6: Config validity
    mode = config.mode
    if mode in ("local", "github", "hybrid"):
        click.echo(f"  [OK] Config mode: {mode}")
    else:
        click.echo(f"  [FAIL] Invalid config mode: {mode}")
        issues_found += 1
        if fix:
            config.mode = "local"
            config.save()
            click.echo("         Fixed: reset mode to 'local'")
            issues_fixed += 1

    # Check 7: GitHub token (if github/hybrid mode)
    if mode in ("github", "hybrid"):
        if state.github_token:
            click.echo("  [OK] GitHub token configured")
        else:
            click.echo("  [WARN] No GitHub token. Run: context-weave auth login")
            issues_found += 1

    # Summary
    click.echo("")
    if issues_found == 0:
        click.secho("All checks passed!", fg="green")
    elif fix:
        click.secho(f"Found {issues_found} issue(s), fixed {issues_fixed}.", fg="yellow")
        if issues_found > issues_fixed:
            click.echo("Some issues require manual intervention.")
    else:
        click.secho(f"Found {issues_found} issue(s). Run with --fix to auto-repair.", fg="yellow")
    click.echo("")
