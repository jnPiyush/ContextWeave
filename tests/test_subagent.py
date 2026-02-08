"""Tests for SubAgent commands."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from context_weave.commands.subagent import (
    ROLE_NEXT,
    complete_cmd,
    handoff_cmd,
    list_cmd,
    recover_cmd,
    spawn_cmd,
    status_cmd,
)
from context_weave.config import Config
from context_weave.state import State, WorktreeInfo


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_git_repo():
    """Create a temporary Git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_dir = Path(temp_dir) / "test_repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    yield repo_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSubagentCommands:
    """Test SubAgent command behaviors."""

    def test_spawn_fails_when_worktree_exists(self, runner, temp_git_repo):
        """Spawning for an existing worktree should fail."""
        state = State(temp_git_repo)
        state.add_worktree(
            WorktreeInfo(
                issue=1,
                branch="issue-1-test",
                path=str(temp_git_repo / "worktrees" / "1"),
                role="engineer",
            )
        )
        state.save()

        result = runner.invoke(
            spawn_cmd,
            ["1", "--role", "engineer"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_list_cmd_json_output(self, runner, temp_git_repo):
        """List command should emit JSON when requested."""
        state = State(temp_git_repo)
        worktree = WorktreeInfo(
            issue=2,
            branch="issue-2-test",
            path=str(temp_git_repo / "worktrees" / "2"),
            role="engineer",
        )
        state.add_worktree(worktree)
        state.save()

        result = runner.invoke(
            list_cmd,
            ["--json"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["issue"] == 2

    @patch("context_weave.commands.subagent.subprocess.run")
    def test_status_cmd_json_output(self, mock_run, runner, temp_git_repo, monkeypatch):
        """Status command returns JSON output with worktree details."""
        worktree_path = temp_git_repo / "worktrees" / "3"
        worktree_path.mkdir(parents=True, exist_ok=True)

        state = State(temp_git_repo)
        state.add_worktree(
            WorktreeInfo(
                issue=3,
                branch="issue-3-test",
                path=str(worktree_path),
                role="engineer",
            )
        )
        state.save()

        monkeypatch.setattr(state, "get_last_commit_time", lambda _branch: None)
        monkeypatch.setattr(state, "get_branch_note", lambda _branch: {"status": "spawned"})

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(
            status_cmd,
            ["3", "--json"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["issue"] == 3
        assert data["worktree_exists"] is True

    @patch("context_weave.commands.subagent.subprocess.run")
    def test_complete_cmd_force_keep_branch(self, mock_run, runner, temp_git_repo):
        """Complete command should remove worktree and update state when forced."""
        worktree_path = temp_git_repo / "worktrees" / "4"
        worktree_path.mkdir(parents=True, exist_ok=True)

        state = State(temp_git_repo)
        state.add_worktree(
            WorktreeInfo(
                issue=4,
                branch="issue-4-test",
                path=str(worktree_path),
                role="engineer",
            )
        )
        state.save()

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(
            complete_cmd,
            ["4", "--force", "--keep-branch"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code == 0
        assert "completed" in result.output

    @patch("context_weave.commands.subagent.subprocess.run")
    def test_recover_cmd_branch_missing(self, mock_run, runner, temp_git_repo):
        """Recover should fail if branch is missing."""
        state = State(temp_git_repo)
        state.add_worktree(
            WorktreeInfo(
                issue=5,
                branch="issue-5-test",
                path=str(temp_git_repo / "worktrees" / "5"),
                role="engineer",
            )
        )
        state.save()

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(
            recover_cmd,
            ["5"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("context_weave.commands.subagent.subprocess.run")
    def test_recover_cmd_worktree_exists(self, mock_run, runner, temp_git_repo):
        """Recover should short-circuit when worktree exists."""
        worktree_path = temp_git_repo / "worktrees" / "6"
        worktree_path.mkdir(parents=True, exist_ok=True)

        state = State(temp_git_repo)
        state.add_worktree(
            WorktreeInfo(
                issue=6,
                branch="issue-6-test",
                path=str(worktree_path),
                role="engineer",
            )
        )
        state.save()

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(
            recover_cmd,
            ["6"],
            obj={"repo_root": temp_git_repo, "state": state},
        )

        assert result.exit_code == 0
        assert "no recovery needed" in result.output.lower()


class TestHandoffCommand:

    def test_handoff_no_active_subagent(self, runner, temp_git_repo):
        """Handoff should fail when no subagent exists for the issue."""
        state = State(temp_git_repo)
        state.save()
        config = Config(temp_git_repo)
        config.save()

        result = runner.invoke(
            handoff_cmd,
            ["42"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code != 0
        assert "No active SubAgent" in result.output

    def test_handoff_no_next_role(self, runner, temp_git_repo):
        """Handoff should fail when current role has no automatic next role."""
        state = State(temp_git_repo)
        state.add_worktree(WorktreeInfo(
            issue=10, branch="issue-10-review",
            path=str(temp_git_repo / "wt" / "10"), role="reviewer"
        ))
        state.save()
        config = Config(temp_git_repo)
        config.save()

        result = runner.invoke(
            handoff_cmd,
            ["10", "--skip-validation"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code != 0
        assert "No next role" in result.output

    @patch("context_weave.commands.start._generate_context")
    def test_handoff_updates_role(self, mock_gen, runner, temp_git_repo):
        """Handoff should update the worktree role in state."""
        state = State(temp_git_repo)
        state.add_worktree(WorktreeInfo(
            issue=11, branch="issue-11-design",
            path=str(temp_git_repo / "wt" / "11"), role="architect"
        ))
        state.save()
        config = Config(temp_git_repo)
        config.save()

        result = runner.invoke(
            handoff_cmd,
            ["11", "--skip-validation"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "Handed off to engineer" in result.output

        # Verify role was updated
        state_reloaded = State(temp_git_repo)
        wt = state_reloaded.get_worktree(11)
        assert wt.role == "engineer"

    @patch("context_weave.commands.start._generate_context")
    def test_handoff_explicit_role(self, mock_gen, runner, temp_git_repo):
        """Handoff should accept explicit --to role."""
        state = State(temp_git_repo)
        state.add_worktree(WorktreeInfo(
            issue=12, branch="issue-12-task",
            path=str(temp_git_repo / "wt" / "12"), role="engineer"
        ))
        state.save()
        config = Config(temp_git_repo)
        config.save()

        result = runner.invoke(
            handoff_cmd,
            ["12", "--to", "ux", "--skip-validation"],
            obj={"repo_root": temp_git_repo, "state": state, "config": config},
        )

        assert result.exit_code == 0
        assert "Handed off to ux" in result.output

    def test_role_next_mapping(self):
        """Verify the role flow mapping is correct."""
        assert ROLE_NEXT["pm"] == "architect"
        assert ROLE_NEXT["architect"] == "engineer"
        assert ROLE_NEXT["engineer"] == "reviewer"
        assert ROLE_NEXT["reviewer"] is None
        assert ROLE_NEXT["ux"] == "engineer"
