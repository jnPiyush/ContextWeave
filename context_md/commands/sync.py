"""
Sync Command - Synchronize with GitHub

Usage:
    context-md sync
    context-md sync --push
    context-md sync --pull
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import click

from context_md.config import Config
from context_md.state import State

GITHUB_API_URL = "https://api.github.com"


@click.group("sync", invoke_without_command=True)
@click.option("--push", is_flag=True, help="Push local changes to GitHub")
@click.option("--pull", is_flag=True, help="Pull changes from GitHub")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without doing it")
@click.pass_context
def sync_cmd(ctx: click.Context, push: bool, pull: bool, dry_run: bool) -> None:
    """Synchronize local state with GitHub.
    
    In 'github' mode, syncs issues, labels, and project status with GitHub.
    In 'local' mode, shows current local state.
    
    \b
    Examples:
        context-md sync           # Show sync status
        context-md sync --push    # Push local changes to GitHub
        context-md sync --pull    # Pull updates from GitHub
    """
    repo_root = ctx.obj.get("repo_root")
    verbose = ctx.obj.get("verbose", False)

    if not repo_root:
        raise click.ClickException("Not in a Git repository with Context.md initialized.")

    config = ctx.obj.get("config", Config(repo_root))
    state = ctx.obj.get("state", State(repo_root))

    # Check mode
    if config.mode == "local":
        click.echo("")
        click.secho("Mode: local", fg="yellow")
        click.echo("")
        click.echo("GitHub sync is disabled in local mode.")
        click.echo("To enable GitHub sync:")
        click.echo("  1. Run: context-md config set mode github")
        click.echo("  2. Configure: context-md sync setup")
        click.echo("")

        # Show local issues
        _show_local_issues(state, verbose)
        return

    # GitHub mode
    if not state.github.enabled:
        raise click.ClickException(
            "GitHub sync not configured. Run: context-md sync setup"
        )

    if push and pull:
        raise click.ClickException("Cannot use --push and --pull together")

    if push:
        _sync_push(state, config, dry_run, verbose)
    elif pull:
        _sync_pull(state, config, dry_run, verbose)
    else:
        _sync_status(state, config, verbose)


@sync_cmd.command("setup")
@click.option("--owner", "-o", help="GitHub repository owner")
@click.option("--repo", "-r", help="GitHub repository name")
@click.option("--project", "-p", help="GitHub Project number (optional)")
@click.pass_context
def setup_cmd(ctx: click.Context, owner: Optional[str], repo: Optional[str],
              project: Optional[int]) -> None:
    """Configure GitHub sync settings.
    
    Detects repository information from Git remote if not provided.
    """
    repo_root = ctx.obj.get("repo_root")
    verbose = ctx.obj.get("verbose", False)

    if not repo_root:
        raise click.ClickException("Not in a Git repository.")

    state = State(repo_root)
    config = Config(repo_root)

    # Try to detect from git remote
    if not owner or not repo:
        detected = _detect_github_remote(repo_root)
        if detected:
            owner = owner or detected.get("owner")
            repo = repo or detected.get("repo")
            if verbose:
                click.echo(f"Detected GitHub remote: {owner}/{repo}")

    if not owner or not repo:
        raise click.ClickException(
            "Could not detect GitHub repository. Please provide --owner and --repo"
        )

    # Check GitHub CLI availability
    if not _check_gh_cli():
        click.echo("")
        click.secho("[!] GitHub CLI (gh) not found or not authenticated", fg="yellow")
        click.echo("")
        click.echo("To use GitHub sync, install and authenticate the GitHub CLI:")
        click.echo("  1. Install: https://cli.github.com/")
        click.echo("  2. Authenticate: gh auth login")
        click.echo("")
        click.echo("GitHub sync configuration saved but will require gh CLI to work.")
        click.echo("")

    # Update state
    state.github.enabled = True
    state.github.owner = owner
    state.github.repo = repo
    state.github.project_number = project
    state.save()

    # Update mode
    config.mode = "github"
    config.save()

    click.echo("")
    click.secho("[OK] GitHub sync configured!", fg="green")
    click.echo("")
    click.echo(f"  Owner: {owner}")
    click.echo(f"  Repo: {repo}")
    if project:
        click.echo(f"  Project: #{project}")
    click.echo("")
    click.echo("Next: Run 'context-md sync --pull' to sync issues from GitHub")


@sync_cmd.command("issues")
@click.option("--state", "issue_state", type=click.Choice(["open", "closed", "all"]),
              default="open", help="Filter by issue state")
@click.option("--label", "-l", multiple=True, help="Filter by label")
@click.pass_context
def issues_cmd(ctx: click.Context, issue_state: str, label: tuple) -> None:
    """List issues from GitHub."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    if not state.github.enabled:
        raise click.ClickException("GitHub sync not configured. Run: context-md sync setup")

    # Get token
    token = _get_auth_token(state)
    if not token:
        raise click.ClickException(
            "Not authenticated with GitHub. Run: context-md auth login"
        )

    # Build API request
    endpoint = f"/repos/{state.github.owner}/{state.github.repo}/issues"
    params = []
    if issue_state != "all":
        params.append(f"state={issue_state}")
    for lbl in label:
        params.append(f"labels={lbl}")

    if params:
        endpoint += "?" + "&".join(params)

    try:
        issues = _github_api_get(token, endpoint)
    except HTTPError as e:
        raise click.ClickException(f"Failed to fetch issues: {e}")

    if not issues:
        click.echo("No issues found.")
        return

    click.echo("")
    click.echo(f"Issues from {state.github.owner}/{state.github.repo}:")
    click.echo("")

    for issue in issues:
        labels = [label["name"] for label in issue.get("labels", [])]
        label_str = f" [{', '.join(labels)}]" if labels else ""
        state_icon = "[+]" if issue["state"] == "open" else "[-]"
        click.echo(f"  {state_icon} #{issue['number']}: {issue['title']}{label_str}")

    click.echo("")


