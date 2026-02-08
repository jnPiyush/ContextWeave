"""Tests for the doctor command."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from context_weave.commands.doctor import doctor_cmd
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

    yield repo_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDoctorCommand:

    def test_doctor_not_initialized(self, runner, temp_git_repo):
        """Doctor should report when ContextWeave is not initialized."""
        result = runner.invoke(
            doctor_cmd,
            [],
            obj={"repo_root": temp_git_repo},
        )

        assert result.exit_code == 0
        assert "not initialized" in result.output.lower()

    @patch("context_weave.commands.doctor.subprocess.run")
    def test_doctor_initialized(self, mock_run, runner, temp_git_repo):
        """Doctor should report OK when properly initialized."""
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        # Initialize
        context_dir = temp_git_repo / ".context-weave"
        context_dir.mkdir()
        state = State(temp_git_repo)
        state.save()
        config = Config(temp_git_repo)
        config.save()

        # Create hooks
        hooks_dir = temp_git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for hook in ["prepare-commit-msg", "pre-commit", "post-commit", "pre-push", "post-merge"]:
            (hooks_dir / hook).write_text("# ContextWeave hook")

        result = runner.invoke(
            doctor_cmd,
            [],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "ContextWeave initialized" in result.output

    def test_doctor_missing_hooks(self, runner, temp_git_repo):
        """Doctor should detect missing hooks."""
        context_dir = temp_git_repo / ".context-weave"
        context_dir.mkdir()
        state = State(temp_git_repo)
        state.save()
        config = Config(temp_git_repo)
        config.save()

        result = runner.invoke(
            doctor_cmd,
            [],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "FAIL" in result.output
        assert "Missing hook" in result.output

    def test_doctor_stale_worktree(self, runner, temp_git_repo):
        """Doctor should detect worktrees in state that don't exist on disk."""
        from context_weave.state import WorktreeInfo

        context_dir = temp_git_repo / ".context-weave"
        context_dir.mkdir()
        state = State(temp_git_repo)
        state.add_worktree(WorktreeInfo(
            issue=99, branch="issue-99-ghost",
            path=str(temp_git_repo / "nonexistent" / "path"),
            role="engineer"
        ))
        state.save()
        config = Config(temp_git_repo)
        config.save()

        # Create hooks to avoid unrelated failures
        hooks_dir = temp_git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        for hook in ["prepare-commit-msg", "pre-commit", "post-commit", "pre-push", "post-merge"]:
            (hooks_dir / hook).write_text("# ContextWeave hook")

        result = runner.invoke(
            doctor_cmd,
            [],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "missing on disk" in result.output.lower()

    def test_doctor_fails_without_repo(self, runner):
        """Doctor should fail when not in a repo."""
        result = runner.invoke(
            doctor_cmd,
            [],
            obj={"repo_root": None},
        )

        assert result.exit_code != 0
        assert "Not in a Git repository" in result.output
