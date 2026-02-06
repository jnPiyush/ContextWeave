"""Tests for context_md.framework.run -- CLI run command."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from context_md.framework.run import run_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_repo(tmp_path):
    """Create a minimal repo structure."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".agent-context").mkdir()
    return tmp_path


class TestRunCommandHelp:
    def test_help(self, runner):
        result = runner.invoke(run_cmd, ["--help"])
        assert result.exit_code == 0
        assert "Run an AI agent workflow" in result.output
        assert "--role" in result.output
        assert "--dry-run" in result.output
        assert "--resume" in result.output


class TestRunCommandFrameworkCheck:
    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", False)
    def test_not_installed(self, runner, mock_repo):
        result = runner.invoke(
            run_cmd, ["42"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code != 0
        assert "not installed" in result.output.lower()

    def test_no_repo_root(self, runner):
        result = runner.invoke(
            run_cmd, ["42"],
            obj={"verbose": False},
        )
        assert result.exit_code != 0


class TestRunCommandDryRun:
    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    def test_dry_run(self, runner, mock_repo):
        result = runner.invoke(
            run_cmd,
            ["42", "--dry-run", "--type", "story"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "story" in result.output.lower()

    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    def test_dry_run_single_agent(self, runner, mock_repo):
        result = runner.invoke(
            run_cmd,
            ["42", "--dry-run", "--role", "engineer"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0
        assert "engineer" in result.output.lower()

    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    def test_dry_run_epic(self, runner, mock_repo):
        result = runner.invoke(
            run_cmd,
            ["42", "--dry-run", "--type", "epic"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0


class TestRunCommandExecution:
    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    @patch("context_md.framework.run._run_async")
    def test_run_workflow(self, mock_run_async, runner, mock_repo):
        from context_md.framework.orchestrator import WorkflowResult, WorkflowType

        mock_run_async.return_value = WorkflowResult(
            success=True,
            outputs={"engineer": "code done"},
            final_output="All done",
            steps_completed=["engineer", "reviewer"],
            workflow_type=WorkflowType.STORY,
        )

        result = runner.invoke(
            run_cmd,
            ["42", "--type", "story"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    @patch("context_md.framework.run._run_async")
    def test_run_with_json_output(self, mock_run_async, runner, mock_repo):
        from context_md.framework.orchestrator import WorkflowResult, WorkflowType

        mock_run_async.return_value = WorkflowResult(
            success=True,
            outputs={"engineer": "done"},
            final_output="done",
            steps_completed=["engineer"],
            workflow_type=WorkflowType.SINGLE_AGENT,
        )

        result = runner.invoke(
            run_cmd,
            ["42", "--role", "engineer", "--json-output"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["success"] is True

    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    @patch("context_md.framework.run._run_async")
    def test_run_failure(self, mock_run_async, runner, mock_repo):
        from context_md.framework.orchestrator import WorkflowResult

        mock_run_async.return_value = WorkflowResult(
            success=False,
            error="Agent crashed",
        )

        result = runner.invoke(
            run_cmd,
            ["42", "--role", "engineer"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code == 0  # CLI exits 0, shows FAIL in output
        assert "FAIL" in result.output

    @patch("context_md.framework.AGENT_FRAMEWORK_AVAILABLE", True)
    @patch("context_md.framework.run.asyncio")
    def test_run_exception(self, mock_asyncio, runner, mock_repo):
        mock_asyncio.run.side_effect = RuntimeError("Connection failed")

        result = runner.invoke(
            run_cmd,
            ["42", "--role", "engineer"],
            obj={"repo_root": mock_repo, "verbose": False},
        )
        assert result.exit_code != 0
        assert "failed" in result.output.lower()