def _detect_github_remote(repo_root: Path) -> Optional[Dict[str, str]]:
    """Detect GitHub owner/repo from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root, capture_output=True, text=True, check=True
        )
        url = result.stdout.strip()

        # Parse various GitHub URL formats
        import re

        # SSH: git@github.com:owner/repo.git
        match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
        if match:
            return {"owner": match.group(1), "repo": match.group(2)}

        # HTTPS: https://github.com/owner/repo.git
        match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
        if match:
            return {"owner": match.group(1), "repo": match.group(2)}

    except subprocess.CalledProcessError:
        pass

    return None


def _check_gh_cli() -> bool:
    """Check if GitHub CLI is available and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _show_local_issues(state: State, verbose: bool) -> None:
    """Show locally tracked issues."""
    local_issues = state.local_issues

    if not local_issues:
        click.echo("No local issues tracked.")
        click.echo("")
        click.echo("Create one with: context-md issue create <title>")
        return

    click.echo(f"Local Issues: {len(local_issues)}")
    click.echo("")

    for issue_id, issue in local_issues.items():
        status_icon = "[+]" if issue.get("state") == "open" else "[-]"
        labels = issue.get("labels", [])
        label_str = f" [{', '.join(labels)}]" if labels else ""
        click.echo(f"  {status_icon} #{issue_id}: {issue.get('title', 'Untitled')}{label_str}")

    click.echo("")


def _sync_status(state: State, config: Config, verbose: bool) -> None:
    """Show sync status between local and GitHub."""
    click.echo("")
    click.secho("GitHub Sync Status", fg="cyan", bold=True)
    click.echo("")
    click.echo(f"  Repository: {state.github.owner}/{state.github.repo}")
    if state.github.project_number:
        click.echo(f"  Project: #{state.github.project_number}")
    click.echo("")

    # Get local branch issues
    local_branches = state.get_issue_branches()
    click.echo(f"  Local issue branches: {len(local_branches)}")

    # Get active worktrees
    worktrees = state.worktrees
    click.echo(f"  Active SubAgents: {len(worktrees)}")

    click.echo("")
    click.echo("Run 'context-md sync --pull' to fetch latest from GitHub")
    click.echo("Run 'context-md sync --push' to push local changes")
    click.echo("")


