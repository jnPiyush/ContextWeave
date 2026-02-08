"""
Auth Command - GitHub OAuth authentication

Usage:
    context-weave auth login
    context-weave auth logout
    context-weave auth status

Uses GitHub's Device Flow for CLI-friendly authentication without
requiring users to manually create Personal Access Tokens.
"""

import json
import logging
import os
import time
import webbrowser
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import click

from context_weave.state import State

logger = logging.getLogger(__name__)

# GitHub OAuth App configuration
# For production, register your own OAuth App at:
# https://github.com/settings/applications/new
# Client ID is public per RFC 8252 for native apps, but configurable for enterprise
GITHUB_CLIENT_ID = os.getenv(
    "CONTEXT_WEAVE_GITHUB_CLIENT_ID",
    "Ov23liUwXgKjNxHiXmpt"  # Default public client for OSS
)
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"  # Used by helper functions below

# Scopes needed for ContextWeave operations
GITHUB_SCOPES = "repo read:org read:user"


@click.group("auth")
@click.pass_context
def auth_cmd(ctx: click.Context) -> None:
    """Authenticate with GitHub using OAuth.

    Uses GitHub's Device Flow for secure CLI authentication.
    No need to manually create Personal Access Tokens.

    \b
    Examples:
        context-weave auth login     # Start OAuth login
        context-weave auth status    # Check authentication status
        context-weave auth logout    # Clear stored credentials
    """
    pass


@auth_cmd.command("login")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
@click.pass_context
def login_cmd(ctx: click.Context, no_browser: bool) -> None:
    """Authenticate with GitHub using Device Flow.

    Opens your browser to complete authentication. The CLI will
    automatically receive the token once you authorize.
    """
    repo_root = ctx.obj.get("repo_root")

    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = State(repo_root)

    # Check if already authenticated
    if state.github_token:
        user = _get_current_user(state.github_token)
        if user:
            click.echo("")
            click.echo(f"Already authenticated as @{user['login']}")
            click.echo("")
            click.echo("To switch accounts, run: context-weave auth logout")
            return

    click.echo("")
    click.secho("GitHub Authentication", fg="cyan", bold=True)
    click.echo("")

    # Step 1: Request device code
    try:
        device_data = _request_device_code()
    except Exception as e:
        raise click.ClickException(f"Failed to start authentication: {e}") from e

    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    device_code = device_data["device_code"]
    expires_in = device_data.get("expires_in", 900)
    interval = device_data.get("interval", 5)

    # Step 2: Show user code and open browser
    click.echo("  1. Copy this code:")
    click.echo("")
    click.secho(f"     {user_code}", fg="green", bold=True)
    click.echo("")
    click.echo(f"  2. Visit: {verification_uri}")
    click.echo("  3. Paste the code and authorize ContextWeave")
    click.echo("")

    if not no_browser:
        try:
            webbrowser.open(verification_uri)
            click.echo("  [Browser opened automatically]")
        except Exception:
            click.echo("  [Could not open browser - please visit the URL manually]")

    click.echo("")
    click.echo("Waiting for authorization...", nl=False)

    # Step 3: Poll for token with rate limiting
    start_time = time.monotonic()
    token = None
    max_interval = 60  # Cap at 60 seconds
    attempts = 0
    max_attempts = 200  # Absolute limit

    while time.monotonic() - start_time < expires_in:
        if attempts >= max_attempts:
            click.echo("")
            raise click.ClickException("Maximum polling attempts exceeded.")

        time.sleep(interval)
        click.echo(".", nl=False)
        attempts += 1

        try:
            result = _poll_for_token(device_code)

            if "access_token" in result:
                token = result["access_token"]
                logger.info("OAuth token received successfully")
                break
            elif result.get("error") == "authorization_pending":
                continue
            elif result.get("error") == "slow_down":
                # Exponential backoff
                interval = min(result.get("interval", interval * 1.5), max_interval)
                logger.debug(f"Slowing down polling interval to {interval}s")
                continue
            elif result.get("error") == "expired_token":
                click.echo("")
                logger.warning("OAuth device code expired")
                raise click.ClickException("Authorization expired. Please try again.")
            elif result.get("error") == "access_denied":
                click.echo("")
                logger.info("User denied authorization")
                raise click.ClickException("Authorization denied by user.")
            else:
                logger.warning(f"Unexpected OAuth response: {result}")
                continue

        except HTTPError as e:
            if e.code == 428:  # Precondition Required (still waiting)
                continue
            elif e.code == 429:  # Rate limited
                interval = min(interval * 2, max_interval)
                logger.warning(f"Rate limited, backing off to {interval}s")
                continue
            logger.error(f"HTTP error during OAuth polling: {e}")
            raise

    click.echo("")

    if not token:
        raise click.ClickException("Authorization timed out. Please try again.")

    # Step 4: Verify token and get user info
    user = _get_current_user(token)
    if not user:
        raise click.ClickException("Failed to verify token. Please try again.")

    # Step 5: Store token
    state.github_token = token
    state.github_token_created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state.save()

    click.echo("")
    click.secho("[OK] Authentication successful!", fg="green")
    click.echo("")
    click.echo(f"  Logged in as: @{user['login']}")
    if user.get("name"):
        click.echo(f"  Name: {user['name']}")
    click.echo("")
    click.echo("You can now use GitHub features:")
    click.echo("  - context-weave sync --pull    # Sync issues from GitHub")
    click.echo("  - context-weave sync --push    # Push branches to GitHub")
    click.echo("")


