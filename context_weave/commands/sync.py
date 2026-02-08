"""
Sync Command - Synchronize with GitHub

Usage:
    context-weave sync
    context-weave sync --push
    context-weave sync --pull
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import click

from context_weave.config import Config
from context_weave.state import State

GITHUB_API_URL = "https://api.github.com"

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # seconds, doubled each retry


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
        context-weave sync           # Show sync status
        context-weave sync --push    # Push local changes to GitHub
        context-weave sync --pull    # Pull updates from GitHub
    """
    repo_root = ctx.obj.get("repo_root")
    verbose = ctx.obj.get("verbose", False)

    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    config = ctx.obj.get("config", Config(repo_root))
    state = ctx.obj.get("state", State(repo_root))

    # Check mode
    if config.mode == "local":
        click.echo("")
        click.secho("Mode: local", fg="yellow")
        click.echo("")
        click.echo("GitHub sync is disabled in local mode.")
        click.echo("To enable GitHub sync:")
        click.echo("  1. Run: context-weave config set mode github")
        click.echo("  2. Configure: context-weave sync setup")
        click.echo("")

        # Show local issues
        _show_local_issues(state, verbose)
        return

    # GitHub mode
    if not state.github.enabled:
        raise click.ClickException(
            "GitHub sync not configured. Run: context-weave sync setup"
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
    click.echo("Next: Run 'context-weave sync --pull' to sync issues from GitHub")


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
        raise click.ClickException("GitHub sync not configured. Run: context-weave sync setup")

    # Get token
    token = _get_auth_token(state)
    if not token:
        raise click.ClickException(
            "Not authenticated with GitHub. Run: context-weave auth login"
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
        raise click.ClickException(f"Failed to fetch issues: {e}") from e

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
        click.echo("Create one with: context-weave issue create <title>")
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
    click.echo("Run 'context-weave sync --pull' to fetch latest from GitHub")
    click.echo("Run 'context-weave sync --push' to push local changes")
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
            "Not authenticated with GitHub. Run: context-weave auth login"
        )

    # Fetch open issues via API
    endpoint = f"/repos/{state.github.owner}/{state.github.repo}/issues?state=open"

    try:
        issues = _github_api_get(token, endpoint)
    except HTTPError as e:
        raise click.ClickException(f"Failed to fetch issues: {e}") from e

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


def _github_request_with_retry(request: Request, timeout: int = 30) -> Dict[str, Any]:
    """Execute an HTTP request with retry logic for transient failures.

    Retries on 5xx errors and network errors with exponential backoff.
    Returns a dict with 'data' (parsed JSON) and 'headers' (captured before
    the connection closes).
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode())
                # Capture headers before context manager closes
                headers = dict(response.headers.items())
                return {"data": body, "headers": headers}
        except HTTPError as e:
            if e.code >= 500:
                last_error = e
                wait = RETRY_BACKOFF * (2 ** attempt)
                logger.warning("GitHub API %s error, retrying in %.1fs...", e.code, wait)
                time.sleep(wait)
                continue
            raise
        except (URLError, OSError) as e:
            last_error = e
            wait = RETRY_BACKOFF * (2 ** attempt)
            logger.warning("Network error: %s, retrying in %.1fs...", e, wait)
            time.sleep(wait)
            continue

    raise last_error  # type: ignore[misc]


def _github_api_get(token: str, endpoint: str) -> Any:
    """Make an authenticated GET request to GitHub API with pagination.

    Automatically follows Link headers to fetch all pages.
    """
    all_results: List[Any] = []
    url = f"{GITHUB_API_URL}{endpoint}"

    while url:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        result = _github_request_with_retry(request)
        data = result["data"]

        if isinstance(data, list):
            all_results.extend(data)
        else:
            return data  # Single object, no pagination needed

        # Check for next page via Link header
        link_header = result["headers"].get("Link", "")
        url = _parse_next_link(link_header)

    return all_results


def _parse_next_link(link_header: str) -> Optional[str]:
    """Parse the 'next' URL from a GitHub Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            url = part.split(";")[0].strip().strip("<>")
            return url
    return None


def _github_api_post(token: str, endpoint: str, data: Dict[str, Any]) -> Any:
    """Make an authenticated POST request to GitHub API with retries."""
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

    return _github_request_with_retry(request)["data"]


def _github_graphql(token: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Any:
    """Execute a GraphQL query against GitHub API with retries.

    Args:
        token: GitHub access token
        query: GraphQL query string
        variables: Optional query variables

    Returns:
        Parsed GraphQL response data

    Raises:
        HTTPError: If request fails after retries
        ValueError: If GraphQL returns errors
    """
    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    request = Request(
        f"{GITHUB_API_URL}/graphql",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    result = _github_request_with_retry(request)["data"]

    if "errors" in result:
        error_messages = [err.get("message", str(err)) for err in result["errors"]]
        raise ValueError(f"GraphQL errors: {'; '.join(error_messages)}")

    return result.get("data")


def get_project_field_ids(token: str, owner: str, repo: str, project_number: int) -> Dict[str, str]:
    """Get field IDs for a GitHub Projects V2 project.

    Retrieves the internal field IDs needed to update project fields like Status.

    Args:
        token: GitHub access token
        owner: Repository owner
        repo: Repository name
        project_number: Project number (not database ID)

    Returns:
        Dict mapping field names to their IDs

    Raises:
        ValueError: If project or fields not found
    """
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        projectV2(number: $number) {
          id
          title
          fields(first: 20) {
            nodes {
              ... on ProjectV2Field {
                id
                name
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "owner": owner,
        "repo": repo,
        "number": project_number
    }

    data = _github_graphql(token, query, variables)

    if not data or not data.get("repository") or not data["repository"].get("projectV2"):
        raise ValueError(f"Project #{project_number} not found in {owner}/{repo}")

    project = data["repository"]["projectV2"]
    fields = {}

    for field in project["fields"]["nodes"]:
        field_name = field["name"]
        field_id = field["id"]
        fields[field_name] = {"id": field_id}

        # If single select field, store option mappings
        if "options" in field:
            fields[field_name]["options"] = {
                opt["name"]: opt["id"] for opt in field["options"]
            }

    return fields


def update_project_status(
    token: str,
    owner: str,
    repo: str,
    project_number: int,
    issue_number: int,
    status: str
) -> bool:
    """Update an issue's status in GitHub Projects V2.

    Args:
        token: GitHub access token
        owner: Repository owner
        repo: Repository name
        project_number: Project number
        issue_number: Issue number
        status: New status (Backlog|In Progress|In Review|Ready|Done)

    Returns:
        True if update succeeded

    Raises:
        ValueError: If project, issue, or status invalid
    """
    # Step 1: Get project and field information
    try:
        fields = get_project_field_ids(token, owner, repo, project_number)
    except ValueError as e:
        raise ValueError(f"Failed to get project fields: {e}") from e

    if "Status" not in fields:
        raise ValueError("Status field not found in project")

    status_field = fields["Status"]
    if status not in status_field.get("options", {}):
        available = ", ".join(status_field.get("options", {}).keys())
        raise ValueError(f"Invalid status '{status}'. Available: {available}")

    status_option_id = status_field["options"][status]

    # Step 2: Get issue node ID
    issue_query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $number) {
          id
          projectItems(first: 10) {
            nodes {
              id
              project {
                number
              }
            }
          }
        }
      }
    }
    """

    issue_data = _github_graphql(token, issue_query, {
        "owner": owner,
        "repo": repo,
        "number": issue_number
    })

    if not issue_data or not issue_data.get("repository") or not issue_data["repository"].get("issue"):
        raise ValueError(f"Issue #{issue_number} not found")

    issue = issue_data["repository"]["issue"]

    # Find project item ID for this project
    project_item_id = None
    for item in issue["projectItems"]["nodes"]:
        if item["project"]["number"] == project_number:
            project_item_id = item["id"]
            break

    if not project_item_id:
        raise ValueError(f"Issue #{issue_number} not found in project #{project_number}")

    # Step 3: Update the status field
    update_mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: {
            singleSelectOptionId: $value
          }
        }
      ) {
        projectV2Item {
          id
        }
      }
    }
    """

    # Get project ID
    projectQuery = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        projectV2(number: $number) {
          id
        }
      }
    }
    """

    project_data = _github_graphql(token, projectQuery, {
        "owner": owner,
        "repo": repo,
        "number": project_number
    })

    project_id = project_data["repository"]["projectV2"]["id"]

    # Execute update
    _github_graphql(token, update_mutation, {
        "projectId": project_id,
        "itemId": project_item_id,
        "fieldId": status_field["id"],
        "value": status_option_id
    })

    return True


@sync_cmd.command("status-update")
@click.argument("issue_number", type=int)
@click.argument("status", type=click.Choice([
    "Backlog", "In Progress", "In Review", "Ready", "Done"
]))
@click.pass_context
def status_update_cmd(ctx: click.Context, issue_number: int, status: str) -> None:
    """Update issue status in GitHub Projects V2.

    Updates the Status field for an issue in the configured GitHub Project.
    This is the primary way to coordinate agent handoffs.

    \b
    Status Values:
        Backlog      - Issue created, not started
        In Progress  - Active work by current agent
        In Review    - Code review phase
        Ready        - Design/spec done, awaiting next phase
        Done         - Completed and closed

    \b
    Examples:
        context-weave sync status-update 42 "Ready"
        context-weave sync status-update 42 "In Progress"
    """
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    if not state.github.enabled:
        raise click.ClickException("GitHub sync not configured. Run: context-weave sync setup")

    if not state.github.project_number:
        raise click.ClickException(
            "No project configured. Run: context-weave sync setup --project <number>"
        )

    # Get token
    token = _get_auth_token(state)
    if not token:
        raise click.ClickException(
            "Not authenticated with GitHub. Run: context-weave auth login"
        )

    click.echo("")
    click.echo(f"Updating issue #{issue_number} status to '{status}'...")

    try:
        update_project_status(
            token=token,
            owner=state.github.owner,
            repo=state.github.repo,
            project_number=state.github.project_number,
            issue_number=issue_number,
            status=status
        )

        click.echo("")
        click.secho("[OK] Status updated successfully!", fg="green")
        click.echo(f"  Issue: #{issue_number}")
        click.echo(f"  Status: {status}")
        click.echo(f"  Project: #{state.github.project_number}")
        click.echo("")

    except ValueError as e:
        raise click.ClickException(f"Failed to update status: {e}") from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e