def _sync_pull(state: State, config: Config, dry_run: bool, verbose: bool) -> None:
    """Pull issues and status from GitHub."""
    click.echo("")
    click.secho("Pulling from GitHub...", fg="cyan")
    click.echo("")

    # Get token
    token = _get_auth_token(state)
    if not token:
        raise click.ClickException(
            "Not authenticated with GitHub. Run: context-md auth login"
        )

    # Fetch open issues via API
    endpoint = f"/repos/{state.github.owner}/{state.github.repo}/issues?state=open"

    try:
        issues = _github_api_get(token, endpoint)
    except HTTPError as e:
        raise click.ClickException(f"Failed to fetch issues: {e}")

    click.echo(f"  Found {len(issues)} open issues")

    if dry_run:
        click.echo("")
        click.secho("  [DRY RUN] Would update local cache", fg="yellow")
        for issue in issues[:5]:
            click.echo(f"    - #{issue['number']}: {issue['title']}")
        if len(issues) > 5:
            click.echo(f"    ... and {len(issues) - 5} more")
        return

    # Cache issues in state
    github_config = state.github
    for issue in issues:
        labels = [label["name"] for label in issue.get("labels", [])]
        github_config.issue_cache[str(issue["number"])] = {
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "labels": labels,
            "body": issue.get("body", ""),
            "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    github_config.last_sync = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state.github = github_config
    state.save()

    click.echo("")
    click.secho("[OK] Sync complete!", fg="green")
    click.echo(f"  Cached {len(issues)} issues locally")
    click.echo("")


def _sync_push(state: State, config: Config, dry_run: bool, verbose: bool) -> None:
    """Push local changes to GitHub."""
    click.echo("")
    click.secho("Pushing to GitHub...", fg="cyan")
    click.echo("")

    # Find SubAgents that have changes to push
    worktrees = state.worktrees

    changes_to_push = []
    for wt in worktrees:
        metadata = state.get_branch_note(wt.branch) or {}
        if metadata.get("status") == "completed" and not metadata.get("pushed"):
            changes_to_push.append((wt, metadata))

    if not changes_to_push:
        click.echo("  No changes to push")
        click.echo("")
        return

    click.echo(f"  Found {len(changes_to_push)} completed SubAgents to push")

    for wt, metadata in changes_to_push:
        if dry_run:
            click.echo(f"  [DRY RUN] Would push branch: {wt.branch}")
            continue

        # Push the branch
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", wt.branch],
                cwd=state.repo_root, check=True, capture_output=True
            )
            click.echo(f"  [OK] Pushed: {wt.branch}")

            # Mark as pushed
            metadata["pushed"] = True
            metadata["pushed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            state.set_branch_note(wt.branch, metadata)

        except subprocess.CalledProcessError as e:
            click.secho(f"  [FAIL] Failed to push {wt.branch}: {e.stderr}", fg="red")

    click.echo("")
    click.secho("[OK] Push complete!", fg="green")
    click.echo("")


# Helper functions for GitHub API

def _get_auth_token(state: State) -> Optional[str]:
    """Get a valid GitHub token from OAuth or gh CLI fallback.
    
    Returns:
        Access token string or None if not authenticated
    """
    # Prefer stored OAuth token
    if state.github_token:
        return state.github_token

    # Fall back to gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def _github_api_get(token: str, endpoint: str) -> Any:
    """Make an authenticated GET request to GitHub API.
    
    Args:
        token: GitHub access token
        endpoint: API endpoint (e.g., "/repos/owner/repo/issues")
        
    Returns:
        Parsed JSON response
        
    Raises:
        HTTPError: If request fails
    """
    url = f"{GITHUB_API_URL}{endpoint}"

    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def _github_api_post(token: str, endpoint: str, data: Dict[str, Any]) -> Any:
    """Make an authenticated POST request to GitHub API.
    
    Args:
        token: GitHub access token
        endpoint: API endpoint
        data: JSON data to post
        
    Returns:
        Parsed JSON response
        
    Raises:
        HTTPError: If request fails
    """
    url = f"{GITHUB_API_URL}{endpoint}"

    request = Request(
        url,
        data=json.dumps(data).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        method="POST"
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())
