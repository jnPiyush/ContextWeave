"""
SubAgent Command - Manage SubAgent worktrees

Usage:
    context-weave subagent spawn <issue> --role <role>
    context-weave subagent list
    context-weave subagent status <issue>
    context-weave subagent complete <issue>
"""

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from context_weave.config import Config
from context_weave.state import State, WorktreeInfo

logger = logging.getLogger(__name__)


@click.group("subagent")
def subagent_cmd() -> None:
    """Manage SubAgent worktrees for isolated task execution.

    SubAgents run in separate Git worktrees, providing TRUE file system
    isolation. Each SubAgent has its own complete checkout of the repository.
    """


@subagent_cmd.command("spawn")
@click.argument("issue", type=int, callback=lambda ctx, param, value: value if value > 0 else ctx.fail("Issue number must be positive"))
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              required=True, help="Agent role")
@click.option("--title", "-t", help="Short description for branch name")
@click.pass_context
def spawn_cmd(ctx: click.Context, issue: int, role: str, title: Optional[str]) -> None:
    """Create a new SubAgent with an isolated worktree.

    This creates:
    1. A new branch: issue-{issue}-{title}
    2. A worktree at: ../worktrees/{issue}/
    3. State tracking entry

    Example:
        context-weave subagent spawn 456 --role engineer --title jwt-auth
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = ctx.obj.get("state", State(repo_root))
    config = ctx.obj.get("config", Config(repo_root))
    verbose = ctx.obj.get("verbose", False)

    # Check if SubAgent already exists for this issue
    existing = state.get_worktree(issue)
    if existing:
        raise click.ClickException(
            f"SubAgent already exists for issue #{issue} at {existing.path}\n"
            f"Use 'context-weave subagent complete {issue}' to finish it first."
        )

    # Generate branch name (keep under 80 chars to avoid long-path issues)
    max_branch_length = 80
    branch_suffix = title or f"task-{issue}"
    branch_suffix = re.sub(r'[^a-zA-Z0-9-]', '-', branch_suffix.lower())
    prefix = f"issue-{issue}-"
    max_suffix = max_branch_length - len(prefix)
    branch_suffix = branch_suffix[:max_suffix].rstrip("-")
    branch_name = f"{prefix}{branch_suffix}"

    # Get worktree path
    worktree_path = config.get_worktree_path(issue)

    click.echo(f"Creating SubAgent for issue #{issue}...")

    # Create branch from current HEAD
    try:
        # Check if branch already exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=repo_root, capture_output=True, text=True,
            check=False, timeout=10
        )

        if not result.stdout.strip():
            # Create new branch
            subprocess.run(
                ["git", "branch", branch_name],
                cwd=repo_root, check=True, capture_output=True
            )
            if verbose:
                click.echo(f"  Created branch: {branch_name}")
        else:
            if verbose:
                click.echo(f"  Using existing branch: {branch_name}")

        # Create worktree
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            cwd=repo_root, check=True, capture_output=True
        )
        if verbose:
            click.echo(f"  Created worktree: {worktree_path}")

        # Add to state tracking
        worktree_info = WorktreeInfo(
            issue=issue,
            branch=branch_name,
            path=str(worktree_path),
            role=role
        )
        state.add_worktree(worktree_info)
        state.save()

        # Set initial Git note metadata
        metadata = {
            "issue": issue,
            "role": role,
            "status": "spawned",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "last_activity": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "commits": 0
        }
        if not state.set_branch_note(branch_name, metadata):
            click.secho("  [WARN] Failed to update Git notes. Run 'context-weave doctor' to check.", fg="yellow")

        click.echo("")
        click.secho("[OK] SubAgent spawned successfully!", fg="green")
        click.echo("")
        click.echo(f"   Issue: #{issue}")
        click.echo(f"   Role: {role}")
        click.echo(f"   Branch: {branch_name}")
        click.echo(f"   Worktree: {worktree_path}")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  1. Generate context: context-weave context generate {issue}")
        click.echo(f"  2. Work in worktree: cd {worktree_path}")
        click.echo(f"  3. When done: context-weave subagent complete {issue}")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        raise click.ClickException(f"Failed to create SubAgent: {error_msg}") from e


@subagent_cmd.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_cmd(ctx: click.Context, as_json: bool) -> None:
    """List all active SubAgents."""
    import json

    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = ctx.obj.get("state", State(repo_root))
    worktrees = state.worktrees

    if as_json:
        data = [w.to_dict() for w in worktrees]
        click.echo(json.dumps(data, indent=2))
        return

    if not worktrees:
        click.echo("No active SubAgents.")
        click.echo("")
        click.echo("Create one with: context-weave subagent spawn <issue> --role <role>")
        return

    click.echo(f"Active SubAgents: {len(worktrees)}")
    click.echo("")

    for wt in worktrees:
        # Get last commit time
        last_commit = state.get_last_commit_time(wt.branch)
        if last_commit:
            delta = datetime.now(timezone.utc) - last_commit.replace(tzinfo=timezone.utc)
            hours = delta.total_seconds() / 3600
            if hours < 1:
                time_ago = f"{int(delta.total_seconds() / 60)}m ago"
            elif hours < 24:
                time_ago = f"{int(hours)}h ago"
            else:
                time_ago = f"{int(hours / 24)}d ago"
        else:
            time_ago = "no commits"

        # Get metadata from Git notes
        metadata = state.get_branch_note(wt.branch) or {}
        status = metadata.get("status", "unknown")
        commits = metadata.get("commits", 0)

        click.echo(f"  Issue #{wt.issue} ({wt.role})")
        click.echo(f"    Branch: {wt.branch}")
        click.echo(f"    Path: {wt.path}")
        click.echo(f"    Status: {status}")
        click.echo(f"    Commits: {commits} (last: {time_ago})")
        click.echo("")


@subagent_cmd.command("status")
@click.argument("issue", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def status_cmd(ctx: click.Context, issue: int, as_json: bool) -> None:
    """Show detailed status of a SubAgent."""
    import json

    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = ctx.obj.get("state", State(repo_root))
    worktree = state.get_worktree(issue)

    if not worktree:
        raise click.ClickException(f"No SubAgent found for issue #{issue}")

    # Get Git notes metadata
    metadata = state.get_branch_note(worktree.branch) or {}

    # Get last commit info
    last_commit = state.get_last_commit_time(worktree.branch)

    # Check worktree exists
    worktree_exists = Path(worktree.path).exists()

    # Get changed files count
    changed_files = 0
    if worktree_exists:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree.path,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
                timeout=10
            )
            if result.returncode == 0:
                changed_files = len([line for line in result.stdout.strip().split("\n") if line])
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking git status in worktree")
            changed_files = 0

    data = {
        "issue": issue,
        "branch": worktree.branch,
        "path": worktree.path,
        "role": worktree.role,
        "created_at": worktree.created_at,
        "worktree_exists": worktree_exists,
        "last_commit": last_commit.isoformat() if last_commit else None,
        "changed_files": changed_files,
        "metadata": metadata
    }

    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
        return

    click.echo(f"SubAgent Status: Issue #{issue}")
    click.echo("=" * 40)
    click.echo(f"  Role: {worktree.role}")
    click.echo(f"  Branch: {worktree.branch}")
    click.echo(f"  Path: {worktree.path}")
    click.echo(f"  Worktree exists: {'[OK]' if worktree_exists else '[MISSING]'}")
    click.echo(f"  Created: {worktree.created_at}")
    click.echo(f"  Last commit: {last_commit or 'N/A'}")
    click.echo(f"  Changed files: {changed_files}")
    click.echo("")
    click.echo("Metadata (from Git notes):")
    for key, value in metadata.items():
        click.echo(f"  {key}: {value}")


@subagent_cmd.command("complete")
@click.argument("issue", type=int)
@click.option("--force", is_flag=True, help="Force completion without validation")
@click.option("--keep-branch", is_flag=True, help="Keep the branch after removing worktree")
@click.option("--push", is_flag=True, help="Push branch to remote before cleanup")
@click.option("--create-pr", is_flag=True, help="Create a pull request (implies --push)")
@click.pass_context
def complete_cmd(ctx: click.Context, issue: int, force: bool, keep_branch: bool,
                 push: bool, create_pr: bool) -> None:
    """Mark SubAgent work as complete and clean up.

    This:
    1. Validates DoD (unless --force)
    2. Removes the worktree
    3. Updates state tracking
    4. Optionally keeps/deletes the branch
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = ctx.obj.get("state", State(repo_root))
    worktree = state.get_worktree(issue)

    if not worktree:
        raise click.ClickException(f"No SubAgent found for issue #{issue}")

    # Capture role before any removal
    role = worktree.role

    click.echo(f"Completing SubAgent for issue #{issue}...")

    # Check for uncommitted changes
    worktree_path = Path(worktree.path)
    if worktree_path.exists():
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree.path, capture_output=True, text=True,
                check=True, timeout=10
            )
            if result.stdout.strip() and not force:
                raise click.ClickException(
                    "Worktree has uncommitted changes. Commit or stash them first.\n"
                    "Use --force to discard changes."
                )
        except subprocess.TimeoutExpired as e:
            logger.error("Timeout checking git status in %s", worktree.path)
            if not force:
                raise click.ClickException("Timeout checking git status. Use --force to proceed anyway.") from e
        except subprocess.CalledProcessError as e:
            logger.error("Failed to check git status: %s", e)
            if not force:
                raise

    # Push branch if requested
    if create_pr:
        push = True

    if push:
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", worktree.branch],
                cwd=repo_root, check=True, capture_output=True, timeout=60
            )
            click.echo(f"  Pushed branch: {worktree.branch}")
        except subprocess.CalledProcessError as e:
            click.secho(f"  [WARN] Failed to push: {e}", fg="yellow")
        except FileNotFoundError:
            click.secho("  [WARN] git not found for push", fg="yellow")

    if create_pr:
        try:
            pr_title = (
                f"Issue #{issue}: "
                f"{worktree.branch.replace(f'issue-{issue}-', '').replace('-', ' ').title()}"
            )
            result = subprocess.run(
                ["gh", "pr", "create",
                 "--title", pr_title,
                 "--body", f"Closes #{issue}\n\nCreated by ContextWeave subagent ({worktree.role}).",
                 "--head", worktree.branch],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
                check=False
            )
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                click.echo(f"  Created PR: {pr_url}")
            else:
                click.secho(f"  [WARN] PR creation failed: {result.stderr.strip()}", fg="yellow")
                click.echo("  Create manually: gh pr create")
        except FileNotFoundError:
            click.secho(
                "  [WARN] GitHub CLI (gh) not found. Install from https://cli.github.com/",
                fg="yellow"
            )

    # Remove worktree
    try:
        if worktree_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"] if force
                else ["git", "worktree", "remove", str(worktree_path)],
                cwd=repo_root, check=True, capture_output=True
            )
            click.echo(f"  Removed worktree: {worktree.path}")
    except subprocess.CalledProcessError as e:
        if not force:
            raise click.ClickException(f"Failed to remove worktree: {e}") from e

    # Update Git note
    metadata = state.get_branch_note(worktree.branch) or {}
    metadata["status"] = "completed"
    metadata["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if not state.set_branch_note(worktree.branch, metadata):
        click.secho("  [WARN] Failed to update Git notes. Run 'context-weave doctor' to check.", fg="yellow")

    # Remove from state
    state.remove_worktree(issue)
    state.save()
    click.echo("  Updated state tracking")

    # Record completion to memory layer
    try:
        from context_weave.memory import ExecutionRecord, Memory
        memory = Memory(repo_root)
        outcome = "partial" if force else "success"
        record = ExecutionRecord(
            issue=issue,
            role=role,
            action="complete",
            outcome=outcome,
        )
        memory.record_execution(record)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to record completion to memory: %s", e)

    # Optionally delete branch
    if not keep_branch:
        # Check if branch has been merged
        try:
            result = subprocess.run(
                ["git", "branch", "--merged", "main"],
                cwd=repo_root, capture_output=True, text=True,
                check=True, timeout=10
            )
            merged_branches = result.stdout.strip().split("\n")

            if any(worktree.branch in b for b in merged_branches):
                subprocess.run(
                    ["git", "branch", "-d", worktree.branch],
                    cwd=repo_root, check=True, capture_output=True
                )
                click.echo(f"  Deleted merged branch: {worktree.branch}")
            else:
                click.echo(f"  Kept unmerged branch: {worktree.branch}")
        except subprocess.CalledProcessError:
            click.echo(f"  Kept branch: {worktree.branch}")

    click.echo("")
    click.secho(f"[OK] SubAgent completed for issue #{issue}", fg="green")


@subagent_cmd.command("recover")
@click.argument("issue", type=int)
@click.pass_context
def recover_cmd(ctx: click.Context, issue: int) -> None:
    """Recover a corrupted or missing worktree."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = ctx.obj.get("state", State(repo_root))

    worktree = state.get_worktree(issue)

    if not worktree:
        raise click.ClickException(f"No SubAgent found for issue #{issue}")

    worktree_path = Path(worktree.path)

    click.echo(f"Recovering SubAgent for issue #{issue}...")

    # Prune stale worktrees
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=repo_root,
        capture_output=True,
        check=False,  # Don't fail if prune has nothing to do
        timeout=30
    )

    # Check if worktree exists
    if worktree_path.exists():
        click.echo("  Worktree exists, no recovery needed.")
        return

    # Check if branch exists
    result = subprocess.run(
        ["git", "branch", "--list", worktree.branch],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,  # Check result manually
        timeout=10
    )

    if not result.stdout.strip():
        raise click.ClickException(
            f"Branch {worktree.branch} not found. Cannot recover.\n"
            f"Use 'context-weave subagent complete {issue} --force' to clean up state."
        )

    # Recreate worktree
    try:
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), worktree.branch],
            cwd=repo_root,
            check=True,
            capture_output=True,
            timeout=60
        )
        click.secho(f"[OK] Worktree recovered at: {worktree_path}", fg="green")
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Failed to recover worktree: {e}") from e


ROLE_NEXT = {
    "pm": "architect",
    "architect": "engineer",
    "engineer": "reviewer",
    "reviewer": None,
    "ux": "engineer",
}


@subagent_cmd.command("handoff")
@click.argument("issue", type=int)
@click.option("--to", "to_role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              help="Target role (auto-detected if omitted)")
@click.option("--skip-validation", is_flag=True, help="Skip DoD check before handoff")
@click.pass_context
def handoff_cmd(ctx: click.Context, issue: int, to_role: Optional[str],
                skip_validation: bool) -> None:
    """Hand off work to the next role in the workflow.

    Validates DoD for current role, updates status, and generates
    fresh context for the next role.

    \b
    Role flow: PM -> Architect -> Engineer -> Reviewer
    UX Designer can hand off to Engineer at any point.

    \b
    Examples:
        context-weave subagent handoff 42
        context-weave subagent handoff 42 --to reviewer
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a ContextWeave repository.")

    state = ctx.obj.get("state", State(repo_root))
    config = ctx.obj.get("config", Config(repo_root))

    worktree = state.get_worktree(issue)
    if not worktree:
        raise click.ClickException(f"No active SubAgent for issue #{issue}")

    current_role = worktree.role
    next_role = to_role or ROLE_NEXT.get(current_role)

    if not next_role:
        raise click.ClickException(
            f"No next role after '{current_role}'. Use --to to specify, "
            "or use 'subagent complete' to finish."
        )

    click.echo(f"Handing off issue #{issue}: {current_role} -> {next_role}")

    # Validate DoD for current role (unless skipped)
    if not skip_validation:
        from context_weave.commands.validate import _run_dod_checks_for_role
        passed, total = _run_dod_checks_for_role(repo_root, issue, current_role, state)
        if passed < total:
            raise click.ClickException(
                f"DoD validation: {passed}/{total} checks passed.\n"
                f"Fix issues or use --skip-validation to force handoff."
            )
        click.echo(f"  DoD: {passed}/{total} checks passed")

    # Update worktree role in state
    state.update_worktree_role(issue, next_role)
    state.save()

    # Update Git note with handoff info
    metadata = state.get_branch_note(worktree.branch) or {}
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata["status"] = "handoff"
    metadata["role"] = next_role
    metadata["handoff_from"] = current_role
    metadata["handoff_to"] = next_role
    metadata["handoff_at"] = now
    metadata["last_activity"] = now
    if not state.set_branch_note(worktree.branch, metadata):
        click.secho("  [WARN] Failed to update Git notes. Run 'context-weave doctor' to check.", fg="yellow")

    # Generate fresh context for the next role
    click.echo(f"  Generating context for {next_role}...")
    from context_weave.commands.context import generate_context_file
    generate_context_file(
        issue=issue, repo_root=repo_root, state=state,
        config=config, role=next_role, verbose=False
    )

    click.echo("")
    click.secho(f"[OK] Handed off to {next_role}", fg="green")
    click.echo("")
    click.echo(f"  Issue: #{issue}")
    click.echo(f"  From: {current_role}")
    click.echo(f"  To: {next_role}")
    click.echo(f"  Context: .context-weave/context-{issue}.md")
    click.echo("")
    click.echo("Next agent should review the updated context and continue work.")

