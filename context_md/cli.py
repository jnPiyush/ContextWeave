"""
Context.md CLI - Main entry point

Usage:
    context-md <command> [options]

Commands:
    init        Initialize Context.md in repository
    config      View/modify configuration
    issue       Create/manage local issues
    context     Generate context for an issue
    subagent    Manage SubAgent worktrees
    validate    Run validation checks
    status      Show current status
    dashboard   Display CLI dashboard
    metrics     Show/export metrics
    sync        Sync with GitHub (hybrid/github mode)
"""

import click
import sys
from pathlib import Path
from typing import Optional

from context_md import __version__
from context_md.state import State
from context_md.config import Config
from context_md.commands import init, config, subagent, context, validate, status


@click.group()
@click.version_option(version=__version__, prog_name="context-md")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Context.md - Runtime context management for AI agents.
    
    Achieve >95% success rate in production code generation through
    Git-native state management, worktree isolation, and automated
    quality gates.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    
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
cli.add_command(config.config_cmd, name="config")
cli.add_command(subagent.subagent_cmd, name="subagent")
cli.add_command(context.context_cmd, name="context")
cli.add_command(validate.validate_cmd, name="validate")
cli.add_command(status.status_cmd, name="status")


def main() -> None:
    """Main entry point."""
    try:
        cli(obj={})
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