@auth_cmd.command("logout")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def logout_cmd(ctx: click.Context, force: bool) -> None:
    """Clear stored GitHub credentials."""
    repo_root = ctx.obj.get("repo_root")

    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = State(repo_root)

    if not state.github_token:
        click.echo("Not currently authenticated with GitHub.")
        return

    # Get current user for confirmation
    user = _get_current_user(state.github_token)
    username = user["login"] if user else "unknown"

    if not force:
        click.confirm(f"Logout from GitHub account @{username}?", abort=True)

    # Clear token
    state.github_token = None
    state.github_token_created = None
    state.save()

    click.echo("")
    click.secho("[OK] Logged out successfully", fg="green")
    click.echo("")


@auth_cmd.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def status_cmd(ctx: click.Context, as_json: bool) -> None:
    """Check GitHub authentication status."""
    repo_root = ctx.obj.get("repo_root")

    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    state = State(repo_root)

    status_data = {
        "authenticated": False,
        "method": None,
        "user": None,
        "scopes": None,
        "token_created": None
    }

    # Check for OAuth token
    if state.github_token:
        user = _get_current_user(state.github_token)
        scopes = _get_token_scopes(state.github_token)

        if user:
            status_data.update({
                "authenticated": True,
                "method": "oauth",
                "user": {
                    "login": user["login"],
                    "name": user.get("name"),
                    "email": user.get("email")
                },
                "scopes": scopes,
                "token_created": state.github_token_created
            })

    # Check for gh CLI as fallback
    if not status_data["authenticated"]:
        gh_user = _check_gh_cli_auth()
        if gh_user:
            status_data.update({
                "authenticated": True,
                "method": "gh-cli",
                "user": {"login": gh_user}
            })

    if as_json:
        click.echo(json.dumps(status_data, indent=2))
        return

    click.echo("")
    if status_data["authenticated"]:
        user = status_data["user"]
        method = "OAuth" if status_data["method"] == "oauth" else "GitHub CLI"

        click.secho("[OK] Authenticated with GitHub", fg="green")
        click.echo("")
        click.echo(f"  Method: {method}")
        click.echo(f"  User: @{user['login']}")
        if user.get("name"):
            click.echo(f"  Name: {user['name']}")
        if status_data.get("scopes"):
            click.echo(f"  Scopes: {', '.join(status_data['scopes'])}")
        if status_data.get("token_created"):
            click.echo(f"  Since: {status_data['token_created']}")
    else:
        click.secho("[!] Not authenticated with GitHub", fg="yellow")
        click.echo("")
        click.echo("  Run: context-weave auth login")

    click.echo("")


