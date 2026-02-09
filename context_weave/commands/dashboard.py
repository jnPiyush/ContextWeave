"""
Dashboard Command - Real-time web dashboard

Usage:
    context-weave dashboard
    context-weave dashboard --port 8080
    context-weave dashboard --no-browser
"""

import asyncio
import logging

import click

from context_weave.state import State

logger = logging.getLogger(__name__)


@click.command("dashboard")
@click.option("--host", default="localhost", help="Server host (default: localhost)")
@click.option("--port", default=8765, help="Server port (default: 8765)")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
@click.pass_context
def dashboard_cmd(ctx: click.Context, host: str, port: int, no_browser: bool) -> None:
    """Start real-time web dashboard (experimental).

    Requires optional dependencies: pip install context-weave[dashboard]

    Opens a web-based dashboard showing:
    - Active agent status
    - Real-time updates via WebSocket
    - Progress tracking
    - Activity stream
    """
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository.")

    state = ctx.obj.get("state", State(repo_root))

    # Check if initialized
    if not state.is_initialized():
        click.echo("[ERROR] ContextWeave not initialized.")
        click.echo("Run: context-weave init")
        return

    # Print startup message
    click.echo("[SUCCESS] Starting dashboard server...")
    click.echo(f"  Host: {host}")
    click.echo(f"  Port: {port}")
    click.echo(f"  URL: http://{host}:{port}")
    click.echo("")

    if not no_browser:
        click.echo("[SUCCESS] Opening browser...")

    click.echo("[INFO] Press Ctrl+C to stop")
    click.echo("")

    # Start async server
    from context_weave.dashboard import start_dashboard

    try:
        asyncio.run(start_dashboard(
            repo_root=repo_root,
            host=host,
            port=port,
            open_browser=not no_browser
        ))
    except KeyboardInterrupt:
        click.echo("")
        click.echo("[SUCCESS] Dashboard stopped")
    except Exception as e:
        raise click.ClickException(f"Dashboard failed: {e}") from e
