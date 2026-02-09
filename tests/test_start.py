"""Tests for the start (quick-start) command."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from context_weave.commands.start import start_cmd
from context_weave.config import Config
from context_weave.state import State


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_git_repo():
    temp_dir = tempfile.mkdtemp()
    repo_dir = Path(temp_dir) / "test_repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    # Initialize ContextWeave dirs
    (repo_dir / ".context-weave").mkdir()
    state = State(repo_dir)
    state.save()
    config = Config(repo_dir)
    config.save()

    yield repo_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestStartCommand:

    @patch("context_weave.commands.start.subprocess.run")
    @patch("context_weave.commands.context.generate_context_file")
    def test_start_creates_issue_and_subagent(self, mock_gen_ctx, mock_run, runner, temp_git_repo):
        """Start command should create an issue, spawn subagent, and generate context."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State(temp_git_repo)
        config = Config(temp_git_repo)

        result = runner.invoke(
            start_cmd,
            ["Add login page"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "[OK]" in result.output
        assert "#1" in result.output

        # Verify issue was created in state
        state_reloaded = State(temp_git_repo)
        assert "1" in state_reloaded.local_issues
        assert state_reloaded.local_issues["1"]["title"] == "Add login page"

    @patch("context_weave.commands.start.subprocess.run")
    @patch("context_weave.commands.context.generate_context_file")
    def test_start_sanitizes_input(self, mock_gen_ctx, mock_run, runner, temp_git_repo):
        """Start command should sanitize title input."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State(temp_git_repo)
        config = Config(temp_git_repo)

        # Title with control characters
        result = runner.invoke(
            start_cmd,
            ["Fix\x00 the\x01 bug"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        state_reloaded = State(temp_git_repo)
        issue = state_reloaded.local_issues["1"]
        assert "\x00" not in issue["title"]
        assert "\x01" not in issue["title"]

    @patch("context_weave.commands.start.subprocess.run")
    @patch("context_weave.commands.context.generate_context_file")
    def test_start_branch_name_truncated(self, mock_gen_ctx, mock_run, runner, temp_git_repo):
        """Branch names should be truncated to stay under limit."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State(temp_git_repo)
        config = Config(temp_git_repo)

        long_title = "a" * 200
        result = runner.invoke(
            start_cmd,
            [long_title],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        # Check the branch name in output is under 80 chars
        for line in result.output.split("\n"):
            if "Branch:" in line:
                branch_name = line.split("Branch:")[1].strip()
                assert len(branch_name) <= 80, f"Branch too long: {len(branch_name)}"

    @patch("context_weave.commands.start.subprocess.run")
    @patch("context_weave.commands.context.generate_context_file")
    def test_start_with_options(self, mock_gen_ctx, mock_run, runner, temp_git_repo):
        """Start command should accept type, role, and label options."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State(temp_git_repo)
        config = Config(temp_git_repo)

        result = runner.invoke(
            start_cmd,
            ["Fix auth", "--type", "bug", "--role", "architect", "--label", "security"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        state_reloaded = State(temp_git_repo)
        issue = state_reloaded.local_issues["1"]
        assert issue["type"] == "bug"
        assert issue["role"] == "architect"
        assert "security" in issue["labels"]
        assert "type:bug" in issue["labels"]

    def test_start_fails_without_repo(self, runner):
        """Start should fail when not in a repository."""
        result = runner.invoke(
            start_cmd,
            ["Test"],
            obj={"repo_root": None},
        )

        assert result.exit_code != 0
        assert "Not in a ContextWeave repository" in result.output
