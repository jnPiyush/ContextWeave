"""
Start Command - Quick-start workflow combining issue + subagent + context

Usage:
    context-weave start "Add login page"
    context-weave start "Fix auth bug" --type bug --role engineer
"""

import re
import subprocess
from datetime import datetime, timezone
from typing import Optional

import click

from context_weave.config import Config
from context_weave.state import State, WorktreeInfo

# Maximum branch name length (Git has a 255-byte limit for refs;
# keep well under to avoid issues on Windows with long paths)
MAX_BRANCH_LENGTH = 80


@click.command("start")
@click.argument("title")
@click.option("--type", "issue_type",
              type=click.Choice(["epic", "feature", "story", "bug", "spike", "docs"]),
              default="story", help="Issue type")
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              default="engineer", help="Agent role (default: engineer)")
@click.option("--label", "-l", "labels", multiple=True, help="Labels")
@click.option("--body", "-b", help="Issue description")
@click.pass_context
def start_cmd(ctx: click.Context, title: str, issue_type: str, role: str,
              labels: tuple, body: Optional[str]) -> None:
    """Quick-start: create issue, spawn subagent, and generate context.

    Combines `issue create` + `subagent spawn` + `context generate` into
    a single command for the common workflow.

    \b
    Examples:
        context-weave start "Add login page"
        context-weave start "Fix auth bug" --type bug
        context-weave start "Design API" --role architect --label api
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a ContextWeave repository. Run 'context-weave init' first.")

    state = ctx.obj.get("state", State(repo_root))
    config = ctx.obj.get("config", Config(repo_root))

    # --- Step 1: Create local issue (reuse sanitization from issue module) ---
    from context_weave.commands.issue import (
        MAX_BODY_LENGTH,
        MAX_TITLE_LENGTH,
        _sanitize_label,
        _sanitize_text,
    )

    click.echo("Creating issue...")

    sanitized_title = _sanitize_text(title, MAX_TITLE_LENGTH, "title")
    sanitized_body = _sanitize_text(body, MAX_BODY_LENGTH, "body") if body else ""
    sanitized_labels = [_sanitize_label(lbl) for lbl in labels if _sanitize_label(lbl)]

    existing_issues = state.local_issues
    issue_number = max((int(k) for k in existing_issues), default=0) + 1

    all_labels = list(sanitized_labels)
    type_label = f"type:{issue_type}"
    if type_label not in all_labels:
        all_labels.append(type_label)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    issue_data = {
        "number": issue_number,
        "title": sanitized_title,
        "body": sanitized_body,
        "state": "open",
        "labels": all_labels,
        "type": issue_type,
        "role": role,
        "created_at": now,
        "updated_at": now,
    }
    state.local_issues[str(issue_number)] = issue_data
    state.save()

    # --- Step 2: Spawn subagent ---
    click.echo("Spawning subagent...")

    branch_suffix = re.sub(r'[^a-zA-Z0-9-]', '-', sanitized_title.lower())
    # Trim suffix so total branch name stays under MAX_BRANCH_LENGTH
    prefix = f"issue-{issue_number}-"
    max_suffix = MAX_BRANCH_LENGTH - len(prefix)
    branch_suffix = branch_suffix[:max_suffix].rstrip("-")
    branch_name = f"{prefix}{branch_suffix}"
    worktree_path = config.get_worktree_path(issue_number)

    try:
        # Create branch
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=repo_root, capture_output=True, text=True,
            check=False, timeout=10
        )
        if not result.stdout.strip():
            subprocess.run(
                ["git", "branch", branch_name],
                cwd=repo_root, check=True, capture_output=True
            )

        # Create worktree
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            cwd=repo_root, check=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        raise click.ClickException(f"Failed to create subagent: {error_msg}") from e

    # Track worktree
    worktree_info = WorktreeInfo(
        issue=issue_number, branch=branch_name,
        path=str(worktree_path), role=role
    )
    state.add_worktree(worktree_info)

    # Set Git note metadata
    metadata = {
        "issue": issue_number,
        "role": role,
        "type": issue_type,
        "title": sanitized_title,
        "description": sanitized_body or f"Complete issue #{issue_number}",
        "labels": all_labels,
        "status": "in_progress",
        "created_at": now,
        "last_activity": now,
        "commits": 0,
    }
    state.set_branch_note(branch_name, metadata)
    state.save()

    # --- Step 3: Generate context ---
    click.echo("Generating context...")
    from context_weave.commands.context import generate_context_file
    generate_context_file(
        issue=issue_number, repo_root=repo_root,
        state=state, config=config, role=role, verbose=False
    )

    # --- Summary ---
    click.echo("")
    click.secho(f"[OK] Ready to work on issue #{issue_number}!", fg="green")
    click.echo("")
    click.echo(f"  Issue: #{issue_number} - {sanitized_title}")
    click.echo(f"  Role: {role}")
    click.echo(f"  Branch: {branch_name}")
    click.echo(f"  Worktree: {worktree_path}")
    click.echo(f"  Context: .context-weave/context-{issue_number}.md")
    click.echo("")
    click.echo(f"Start working: cd {worktree_path}")

