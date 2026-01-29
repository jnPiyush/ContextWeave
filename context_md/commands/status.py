"""
Status Command - Show Context.md status and dashboard

Usage:
    context-md status
    context-md status --watch
    context-md dashboard
"""

import click
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from context_md.state import State
from context_md.config import Config


@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--watch", "-w", is_flag=True, help="Continuously update")
@click.pass_context
def status_cmd(ctx: click.Context, as_json: bool, watch: bool) -> None:
    """Show current Context.md status.
    
    Displays:
    - Operating mode
    - Active SubAgents and their status
    - Recent activity
    - Stuck issues
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository.")
    
    state = ctx.obj.get("state")
    config = ctx.obj.get("config")
    
    if not state:
        state_file = repo_root / ".agent-context" / "state.json"
        if not state_file.exists():
            click.echo("Context.md not initialized.")
            click.echo("Run: context-md init")
            return
        state = State(repo_root)
        config = Config(repo_root)
    
    if watch:
        _watch_status(repo_root, state, config)
        return
    
    status_data = _collect_status(repo_root, state, config)
    
    if as_json:
        click.echo(json.dumps(status_data, indent=2, default=str))
        return
    
    _display_status(status_data, config)


def _collect_status(repo_root: Path, state: State, config: Config) -> Dict[str, Any]:
    """Collect all status information."""
    worktrees = state.worktrees
    branches = state.get_issue_branches()
    
    # Analyze worktrees
    worktree_info = []
    stuck_issues = []
    
    for wt in worktrees:
        last_commit = state.get_last_commit_time(wt.branch)
        metadata = state.get_branch_note(wt.branch) or {}
        
        # Calculate hours since last activity
        hours_inactive = 0
        if last_commit:
            delta = datetime.utcnow() - last_commit.replace(tzinfo=None)
            hours_inactive = delta.total_seconds() / 3600
        
        # Check if stuck
        issue_type = metadata.get("type", "story")
        threshold = config.get_stuck_threshold(issue_type)
        is_stuck = hours_inactive > threshold
        
        info = {
            "issue": wt.issue,
            "branch": wt.branch,
            "path": wt.path,
            "role": wt.role,
            "status": metadata.get("status", "unknown"),
            "commits": metadata.get("commits", 0),
            "last_commit": last_commit.isoformat() if last_commit else None,
            "hours_inactive": round(hours_inactive, 1),
            "is_stuck": is_stuck
        }
        worktree_info.append(info)
        
        if is_stuck:
            stuck_issues.append(info)
    
    # Count by role
    by_role = {}
    for wt in worktree_info:
        role = wt["role"]
        by_role[role] = by_role.get(role, 0) + 1
    
    # Count by status
    by_status = {}
    for wt in worktree_info:
        status = wt["status"]
        by_status[status] = by_status.get(status, 0) + 1
    
    return {
        "mode": state.mode,
        "initialized": state.is_initialized(),
        "github_enabled": state.github.enabled,
        "total_branches": len(branches),
        "active_subagents": len(worktrees),
        "stuck_issues": len(stuck_issues),
        "by_role": by_role,
        "by_status": by_status,
        "worktrees": worktree_info,
        "stuck": stuck_issues,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def _display_status(data: Dict[str, Any], config: Config) -> None:
    """Display status in a nice format."""
    # Header
    click.echo("")
    click.secho("┌─────────────────────────────────────────────────────────┐", fg="cyan")
    click.secho("│ Context.md Status                                        │", fg="cyan")
    click.secho("└─────────────────────────────────────────────────────────┘", fg="cyan")
    click.echo("")
    
    # Mode and summary
    mode_color = {"local": "yellow", "github": "green", "hybrid": "blue"}.get(data["mode"], "white")
    click.echo(f"  Mode: ", nl=False)
    click.secho(data["mode"], fg=mode_color)
    click.echo(f"  Issue Branches: {data['total_branches']}")
    click.echo(f"  Active SubAgents: {data['active_subagents']}")
    
    if data["stuck_issues"] > 0:
        click.secho(f"  ⚠️  Stuck Issues: {data['stuck_issues']}", fg="red")
    
    click.echo("")
    
    # SubAgents
    if data["worktrees"]:
        click.secho("  Active SubAgents:", bold=True)
        click.echo("")
        
        for wt in data["worktrees"]:
            # Status indicator
            if wt["is_stuck"]:
                status_icon = "🔴"
                status_color = "red"
            elif wt["status"] == "spawned":
                status_icon = "🟡"
                status_color = "yellow"
            else:
                status_icon = "🟢"
                status_color = "green"
            
            # Format time ago
            if wt["hours_inactive"] < 1:
                time_ago = "< 1h ago"
            elif wt["hours_inactive"] < 24:
                time_ago = f"{int(wt['hours_inactive'])}h ago"
            else:
                time_ago = f"{int(wt['hours_inactive'] / 24)}d ago"
            
            click.echo(f"  {status_icon} ", nl=False)
            click.secho(f"Issue #{wt['issue']}", fg=status_color, bold=True, nl=False)
            click.echo(f" ({wt['role']})")
            click.echo(f"      Branch: {wt['branch']}")
            click.echo(f"      Path: {wt['path']}")
            click.echo(f"      Commits: {wt['commits']} (last: {time_ago})")
            click.echo("")
    else:
        click.echo("  No active SubAgents.")
        click.echo("")
        click.echo("  Create one with: context-md subagent spawn <issue> --role <role>")
    
    click.echo("")
    
    # Summary by role
    if data["by_role"]:
        click.echo("  By Role: ", nl=False)
        parts = [f"{role}: {count}" for role, count in data["by_role"].items()]
        click.echo(" | ".join(parts))
    
    # Stuck issues warning
    if data["stuck"]:
        click.echo("")
        click.secho("  ⚠️  Stuck Issues (no activity):", fg="red", bold=True)
        for stuck in data["stuck"]:
            click.echo(f"      • #{stuck['issue']} - {stuck['hours_inactive']:.0f}h inactive")
    
    click.echo("")


def _watch_status(repo_root: Path, state: State, config: Config) -> None:
    """Watch mode - continuously update status."""
    import time
    
    click.echo("Watching status (Ctrl+C to stop)...")
    click.echo("")
    
    try:
        while True:
            # Clear screen
            click.clear()
            
            # Reload state
            state._load()
            
            # Collect and display
            data = _collect_status(repo_root, state, config)
            _display_status(data, config)
            
            click.echo(f"  Updated: {data['timestamp']}")
            click.echo("  (refreshing every 5s, Ctrl+C to stop)")
            
            time.sleep(5)
    except KeyboardInterrupt:
        click.echo("")
        click.echo("Stopped watching.")