@auth_cmd.command("token")
@click.option("--show", is_flag=True, help="Show the actual token (use with caution)")
@click.pass_context
def token_cmd(ctx: click.Context, show: bool) -> None:
    """Display token information (for debugging)."""
    repo_root = ctx.obj.get("repo_root")

    if not repo_root:
        raise click.ClickException("Not in a Git repository.")

    state = State(repo_root)

    if not state.github_token:
        click.echo("No OAuth token stored.")
        click.echo("Run: context-weave auth login")
        return

    click.echo("")
    click.echo("OAuth Token Information:")
    click.echo("")

    if show:
        # Security: Mask most of token, showing only minimal identification chars
        # GitHub tokens start with prefixes like gho_, ghp_, etc.
        token = state.github_token
        if len(token) > 12:
            # Show prefix (4 chars) + masked middle + last 4 chars
            masked = token[:4] + "*" * min(len(token) - 8, 20) + token[-4:]
        else:
            # Very short token - show even less
            masked = token[:2] + "*" * (len(token) - 2)
        click.secho("  WARNING: SENSITIVE - Do not share this output", fg="yellow")
        click.echo(f"  Token: {masked}")
    else:
        click.echo("  Token: [hidden - use --show to reveal]")

    click.echo(f"  Created: {state.github_token_created or 'unknown'}")

    # Verify token
    scopes = _get_token_scopes(state.github_token)
    if scopes is not None:
        click.secho("  Status: Valid", fg="green")
        click.echo(f"  Scopes: {', '.join(scopes) if scopes else 'none'}")
    else:
        click.secho("  Status: Invalid or expired", fg="red")

    click.echo("")


# Helper functions

def _request_device_code() -> Dict[str, Any]:
    """Request a device code from GitHub."""
    data = urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "scope": GITHUB_SCOPES
    }).encode()

    request = Request(
        GITHUB_DEVICE_CODE_URL,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def _poll_for_token(device_code: str) -> Dict[str, Any]:
    """Poll GitHub for the access token."""
    data = urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }).encode()

    request = Request(
        GITHUB_TOKEN_URL,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def _get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """Get the authenticated user's information."""
    try:
        request = Request(
            f"{GITHUB_API_URL}/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError):
        return None


def _get_token_scopes(token: str) -> Optional[list]:
    """Get the scopes associated with a token."""
    try:
        request = Request(
            f"{GITHUB_API_URL}/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        with urlopen(request, timeout=30) as response:
            scopes_header = response.headers.get("X-OAuth-Scopes", "")
            return [s.strip() for s in scopes_header.split(",") if s.strip()]
    except (HTTPError, URLError):
        return None


def _check_gh_cli_auth() -> Optional[str]:
    """Check if gh CLI is authenticated."""
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def get_github_token(state: State) -> Optional[str]:
    """Get a valid GitHub token from OAuth or gh CLI.

    This is the main function other commands should use to get
    an authenticated token for GitHub API calls.

    Returns:
        Access token string or None if not authenticated
    """
    # Prefer OAuth token
    if state.github_token:
        # Verify it's still valid
        if _get_current_user(state.github_token):
            return state.github_token

    # Fall back to gh CLI
    import subprocess
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


def github_api_request(
    token: str,
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make an authenticated GitHub API request.

    Args:
        token: GitHub access token
        endpoint: API endpoint (e.g., "/repos/owner/repo/issues")
        method: HTTP method
        data: JSON data for POST/PATCH requests

    Returns:
        JSON response as dictionary

    Raises:
        HTTPError: If request fails
    """
    url = f"{GITHUB_API_URL}{endpoint}"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    body = None
    if data:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())
