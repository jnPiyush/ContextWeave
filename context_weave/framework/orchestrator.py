"""
Graph Workflow Orchestrator for Agent Framework integration.

Implements multi-agent workflows using sequential execution with
a fallback design. Supports graph-based workflows when the
Agent Framework's WorkflowBuilder API is available.

Workflow types match the routing logic from AGENTS.md:
- Epic: PM -> UX -> Architect -> Engineer -> Reviewer
- Feature: Architect -> Engineer -> Reviewer
- Story/Bug: Engineer -> Reviewer
- Spike: Architect
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Predefined workflow configurations from AGENTS.md routing rules."""
    FULL_EPIC = "full_epic"
    FEATURE = "feature"
    STORY = "story"
    BUG_FIX = "bug_fix"
    SPIKE = "spike"
    SINGLE_AGENT = "single_agent"


# Ordered list of roles for each workflow type
WORKFLOW_STEPS: Dict[WorkflowType, List[str]] = {
    WorkflowType.FULL_EPIC: ["pm", "ux", "architect", "engineer", "reviewer"],
    WorkflowType.FEATURE: ["architect", "engineer", "reviewer"],
    WorkflowType.STORY: ["engineer", "reviewer"],
    WorkflowType.BUG_FIX: ["engineer", "reviewer"],
    WorkflowType.SPIKE: ["architect"],
}

# Issue type to workflow type mapping
ISSUE_TYPE_MAP: Dict[str, WorkflowType] = {
    "epic": WorkflowType.FULL_EPIC,
    "feature": WorkflowType.FEATURE,
    "story": WorkflowType.STORY,
    "bug": WorkflowType.BUG_FIX,
    "spike": WorkflowType.SPIKE,
}


@dataclass
class StepResult:
    """Result from a single agent step in the workflow."""
    role: str
    output: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None


