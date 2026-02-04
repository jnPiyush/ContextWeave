"""
Issue Command - Create and manage local issues

Usage:
    context-md issue create <title>
    context-md issue list
    context-md issue show <issue>
    context-md issue close <issue>
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional

import click

from context_md.state import State


# Input validation constants
MAX_TITLE_LENGTH = 200
MAX_BODY_LENGTH = 65535
MAX_LABEL_LENGTH = 50


def _sanitize_text(text: str, max_length: int, field_name: str) -> str:
    """Sanitize text input for safe storage.
    
    - Removes control characters (except newlines/tabs in body)
    - Trims whitespace
    - Enforces maximum length
    - Prevents potential injection attacks
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        field_name: Name of field for error messages
        
    Returns:
        Sanitized text
        
    Raises:
        click.BadParameter: If text is invalid after sanitization
    """
    if not text:
        return text
    
    # Remove null bytes and other dangerous control chars (keep \n, \t for body)
    if field_name == "body":
        # Allow newlines and tabs in body
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    else:
        # Remove all control characters for titles/labels
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', text)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Enforce length limit
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    
    # Check if anything remains
    if not sanitized:
        raise click.BadParameter(f"{field_name} cannot be empty or contain only whitespace")
    
    return sanitized


def _sanitize_label(label: str) -> str:
    """Sanitize a label for safe storage and Git branch naming.
    
    Labels should be alphanumeric with limited special chars.
    """
    # Remove dangerous characters, keep alphanumeric, dash, underscore, colon
    sanitized = re.sub(r'[^a-zA-Z0-9_:\-]', '', label)
    return sanitized[:MAX_LABEL_LENGTH] if sanitized else ""


@click.group("issue")
def issue_cmd() -> None:
    """Create and manage issues locally.
    
    In 'local' mode, issues are tracked in state.json.
    In 'github' mode, use 'context-md sync issues' to view GitHub issues.
    
    \b
    Examples:
        context-md issue create "Add user authentication"
        context-md issue list
        context-md issue show 1
        context-md issue close 1
    """


@issue_cmd.command("create")
@click.argument("title")
@click.option("--body", "-b", help="Issue description")
@click.option("--label", "-l", "labels", multiple=True,
              help="Labels (can be used multiple times)")
@click.option("--type", "issue_type",
              type=click.Choice(["epic", "feature", "story", "bug", "spike", "docs"]),
              default="story", help="Issue type")
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              help="Assign to role")
@click.pass_context
def create_cmd(ctx: click.Context, title: str, body: Optional[str],
               labels: tuple, issue_type: str, role: Optional[str]) -> None:
    """Create a new local issue.
    
    \b
    Examples:
        context-md issue create "Add login page"
        context-md issue create "Fix bug" --type bug --label priority:p0
        context-md issue create "Design auth flow" --type feature --role architect
    """
    repo_root = ctx.obj.get("repo_root")

    if not repo_root:
        raise click.ClickException("Not in a Context.md repository. Run 'context-md init' first.")

    state = ctx.obj.get("state", State(repo_root))

    # Sanitize inputs for security
    sanitized_title = _sanitize_text(title, MAX_TITLE_LENGTH, "title")
    sanitized_body = _sanitize_text(body, MAX_BODY_LENGTH, "body") if body else ""
    sanitized_labels = [_sanitize_label(lbl) for lbl in labels if _sanitize_label(lbl)]

    # Generate issue number
    existing_issues = state.local_issues
    if existing_issues:
        max_num = max(int(k) for k in existing_issues.keys())
        issue_number = max_num + 1
    else:
        issue_number = 1

    # Build labels list
    all_labels = list(sanitized_labels)
    type_label = f"type:{issue_type}"
    if type_label not in all_labels:
        all_labels.append(type_label)

    # Create issue
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    issue = {
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

    state.local_issues[str(issue_number)] = issue
    state.save()

    click.echo("")
    click.secho(f"[OK] Created issue #{issue_number}", fg="green")
    click.echo("")
    click.echo(f"  Title: {sanitized_title}")
    click.echo(f"  Type: {issue_type}")
    click.echo(f"  Labels: {', '.join(all_labels)}")
    if role:
        click.echo(f"  Assigned to: {role}")
    click.echo("")
    click.echo(f"Next: context-md subagent spawn {issue_number} --role {role or 'engineer'}")


@issue_cmd.command("list")
@click.option("--state", "issue_state", type=click.Choice(["open", "closed", "all"]),
              default="open", help="Filter by state")
@click.option("--type", "issue_type",
              type=click.Choice(["epic", "feature", "story", "bug", "spike", "docs"]),
              help="Filter by type")
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              help="Filter by assigned role")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_cmd(ctx: click.Context, issue_state: str, issue_type: Optional[str],
             role: Optional[str], as_json: bool) -> None:
    """List local issues."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    issues = list(state.local_issues.values())

    # Apply filters
    if issue_state != "all":
        issues = [i for i in issues if i.get("state") == issue_state]

    if issue_type:
        issues = [i for i in issues if i.get("type") == issue_type]

    if role:
        issues = [i for i in issues if i.get("role") == role]

    if as_json:
        click.echo(json.dumps(issues, indent=2))
        return

    if not issues:
        click.echo("No issues found.")
        click.echo("")
        click.echo("Create one with: context-md issue create <title>")
        return

    click.echo("")
    click.echo(f"Local Issues ({len(issues)}):")
    click.echo("")

    for issue in issues:
        state_icon = "[+]" if issue.get("state") == "open" else "[-]"
        labels = issue.get("labels", [])
        label_str = f" [{', '.join(labels)}]" if labels else ""
        role_str = f" @{issue['role']}" if issue.get("role") else ""
        click.echo(f"  {state_icon} #{issue['number']}: {issue['title']}{label_str}{role_str}")

    click.echo("")


