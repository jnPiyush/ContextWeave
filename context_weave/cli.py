"""
ContextWeave CLI - Main entry point

Implements the 4-Layer AI Context Architecture:
1. System Context - Role instructions (governs AI behavior)
2. User Prompt - Issue details (what user asks)
3. Memory - Lessons learned, session history (persistent info)
4. Retrieval Context - Skills/docs (knowledge grounding)

Usage:
    context-weave <command> [options]

Commands:
    init        Initialize ContextWeave in repository
    config      View/modify configuration
    issue       Create/manage local issues
    context     Generate context for an issue
    memory      Manage AI agent memory (Layer 3)
    subagent    Manage SubAgent worktrees
    validate    Run validation checks
    status      Show current status
    dashboard   Display CLI dashboard
    metrics     Show/export metrics
    sync        Sync with GitHub (hybrid/github mode)
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from context_weave import __version__
from context_weave.commands import (
    auth,
    config,
    context,
    dashboard,
    doctor,
    export,
    init,
    issue,
    memory,
    start,
    status,
    subagent,
    sync,
    validate,
)
from context_weave.config import Config
from context_weave.state import State


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Setup logging configuration."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Log to file in user's home directory
    log_dir = Path.home() / ".context-weave" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "context-weave.log"

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler() if verbose else logging.NullHandler()
        ]
    )

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('keyring').setLevel(logging.WARNING)


@click.group()
@click.version_option(version=__version__, prog_name="context-weave")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """ContextWeave - Runtime context management for AI agents.

    Achieve >95% success rate in production code generation through
    Git-native state management, worktree isolation, and automated
    quality gates.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Setup logging
    setup_logging(verbose, quiet)

    # Find repository root
    repo_root = find_repo_root()
    if repo_root:
        ctx.obj["repo_root"] = repo_root
        ctx.obj["state"] = State(repo_root)
        ctx.obj["config"] = Config(repo_root)


def find_repo_root() -> Optional[Path]:
    """Find the Git repository root from current directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


# Register commands
cli.add_command(init.init_cmd, name="init")
cli.add_command(auth.auth_cmd, name="auth")
cli.add_command(config.config_cmd, name="config")
cli.add_command(issue.issue_cmd, name="issue")
cli.add_command(subagent.subagent_cmd, name="subagent")
cli.add_command(context.context_cmd, name="context")
cli.add_command(export.export_cmd, name="export")
cli.add_command(memory.memory_cmd, name="memory")  # Layer 3: Memory
cli.add_command(validate.validate_cmd, name="validate")
cli.add_command(status.status_cmd, name="status")
cli.add_command(dashboard.dashboard_cmd, name="dashboard")  # Real-time web dashboard
cli.add_command(sync.sync_cmd, name="sync")
cli.add_command(start.start_cmd, name="start")  # Quick-start workflow
cli.add_command(doctor.doctor_cmd, name="doctor")  # Diagnostics

# Conditionally register agent framework command
try:
    from context_weave.framework import AGENT_FRAMEWORK_AVAILABLE
    if AGENT_FRAMEWORK_AVAILABLE:
        from context_weave.framework.run import run_cmd
        cli.add_command(run_cmd, name="run")
except ImportError:
    pass  # Agent framework not installed, skip


# Input validation helpers
def validate_issue_number(_ctx, _param, value):
    """Validate issue number is positive and reasonable.

    Click callback signature requires ctx and param parameters
    even if not used.
    """
    if value is not None:
        if value <= 0:
            raise click.BadParameter("Issue number must be positive")
        if value > 999999:
            raise click.BadParameter("Issue number too large (max: 999999)")
    return value


def validate_branch_name(name: str) -> str:
    """Validate branch name doesn't contain invalid characters."""
    import re
    if not name:
        raise click.BadParameter("Branch name cannot be empty")

    # Git branch name rules
    invalid_patterns = [
        r'^\.', r'\.\.', r'\.$', r'^/', r'/$', r'//', r'@{', r'\\',
        r'[\x00-\x1f\x7f]', r'[ ~^:?*\[]', r'^\.lock$', r'\.lock/'
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, name):
            raise click.BadParameter(
                f"Invalid branch name '{name}': contains invalid characters"
            )

    return name


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except click.ClickException:
        # Click handles these gracefully
        raise
    except KeyboardInterrupt:
        click.echo("\n\nOperation cancelled by user.", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except (OSError, IOError) as e:
        # File system errors
        logging.getLogger(__name__).error("File system error: %s", e)
        click.secho(f"File system error: {e}", fg="red", err=True)
        sys.exit(1)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # Git command failures
        logging.getLogger(__name__).error("Git command failed: %s", e)
        click.secho(f"Git command failed: {e}", fg="red", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        # Configuration parsing errors
        logging.getLogger(__name__).error("Invalid JSON in config: %s", e)
        click.secho(f"Configuration error: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 - Intentional catch-all for CLI robustness
        # Unexpected errors - log full traceback for debugging
        logging.getLogger(__name__).exception("Unexpected error")
        click.secho(f"Unexpected error: {e}", fg="red", err=True)
        click.echo("Please report this issue with the log file.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
