"""
Memory Command - Manage AI agent memory and learning

Usage:
    context-weave memory show                    # Show memory summary
    context-weave memory lessons                 # List lessons learned
    context-weave memory lessons add             # Add a lesson
    context-weave memory record <issue>          # Record execution outcome
    context-weave memory metrics                 # Show success metrics
    context-weave memory session <issue>         # Save/show session context
"""

import json
import uuid
from typing import Optional

import click

from context_weave.memory import (
    ExecutionRecord,
    LessonLearned,
    Memory,
    SessionContext,
)


@click.group("memory")
def memory_cmd() -> None:
    """Manage AI agent memory and learning.

    The Memory layer enables agents to:
    - Learn from past executions
    - Track success/failure patterns
    - Maintain session continuity
    - Improve over time

    This is Layer 3 of the 4-Layer AI Context Architecture.
    """
    pass


@memory_cmd.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def show_cmd(ctx: click.Context, as_json: bool) -> None:
    """Show memory summary."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    if as_json:
        click.echo(json.dumps(memory.to_dict(), indent=2))
        return

    metrics = memory.metrics

    click.echo("")
    click.secho("=" * 59, fg="cyan")
    click.secho("  AI AGENT MEMORY SUMMARY", fg="cyan")
    click.secho("=" * 59, fg="cyan")
    click.echo("")

    # Overall metrics
    total = metrics.get("total_executions", 0)
    success = metrics.get("success_count", 0)
    failure = metrics.get("failure_count", 0)
    partial = metrics.get("partial_count", 0)

    click.echo("Execution Metrics:")
    click.echo(f"   Total Executions: {total}")
    if total > 0:
        click.echo(f"   Success Rate: {success/total:.1%} ({success} success, {failure} failure, {partial} partial)")
    click.echo("")

    # By role
    by_role = metrics.get("by_role", {})
    if by_role:
        click.echo("By Role:")
        for role, stats in by_role.items():
            role_total = stats.get("total", 0)
            role_success = stats.get("success", 0)
            rate = role_success / role_total if role_total > 0 else 0
            click.echo(f"   {role.title()}: {rate:.1%} ({role_total} executions)")
        click.echo("")

    # Lessons count
    lessons = memory._data.get("lessons", [])
    click.echo(f"Lessons Learned: {len(lessons)}")

    # Sessions count
    sessions = memory._data.get("sessions", {})
    total_sessions = sum(len(s) for s in sessions.values())
    click.echo(f"Session Records: {total_sessions} across {len(sessions)} issues")
    click.echo("")


@memory_cmd.group("lessons")
def lessons_group() -> None:
    """Manage lessons learned."""
    pass


@lessons_group.command("list")
@click.option("--role", type=str, help="Filter by role")
@click.option("--category", type=str, help="Filter by category")
@click.option("--limit", type=int, default=10, help="Number of lessons to show")
@click.pass_context
def lessons_list_cmd(ctx: click.Context, role: Optional[str], category: Optional[str], limit: int) -> None:
    """List lessons learned."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)
    categories = [category] if category else None
    lessons = memory.get_lessons_for_context(role=role, categories=categories, limit=limit)

    if not lessons:
        click.echo("No lessons learned yet. Use 'context-weave memory lessons add' to add one.")
        return

    click.echo("")
    click.secho("Lessons Learned", fg="cyan", bold=True)
    click.echo("")

    for i, lesson in enumerate(lessons, 1):
        effectiveness = "[HIGH]" if lesson.effectiveness >= 0.7 else "[MED]" if lesson.effectiveness >= 0.4 else "[LOW]"
        click.echo(f"{i}. [{lesson.category}] {lesson.lesson}")
        click.echo(f"   {effectiveness} Effectiveness: {lesson.effectiveness:.0%} | Applied: {lesson.applied_count}x")
        click.echo(f"   Role: {lesson.role} | Issue Type: {lesson.issue_type}")
        click.echo("")


@lessons_group.command("add")
@click.option("--issue", type=int, required=True, help="Related issue number")
@click.option("--issue-type", type=str, default="story", help="Issue type (bug, story, feature)")
@click.option("--role", type=str, default="engineer", help="Role that learned this")
@click.option("--category", type=str, required=True, help="Category (security, testing, api, etc.)")
@click.option("--lesson", type=str, required=True, help="The lesson learned")
@click.option("--context", type=str, required=True, help="What triggered this lesson")
@click.option("--outcome", type=click.Choice(["success", "failure", "partial"]), required=True)
@click.pass_context
def lessons_add_cmd(
    ctx: click.Context,
    issue: int,
    issue_type: str,
    role: str,
    category: str,
    lesson: str,
    context: str,
    outcome: str
) -> None:
    """Add a new lesson learned."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    new_lesson = LessonLearned(
        id=str(uuid.uuid4())[:8],
        issue=issue,
        issue_type=issue_type,
        role=role,
        category=category,
        lesson=lesson,
        context=context,
        outcome=outcome
    )

    memory.add_lesson(new_lesson)

    click.secho(f"[OK] Lesson added: {lesson[:50]}...", fg="green")


@memory_cmd.command("record")
@click.argument("issue", type=int)
@click.option("--role", type=str, required=True, help="Role performing the action")
@click.option("--action", type=str, required=True, help="What was attempted")
@click.option("--outcome", type=click.Choice(["success", "failure", "partial"]), required=True)
@click.option("--error-type", type=str, help="Error classification if failed")
@click.option("--error-message", type=str, help="Error message if failed")
@click.option("--duration", type=float, help="Duration in seconds")
@click.option("--tokens", type=int, help="Tokens used")
@click.pass_context
def record_cmd(
    ctx: click.Context,
    issue: int,
    role: str,
    action: str,
    outcome: str,
    error_type: Optional[str],
    error_message: Optional[str],
    duration: Optional[float],
    tokens: Optional[int]
) -> None:
    """Record an execution outcome."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    record = ExecutionRecord(
        issue=issue,
        role=role,
        action=action,
        outcome=outcome,
        error_type=error_type,
        error_message=error_message,
        duration_seconds=duration,
        tokens_used=tokens
    )

    memory.record_execution(record)

    # Show updated stats
    success_rate = memory.get_success_rate(role)
    click.secho(f"[OK] Execution recorded: {outcome}", fg="green" if outcome == "success" else "yellow")
    click.echo(f"   {role.title()} success rate: {success_rate:.1%}")