@issue_cmd.command("show")
@click.argument("issue", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def show_cmd(ctx: click.Context, issue: int, as_json: bool) -> None:
    """Show details of a local issue."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    issue_data = state.local_issues.get(str(issue))

    if not issue_data:
        raise click.ClickException(f"Issue #{issue} not found")

    if as_json:
        click.echo(json.dumps(issue_data, indent=2))
        return

    click.echo("")
    click.echo(f"Issue #{issue_data['number']}: {issue_data['title']}")
    click.echo("-" * 50)
    click.echo(f"  State: {issue_data.get('state', 'unknown')}")
    click.echo(f"  Type: {issue_data.get('type', 'story')}")
    click.echo(f"  Labels: {', '.join(issue_data.get('labels', []))}")
    if issue_data.get("role"):
        click.echo(f"  Assigned to: {issue_data['role']}")
    click.echo(f"  Created: {issue_data.get('created_at', 'unknown')}")
    click.echo(f"  Updated: {issue_data.get('updated_at', 'unknown')}")

    if issue_data.get("body"):
        click.echo("")
        click.echo("Description:")
        click.echo(issue_data["body"])

    click.echo("")


@issue_cmd.command("close")
@click.argument("issue", type=int)
@click.option("--reason", "-r", help="Reason for closing")
@click.pass_context
def close_cmd(ctx: click.Context, issue: int, reason: Optional[str]) -> None:
    """Close a local issue."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    issue_data = state.local_issues.get(str(issue))

    if not issue_data:
        raise click.ClickException(f"Issue #{issue} not found")

    if issue_data.get("state") == "closed":
        click.echo(f"Issue #{issue} is already closed")
        return

    # Update issue
    issue_data["state"] = "closed"
    issue_data["closed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    issue_data["updated_at"] = issue_data["closed_at"]
    if reason:
        issue_data["close_reason"] = reason

    state.local_issues[str(issue)] = issue_data
    state.save()

    click.echo("")
    click.secho(f"[OK] Closed issue #{issue}", fg="green")
    if reason:
        click.echo(f"  Reason: {reason}")
    click.echo("")


@issue_cmd.command("reopen")
@click.argument("issue", type=int)
@click.pass_context
def reopen_cmd(ctx: click.Context, issue: int) -> None:
    """Reopen a closed local issue."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    issue_data = state.local_issues.get(str(issue))

    if not issue_data:
        raise click.ClickException(f"Issue #{issue} not found")

    if issue_data.get("state") == "open":
        click.echo(f"Issue #{issue} is already open")
        return

    # Update issue
    issue_data["state"] = "open"
    issue_data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if "closed_at" in issue_data:
        del issue_data["closed_at"]
    if "close_reason" in issue_data:
        del issue_data["close_reason"]

    state.local_issues[str(issue)] = issue_data
    state.save()

    click.echo("")
    click.secho(f"[OK] Reopened issue #{issue}", fg="green")
    click.echo("")


@issue_cmd.command("edit")
@click.argument("issue", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--body", "-b", help="New description")
@click.option("--add-label", "-l", "add_labels", multiple=True, help="Add labels")
@click.option("--remove-label", "remove_labels", multiple=True, help="Remove labels")
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              help="Assign to role")
@click.pass_context
def edit_cmd(ctx: click.Context, issue: int, title: Optional[str],
             body: Optional[str], add_labels: tuple, remove_labels: tuple,
             role: Optional[str]) -> None:
    """Edit a local issue."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    issue_data = state.local_issues.get(str(issue))

    if not issue_data:
        raise click.ClickException(f"Issue #{issue} not found")

    # Apply changes with sanitization
    if title:
        issue_data["title"] = _sanitize_text(title, MAX_TITLE_LENGTH, "title")

    if body:
        issue_data["body"] = _sanitize_text(body, MAX_BODY_LENGTH, "body")

    # Handle labels with sanitization
    labels = set(issue_data.get("labels", []))
    for lbl in add_labels:
        sanitized = _sanitize_label(lbl)
        if sanitized:
            labels.add(sanitized)
    for lbl in remove_labels:
        labels.discard(lbl)
        # Also try sanitized version
        labels.discard(_sanitize_label(lbl))
    issue_data["labels"] = list(labels)

    if role:
        issue_data["role"] = role

    issue_data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    state.local_issues[str(issue)] = issue_data
    state.save()

    click.echo("")
    click.secho(f"[OK] Updated issue #{issue}", fg="green")
    click.echo("")
