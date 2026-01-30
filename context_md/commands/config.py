"""
Config Command - View and modify Context.md configuration

Usage:
    context-md config [key] [value]
    context-md config mode [local|github|hybrid]
    context-md config --list
"""

import json
from typing import Optional

import click

from context_md.config import Config


@click.command("config")
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--list", "-l", "list_all", is_flag=True, help="List all configuration")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def config_cmd(ctx: click.Context, key: Optional[str], value: Optional[str],
               list_all: bool, as_json: bool) -> None:
    """View or modify Context.md configuration.
    
    Examples:
        context-md config                    # Show current mode
        context-md config --list             # List all config
        context-md config mode               # Get mode value
        context-md config mode github        # Set mode to github
        context-md config hooks.pre_push     # Get specific setting
        context-md config hooks.pre_push false  # Disable pre-push hook
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with Context.md initialized.")

    config = ctx.obj.get("config")
    if not config:
        config = Config(repo_root)

    # List all configuration
    if list_all:
        if as_json:
            click.echo(json.dumps(config.to_dict(), indent=2))
        else:
            _print_config(config.to_dict())
        return

    # No key provided - show mode
    if not key:
        click.echo(f"Mode: {config.mode}")
        click.echo("")
        click.echo("Use 'context-md config --list' to see all settings")
        click.echo("Use 'context-md config <key> <value>' to change a setting")
        return

    # Handle mode specially
    if key == "mode":
        if value:
            # Set mode
            try:
                config.mode = value
                config.save()
                click.secho(f"[OK] Mode set to: {value}", fg="green")
            except ValueError as e:
                raise click.ClickException(str(e))
        else:
            # Get mode
            if as_json:
                click.echo(json.dumps({"mode": config.mode}))
            else:
                click.echo(f"Mode: {config.mode}")
        return

    # Get or set arbitrary key
    if value:
        # Set value (attempt type conversion)
        converted_value = _convert_value(value)
        config.set(key, converted_value)
        config.save()
        click.secho(f"[OK] Set {key} = {converted_value}", fg="green")
    else:
        # Get value
        result = config.get(key)
        if result is None:
            raise click.ClickException(f"Configuration key not found: {key}")
        if as_json:
            click.echo(json.dumps({key: result}))
        else:
            if isinstance(result, dict):
                _print_config(result, prefix=key)
            else:
                click.echo(f"{key}: {result}")


def _convert_value(value: str):
    """Convert string value to appropriate type."""
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # List (comma-separated)
    if "," in value:
        return [v.strip() for v in value.split(",")]

    # String
    return value


def _print_config(data: dict, prefix: str = "", indent: int = 0) -> None:
    """Pretty print configuration."""
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            click.echo("  " * indent + f"{key}:")
            _print_config(value, full_key, indent + 1)
        else:
            click.echo("  " * indent + f"{key}: {value}")
