"""
CLI Command for running Agent Framework workflows.

Provides the `context-weave run` command that bridges the sync Click CLI
to the async Agent Framework using asyncio.run().

Usage:
    context-weave run 42 --role engineer
    context-weave run 42 --type story
    context-weave run 42 --dry-run
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

import click

logger = logging.getLogger(__name__)


@click.command("run")
@click.argument("issue", type=int)
@click.option(
    "--role",
    type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
    help="Run a specific agent role (single-agent mode)",
)
@click.option(
    "--type", "issue_type",
    type=click.Choice(["epic", "feature", "story", "bug", "spike"]),
    default="story",
    help="Issue type (determines workflow)",
)
@click.option("--labels", help="Comma-separated labels")
@click.option("--prompt", help="Custom prompt/instructions")
@click.option(
    "--workflow",
    "workflow_type",
    type=click.Choice(["full_epic", "feature", "story", "bug_fix", "spike", "single_agent"]),
    help="Force a specific workflow type",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "azure_openai", "anthropic"]),
    help="LLM provider override",
)
@click.option("--model", help="Model name override")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.option("--resume", is_flag=True, help="Resume from existing thread")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
@click.pass_context
def run_cmd(
    ctx: click.Context,
    issue: int,
    role: Optional[str],
    issue_type: str,
    labels: Optional[str],
    prompt: Optional[str],
    workflow_type: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    dry_run: bool,
    resume: bool,
    json_out: bool,
) -> None:
    """Run an AI agent workflow for an issue.

    Uses the Microsoft Agent Framework to execute role-based agents
    with the full ContextWeave 4-layer context architecture.

    Requires: pip install agent-framework --pre

    \b
    Examples:
        context-weave run 42                          # Auto-detect workflow
        context-weave run 42 --role engineer          # Single agent
        context-weave run 42 --type epic              # Full epic workflow
        context-weave run 42 --dry-run                # Preview workflow
        context-weave run 42 --resume                 # Resume from thread
    """
    from context_weave.framework import AGENT_FRAMEWORK_AVAILABLE

    if not AGENT_FRAMEWORK_AVAILABLE:
        raise click.ClickException(
            "Microsoft Agent Framework not installed.\n"
            "Install with: pip install agent-framework --pre\n"
            "Or: pip install context-weave[agent]"
        )

    repo_root = ctx.obj.get("repo_root")
    if not repo_root:
        raise click.ClickException(
            "Not in a Git repository with ContextWeave initialized.\n"
            "Run 'context-weave init' first."
        )

    repo_root = Path(repo_root)
    verbose = ctx.obj.get("verbose", False)
    label_list = [lbl.strip() for lbl in labels.split(",")] if labels else []
    default_prompt = prompt or f"Work on issue #{issue}"

    # Dry run: show what would execute
    if dry_run:
        _handle_dry_run(
            repo_root, issue, issue_type, label_list,
            role, workflow_type, provider, model, verbose,
        )
        return

    # Execute the workflow
    try:
        result = asyncio.run(
            _run_async(
                repo_root=repo_root,
                issue=issue,
                role=role,
                issue_type=issue_type,
                labels=label_list,
                prompt=default_prompt,
                workflow_type=workflow_type,
                provider=provider,
                model=model,
                resume=resume,
                verbose=verbose,
            )
        )
    except KeyboardInterrupt:
        click.echo("\nWorkflow cancelled by user.", err=True)
        return
    except Exception as e:
        raise click.ClickException(f"Agent execution failed: {e}") from e

    # Output results
    if json_out:
        _output_json(result)
    else:
        _output_human(result, verbose)


async def _run_async(
    repo_root: Path,
    issue: int,
    role: Optional[str] = None,
    issue_type: str = "story",
    labels: Optional[list] = None,
    prompt: str = "",
    workflow_type: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    resume: bool = False,
    verbose: bool = False,
) -> "WorkflowResult":  # noqa: F821
    """Async implementation of the run command."""
    from context_weave.framework.config import LLMProvider, load_llm_config
    from context_weave.framework.context_provider import ContextWeaveProvider
    from context_weave.framework.middleware import create_middleware_stack
    from context_weave.framework.orchestrator import WorkflowOrchestrator, WorkflowType
    from context_weave.framework.thread_store import GitThreadStore
    from context_weave.framework.tools import ToolRegistry

    # 1. Load and configure LLM
    llm_config = load_llm_config(repo_root)

    if provider:
        llm_config.provider = LLMProvider(provider)
        # Set appropriate env var name for the provider
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "azure_openai": "AZURE_OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        llm_config.api_key_env_var = env_var_map.get(provider, llm_config.api_key_env_var)

    if model:
        if llm_config.provider == LLMProvider.ANTHROPIC:
            llm_config.anthropic_model = model
        else:
            llm_config.model = model

    # 2. Create components
    tool_registry = ToolRegistry(repo_root)

    effective_role = role or "engineer"
    context_provider = ContextWeaveProvider(
        repo_root, issue, effective_role, issue_type, labels
    )

    middleware = create_middleware_stack(repo_root, issue, effective_role)

    # 3. Create agent factory (lazy import to avoid circular)
    from context_weave.framework.agents import AgentFactory

    factory = AgentFactory(
        repo_root=repo_root,
        llm_config=llm_config,
        tool_registry=tool_registry,
        context_provider=context_provider,
        middleware=middleware,
    )

    # 4. Setup thread store if resuming
    thread_store = None
    if resume:
        thread_store = GitThreadStore(repo_root, issue, effective_role)
        if thread_store.messages:
            logger.info(
                "Resuming thread %s with %d existing messages",
                thread_store.thread_id, len(thread_store.messages)
            )

    # 5. Create orchestrator and run
    orchestrator = WorkflowOrchestrator(
        repo_root=repo_root,
        agent_factory=factory,
        thread_store=thread_store,
    )

    wf_type = WorkflowType(workflow_type) if workflow_type else None

    result = await orchestrator.run_workflow(
        issue=issue,
        issue_type=issue_type,
        prompt=prompt,
        labels=labels,
        role=role,
        workflow_type=wf_type,
    )

    # 6. Save thread state
    if thread_store:
        from context_weave.framework.thread_store import ChatMessage

        await thread_store.add_messages([
            ChatMessage("user", prompt),
            ChatMessage("assistant", result.final_output),
        ])

    return result


def _handle_dry_run(
    repo_root: Path,
    issue: int,
    issue_type: str,
    labels: list,
    role: Optional[str],
    workflow_type: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    verbose: bool,
) -> None:
    """Show what would execute without running."""
    from context_weave.framework.config import load_llm_config
    from context_weave.framework.orchestrator import WorkflowOrchestrator, WorkflowType
    from context_weave.framework.tools import ToolRegistry

    llm_config = load_llm_config(repo_root)

    click.secho("\n[DRY RUN] Agent Workflow Preview\n", fg="cyan", bold=True)

    # Show configuration
    click.echo(f"  Repository: {repo_root}")
    click.echo(f"  LLM Provider: {provider or llm_config.provider.value}")
    click.echo(f"  Model: {model or llm_config.model}")
    click.echo("")

    # Show workflow plan
    tool_registry = ToolRegistry(repo_root)

    # We don't need a real factory for dry run -- use orchestrator directly
    from context_weave.framework.agents import AgentFactory

    factory = AgentFactory(repo_root, llm_config, tool_registry)
    orchestrator = WorkflowOrchestrator(repo_root, factory)

    wf_type = WorkflowType(workflow_type) if workflow_type else None
    summary = orchestrator.get_dry_run_summary(
        issue, issue_type, labels, role, wf_type
    )
    click.echo(summary)

    # Show available tools for the role
    effective_role = role or "engineer"
    tools = tool_registry.get_tools_for_role(effective_role)
    click.echo(f"\n  Tools ({len(tools)}):")
    for tool in tools:
        name = getattr(tool, "__name__", str(tool))
        doc = getattr(tool, "__doc__", "")
        if doc:
            doc = doc.strip().split("\n")[0]
        click.echo(f"    - {name}: {doc}")

    # Show thread status
    from context_weave.framework.thread_store import GitThreadStore

    if GitThreadStore.thread_exists(repo_root, issue, effective_role):
        click.secho(f"\n  Existing thread found for issue #{issue}/{effective_role}", fg="yellow")
        click.echo("  Use --resume to continue from previous conversation")

    click.echo("")


def _output_human(result: Any, verbose: bool = False) -> None:
    """Format and print results for human consumption."""
    if result.success:
        click.secho("\n[OK] Workflow completed successfully\n", fg="green")
    else:
        click.secho(f"\n[FAIL] Workflow failed: {result.error}\n", fg="red")

    # Show steps
    click.echo(f"  Steps completed: {', '.join(result.steps_completed)}")

    if result.workflow_type:
        click.echo(f"  Workflow: {result.workflow_type.value}")

    # Show step details
    if verbose and result.step_results:
        click.echo("\n  Step Details:")
        for step in result.step_results:
            status = click.style("[OK]", fg="green") if step.success else click.style("[FAIL]", fg="red")
            click.echo(f"    {status} {step.role}")
            if step.error:
                click.echo(f"         Error: {step.error}")

    # Show final output
    if result.final_output:
        click.echo("\n--- Output ---\n")
        # Truncate long outputs
        output = result.final_output
        if len(output) > 2000 and not verbose:
            click.echo(output[:2000])
            click.echo(f"\n... ({len(output) - 2000} chars truncated, use -v for full output)")
        else:
            click.echo(output)

    click.echo("")


def _output_json(result: Any) -> None:
    """Print results as JSON."""
    data = {
        "success": result.success,
        "steps_completed": result.steps_completed,
        "workflow_type": result.workflow_type.value if result.workflow_type else None,
        "error": result.error,
        "outputs": result.outputs,
        "final_output": result.final_output,
    }
    if result.step_results:
        data["step_results"] = [
            {
                "role": s.role,
                "success": s.success,
                "error": s.error,
                "output_length": len(s.output),
            }
            for s in result.step_results
        ]
    click.echo(json.dumps(data, indent=2))
