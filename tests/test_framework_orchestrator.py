"""Tests for context_md.framework.orchestrator -- Workflow Orchestrator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from context_md.framework.orchestrator import (
    WORKFLOW_STEPS,
    StepResult,
    WorkflowOrchestrator,
    WorkflowResult,
    WorkflowType,
)


class TestWorkflowType:
    def test_all_types_defined(self):
        assert WorkflowType.FULL_EPIC.value == "full_epic"
        assert WorkflowType.FEATURE.value == "feature"
        assert WorkflowType.STORY.value == "story"
        assert WorkflowType.BUG_FIX.value == "bug_fix"
        assert WorkflowType.SPIKE.value == "spike"
        assert WorkflowType.SINGLE_AGENT.value == "single_agent"


class TestWorkflowSteps:
    def test_full_epic_steps(self):
        steps = WORKFLOW_STEPS[WorkflowType.FULL_EPIC]
        assert steps == ["pm", "ux", "architect", "engineer", "reviewer"]

    def test_story_steps(self):
        steps = WORKFLOW_STEPS[WorkflowType.STORY]
        assert steps == ["engineer", "reviewer"]

    def test_spike_steps(self):
        steps = WORKFLOW_STEPS[WorkflowType.SPIKE]
        assert steps == ["architect"]


class TestWorkflowOrchestrator:
    @pytest.fixture
    def orchestrator(self, tmp_path):
        factory = MagicMock()
        return WorkflowOrchestrator(tmp_path, factory)

    def test_determine_workflow_story(self, orchestrator):
        wf = orchestrator.determine_workflow("story")
        assert wf == WorkflowType.STORY

    def test_determine_workflow_epic(self, orchestrator):
        wf = orchestrator.determine_workflow("epic")
        assert wf == WorkflowType.FULL_EPIC

    def test_determine_workflow_bug(self, orchestrator):
        wf = orchestrator.determine_workflow("bug")
        assert wf == WorkflowType.BUG_FIX

    def test_determine_workflow_from_labels(self, orchestrator):
        wf = orchestrator.determine_workflow("story", labels=["type:epic"])
        assert wf == WorkflowType.FULL_EPIC

    def test_determine_workflow_unknown_defaults_to_story(self, orchestrator):
        wf = orchestrator.determine_workflow("unknown_type")
        assert wf == WorkflowType.STORY

    def test_get_workflow_steps(self, orchestrator):
        steps = orchestrator.get_workflow_steps(WorkflowType.FEATURE)
        assert steps == ["architect", "engineer", "reviewer"]

    def test_dry_run_summary(self, orchestrator):
        summary = orchestrator.get_dry_run_summary(
            issue=42, issue_type="story"
        )
        assert "story" in summary.lower()
        assert "#42" in summary

    def test_dry_run_summary_single_agent(self, orchestrator):
        summary = orchestrator.get_dry_run_summary(
            issue=42, issue_type="story", role="engineer"
        )
        assert "single agent" in summary.lower()
        assert "engineer" in summary.lower()


class TestWorkflowResult:
    def test_success_result(self):
        result = WorkflowResult(
            success=True,
            outputs={"engineer": "code output"},
            final_output="code output",
            steps_completed=["engineer"],
        )
        assert result.success
        assert result.final_output == "code output"
        assert result.error is None

    def test_failure_result(self):
        result = WorkflowResult(
            success=False,
            error="Step 'engineer' failed",
        )
        assert not result.success
        assert "engineer" in result.error


class TestStepResult:
    def test_success(self):
        step = StepResult(role="engineer", output="done", success=True)
        assert step.success
        assert step.error is None

    def test_failure(self):
        step = StepResult(role="engineer", output="", success=False, error="timeout")
        assert not step.success
        assert step.error == "timeout"


class TestSequentialWorkflow:
    @pytest.mark.asyncio
    async def test_run_single_agent(self, tmp_path):
        mock_agent = AsyncMock()
        mock_agent.run.return_value = "Task completed successfully"

        mock_factory = MagicMock()
        mock_factory.create_agent.return_value = mock_agent

        orchestrator = WorkflowOrchestrator(tmp_path, mock_factory)
        result = await orchestrator.run_single_agent(
            issue=1, role="engineer", prompt="Fix the bug"
        )

        assert result.success
        assert "Task completed successfully" in result.final_output
        assert result.steps_completed == ["engineer"]

    @pytest.mark.asyncio
    async def test_run_single_agent_failure(self, tmp_path):
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("Agent crashed")

        mock_factory = MagicMock()
        mock_factory.create_agent.return_value = mock_agent

        orchestrator = WorkflowOrchestrator(tmp_path, mock_factory)
        result = await orchestrator.run_single_agent(
            issue=1, role="engineer", prompt="Fix the bug"
        )

        assert not result.success
        assert "crashed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_workflow_sequential(self, tmp_path):
        """Test sequential fallback when WorkflowBuilder is unavailable."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = "Step output"

        mock_factory = MagicMock()
        mock_factory.create_agent.return_value = mock_agent

        orchestrator = WorkflowOrchestrator(tmp_path, mock_factory)
        result = await orchestrator.run_workflow(
            issue=1, issue_type="story", prompt="Implement feature"
        )

        assert result.success
        # Story workflow: engineer -> reviewer
        assert "engineer" in result.steps_completed
        assert "reviewer" in result.steps_completed

    @pytest.mark.asyncio
    async def test_run_workflow_step_failure_stops(self, tmp_path):
        """Test that failure in a step stops the workflow."""
        call_count = 0

        async def mock_run(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Engineer failed")
            return "ok"

        mock_agent = AsyncMock()
        mock_agent.run = mock_run

        mock_factory = MagicMock()
        mock_factory.create_agent.return_value = mock_agent

        orchestrator = WorkflowOrchestrator(tmp_path, mock_factory)
        result = await orchestrator.run_workflow(
            issue=1, issue_type="story", prompt="Implement feature"
        )

        assert not result.success
        assert "engineer" not in result.steps_completed
        # Reviewer should not have run
        assert "reviewer" not in result.steps_completed