@dataclass
class WorkflowResult:
    """Result from a complete workflow execution."""
    success: bool
    outputs: Dict[str, str] = field(default_factory=dict)
    final_output: str = ""
    steps_completed: List[str] = field(default_factory=list)
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows using Agent Framework.

    Implements the routing logic from AGENTS.md:
    - Epic + Backlog -> PM -> (UX) -> Architect -> Engineer -> Reviewer
    - Bug + Backlog -> Engineer -> Reviewer
    - Spike + Backlog -> Architect
    """

    def __init__(
        self,
        repo_root: Path,
        agent_factory: Any,
        thread_store: Optional[Any] = None,
    ):
        self.repo_root = repo_root
        self.agent_factory = agent_factory
        self.thread_store = thread_store

    def determine_workflow(
        self,
        issue_type: str,
        labels: Optional[List[str]] = None,
    ) -> WorkflowType:
        """Determine the workflow type from issue metadata."""
        # Check explicit labels first
        labels = labels or []
        label_lower = [lbl.lower().replace("type:", "") for lbl in labels]

        for label in label_lower:
            if label in ISSUE_TYPE_MAP:
                return ISSUE_TYPE_MAP[label]

        # Fall back to issue_type
        return ISSUE_TYPE_MAP.get(issue_type.lower(), WorkflowType.STORY)

    async def run_workflow(
        self,
        issue: int,
        issue_type: str,
        prompt: str,
        labels: Optional[List[str]] = None,
        role: Optional[str] = None,
        workflow_type: Optional[WorkflowType] = None,
    ) -> WorkflowResult:
        """Execute a complete workflow for an issue.

        If role is specified and workflow_type is None, runs SINGLE_AGENT.
        Otherwise determines workflow from issue_type/labels.
        """
        # Single agent mode
        if role and not workflow_type:
            return await self.run_single_agent(issue, role, prompt,
                                                issue_type=issue_type,
                                                labels=labels)

        # Determine workflow
        if workflow_type is None:
            workflow_type = self.determine_workflow(issue_type, labels)

        wf_type = WorkflowType(workflow_type) if isinstance(workflow_type, str) else workflow_type
        steps = WORKFLOW_STEPS.get(wf_type, WORKFLOW_STEPS[WorkflowType.STORY])

        logger.info(
            "Running %s workflow for issue #%d: %s",
            wf_type.value, issue, " -> ".join(steps)
        )

        # Try graph-based workflow first, fall back to sequential
        try:
            return await self._run_graph_workflow(
                steps, issue, prompt, issue_type, labels, wf_type
            )
        except (ImportError, AttributeError, TypeError) as e:
            logger.info(
                "Graph workflow unavailable (%s), using sequential fallback", e
            )
            return await self._run_sequential(
                steps, issue, prompt, issue_type, labels, wf_type
            )

    async def run_single_agent(
        self,
        issue: int,
        role: str,
        prompt: str,
        issue_type: str = "story",
        labels: Optional[List[str]] = None,
    ) -> WorkflowResult:
        """Run a single agent for an issue (no multi-step workflow)."""
        logger.info("Running single agent '%s' for issue #%d", role, issue)

        try:
            agent = self.agent_factory.create_agent(
                role, issue=issue, issue_type=issue_type,
                labels=labels, additional_instructions=prompt,
            )

            # Run the agent
            response = await agent.run(prompt)
            output = str(response) if response else ""

            # Record execution
            await self._record_execution(issue, role, "single_agent_run", "success")

            return WorkflowResult(
                success=True,
                outputs={role: output},
                final_output=output,
                steps_completed=[role],
                step_results=[StepResult(role=role, output=output, success=True)],
                workflow_type=WorkflowType.SINGLE_AGENT,
            )

        except Exception as e:  # noqa: BLE001
            error_msg = str(e)
            logger.error("Single agent '%s' failed: %s", role, error_msg)
            await self._record_execution(
                issue, role, "single_agent_run", "failure",
                error_type=type(e).__name__, error_message=error_msg,
            )
            return WorkflowResult(
                success=False,
                error=error_msg,
                step_results=[StepResult(role=role, output="", success=False, error=error_msg)],
                workflow_type=WorkflowType.SINGLE_AGENT,
            )

    async def _run_graph_workflow(
        self,
        steps: List[str],
        issue: int,
        prompt: str,
        issue_type: str,
        labels: Optional[List[str]],
        workflow_type: WorkflowType,
    ) -> WorkflowResult:
        """Run using Agent Framework's graph workflow builder."""
        from agent_framework import WorkflowBuilder

        builder = WorkflowBuilder()

        # Register agents as executors
        agents = {}
        for role in steps:
            agent = self.agent_factory.create_agent(
                role, issue=issue, issue_type=issue_type, labels=labels,
            )
            agents[role] = agent
            builder.register_agent(lambda a=agent: a, name=role)

        # Add sequential edges
        for i in range(len(steps) - 1):
            builder.add_edge(steps[i], steps[i + 1])

        builder.set_start_executor(steps[0])
        workflow = builder.build()

        result = await workflow.run(prompt)
        output = str(result) if result else ""

        return WorkflowResult(
            success=True,
            outputs={steps[-1]: output},
            final_output=output,
            steps_completed=steps,
            workflow_type=workflow_type,
        )

    async def _run_sequential(
        self,
        steps: List[str],
        issue: int,
        prompt: str,
        issue_type: str,
        labels: Optional[List[str]],
        workflow_type: WorkflowType,
    ) -> WorkflowResult:
        """Fallback: run agents sequentially, passing output forward."""
        outputs: Dict[str, str] = {}
        step_results: List[StepResult] = []
        steps_completed: List[str] = []
        current_input = prompt

        for role in steps:
            logger.info("Running step: %s", role)

            try:
                agent = self.agent_factory.create_agent(
                    role, issue=issue, issue_type=issue_type,
                    labels=labels, additional_instructions=current_input,
                )

                response = await agent.run(current_input)
                output = str(response) if response else ""

                outputs[role] = output
                steps_completed.append(role)
                step_results.append(StepResult(role=role, output=output, success=True))

                await self._record_execution(issue, role, f"workflow_step_{role}", "success")

                # Pass output to next agent
                current_input = (
                    f"Previous agent ({role}) output:\n\n{output}\n\n"
                    f"Continue working on issue #{issue}."
                )

            except Exception as e:  # noqa: BLE001
                error_msg = str(e)
                logger.error("Workflow step '%s' failed: %s", role, error_msg)
                step_results.append(
                    StepResult(role=role, output="", success=False, error=error_msg)
                )
                await self._record_execution(
                    issue, role, f"workflow_step_{role}", "failure",
                    error_type=type(e).__name__, error_message=error_msg,
                )
                return WorkflowResult(
                    success=False,
                    outputs=outputs,
                    final_output=outputs.get(steps_completed[-1], "") if steps_completed else "",
                    steps_completed=steps_completed,
                    step_results=step_results,
                    error=f"Step '{role}' failed: {error_msg}",
                    workflow_type=workflow_type,
                )

        return WorkflowResult(
            success=True,
            outputs=outputs,
            final_output=outputs.get(steps[-1], ""),
            steps_completed=steps_completed,
            step_results=step_results,
            workflow_type=workflow_type,
        )

    async def _record_execution(
        self,
        issue: int,
        role: str,
        action: str,
        outcome: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record execution to memory layer."""
        try:
            from context_weave.memory import ExecutionRecord, Memory

            memory = Memory(self.repo_root)
            record = ExecutionRecord(
                issue=issue,
                role=role,
                action=action,
                outcome=outcome,
                error_type=error_type,
                error_message=error_message,
            )
            memory.record_execution(record)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to record execution: %s", e)

    def get_workflow_steps(self, workflow_type: WorkflowType) -> List[str]:
        """Return ordered list of role names for a workflow type."""
        return WORKFLOW_STEPS.get(workflow_type, [])

    def get_dry_run_summary(
        self,
        issue: int,
        issue_type: str,
        labels: Optional[List[str]] = None,
        role: Optional[str] = None,
        workflow_type: Optional[WorkflowType] = None,
    ) -> str:
        """Generate a dry-run summary showing what would execute."""
        if role and not workflow_type:
            return (
                f"Single Agent Mode\n"
                f"  Issue: #{issue}\n"
                f"  Agent: {role}\n"
                f"  Type: {issue_type}\n"
            )

        if workflow_type is None:
            workflow_type = self.determine_workflow(issue_type, labels)

        wf_type = WorkflowType(workflow_type) if isinstance(workflow_type, str) else workflow_type
        steps = WORKFLOW_STEPS.get(wf_type, [])

        lines = [
            f"Workflow: {wf_type.value}",
            f"  Issue: #{issue}",
            f"  Type: {issue_type}",
            f"  Labels: {', '.join(labels or ['none'])}",
            f"  Steps ({len(steps)}):",
        ]
        for i, step in enumerate(steps, 1):
            arrow = " -> " if i < len(steps) else ""
            lines.append(f"    {i}. {step.title()}{arrow}")

        return "\n".join(lines)