@memory_cmd.command("metrics")
@click.option("--role", type=str, help="Show metrics for specific role")
@click.pass_context
def metrics_cmd(ctx: click.Context, role: Optional[str]) -> None:
    """Show success metrics and common failures."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    click.echo("")
    click.secho("Success Metrics", fg="cyan", bold=True)
    click.echo("")

    if role:
        success_rate = memory.get_success_rate(role)
        click.echo(f"   {role.title()} Success Rate: {success_rate:.1%}")
    else:
        overall = memory.get_success_rate()
        click.echo(f"   Overall Success Rate: {overall:.1%}")

        # Show by role
        by_role = memory.metrics.get("by_role", {})
        if by_role:
            click.echo("")
            click.echo("   By Role:")
            for r, stats in by_role.items():
                total = stats.get("total", 0)
                success = stats.get("success", 0)
                rate = success / total if total > 0 else 0
                click.echo(f"   - {r.title()}: {rate:.1%} ({total} executions)")

    click.echo("")

    # Common failures
    failures = memory.get_common_failures(limit=5)
    if failures:
        click.secho("Common Failures", fg="yellow", bold=True)
        click.echo("")
        for f in failures:
            click.echo(f"   - {f['error_type']}: {f['count']} occurrences")
            if f.get('example'):
                click.echo(f"     Example: {f['example'][:60]}...")
        click.echo("")


@memory_cmd.group("session")
def session_group() -> None:
    """Manage session context for continuity."""
    pass


@session_group.command("save")
@click.argument("issue", type=int)
@click.option("--summary", type=str, required=True, help="Brief summary of what was done")
@click.option("--progress", type=str, required=True, help="Where we left off")
@click.option("--blocker", "blockers", multiple=True, help="Current blockers (can repeat)")
@click.option("--next", "next_steps", multiple=True, help="Next steps (can repeat)")
@click.option("--file", "files", multiple=True, help="Files modified (can repeat)")
@click.pass_context
def session_save_cmd(
    ctx: click.Context,
    issue: int,
    summary: str,
    progress: str,
    blockers: tuple,
    next_steps: tuple,
    files: tuple
) -> None:
    """Save session context for an issue."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    session = SessionContext(
        issue=issue,
        session_id=str(uuid.uuid4())[:8],
        summary=summary,
        progress=progress,
        blockers=list(blockers),
        next_steps=list(next_steps),
        files_modified=list(files)
    )

    memory.save_session(session)

    click.secho(f"[OK] Session saved for issue #{issue}", fg="green")


@session_group.command("show")
@click.argument("issue", type=int)
@click.option("--history", is_flag=True, help="Show full session history")
@click.pass_context
def session_show_cmd(ctx: click.Context, issue: int, history: bool) -> None:
    """Show session context for an issue."""
    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException("Not in a Git repository with ContextWeave initialized.")

    memory = Memory(repo_root)

    if history:
        sessions = memory.get_session_history(issue, limit=10)
        if not sessions:
            click.echo(f"No session history for issue #{issue}")
            return

        click.echo("")
        click.secho(f"Session History for Issue #{issue}", fg="cyan", bold=True)
        click.echo("")

        for i, sess in enumerate(reversed(sessions), 1):
            click.echo(f"{i}. {sess.timestamp}")
            click.echo(f"   Summary: {sess.summary}")
            click.echo(f"   Progress: {sess.progress}")
            click.echo("")
    else:
        session: Optional[SessionContext] = memory.get_latest_session(issue)
        if not session:
            click.echo(f"No session context for issue #{issue}")
            return

        click.echo("")
        click.secho(f"Latest Session for Issue #{issue}", fg="cyan", bold=True)
        click.echo("")
        click.echo(f"   Timestamp: {session.timestamp}")
        click.echo(f"   Summary: {session.summary}")
        click.echo(f"   Progress: {session.progress}")

        if session.blockers:
            click.echo("   Blockers:")
            for b in session.blockers:
                click.echo(f"     - {b}")

        if session.next_steps:
            click.echo("   Next Steps:")
            for s in session.next_steps:
                click.echo(f"     - {s}")

        if session.files_modified:
            click.echo("   Files Modified:")
            for f in session.files_modified:
                click.echo(f"     - {f}")

        click.echo("")
