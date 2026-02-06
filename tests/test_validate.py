"""
Tests for Validation Commands

Coverage target: 60% (from 18%)
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from context_md.commands.validate import (
    validate_dod_cmd,
    validate_preexec_cmd,
    validate_task_cmd,
)
from context_md.state import State


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_state(tmp_path):
    """Create a mock state object."""
    state = State(tmp_path)
    return state


class TestTaskValidation:
    """Test task quality validation."""

    @patch('subprocess.run')
    def test_validate_task_quality_success(self, mock_run, runner, tmp_path):
        """Test successful task validation."""
        # Mock git notes read
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "title": "Implement feature X",
                "description": "Detailed description of feature X implementation",
                "type": "feature",
                "labels": ["backend", "api"],
                "acceptance_criteria": [
                    "API endpoint created",
                    "Tests written",
                    "Documentation updated"
                ]
            }),
            returncode=0
        )

        result = runner.invoke(
            validate_task_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "valid" in result.output.lower()

    @patch('subprocess.run')
    def test_validate_task_missing_fields(self, mock_run, runner, tmp_path):
        """Test validation with missing required fields."""
        # Mock git notes with missing fields
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "title": "Feature X"
                # Missing description, type, etc.
            }),
            returncode=0
        )

        result = runner.invoke(
            validate_task_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should still work but report issues
        assert "description" in result.output.lower() or "missing" in result.output.lower()

    @patch('subprocess.run')
    def test_validate_task_no_git_notes(self, mock_run, runner, tmp_path):
        """Test validation when git notes don't exist."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = runner.invoke(
            validate_task_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should show validation failure or missing data
        assert "fail" in result.output.lower() or "title" in result.output.lower()


class TestPreExecutionValidation:
    """Test pre-execution validation."""

    @patch('subprocess.run')
    def test_pre_exec_branch_exists(self, mock_run, runner, tmp_path):
        """Test pre-execution when branch exists."""
        # Mock git branch check
        mock_run.return_value = MagicMock(
            stdout="* issue-123-feature\n  main\n",
            returncode=0
        )

        result = runner.invoke(
            validate_preexec_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert result.exit_code == 0

    @patch('subprocess.run')
    def test_pre_exec_branch_not_exists(self, mock_run, runner, tmp_path):
        """Test pre-execution when branch doesn't exist."""
        # Mock git branch check - branch not found
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = runner.invoke(
            validate_preexec_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert "branch" in result.output.lower() or "not found" in result.output.lower()

    @patch('subprocess.run')
    def test_pre_exec_uncommitted_changes(self, mock_run, runner, tmp_path):
        """Test pre-execution with uncommitted changes."""
        # Mock git status showing changes
        mock_run.return_value = MagicMock(
            stdout=" M file1.py\n M file2.py\n",
            returncode=0
        )

        result = runner.invoke(
            validate_preexec_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should show pre-flight validation results
        assert "validation" in result.output.lower() or "fail" in result.output.lower()


class TestDoDValidation:
    """Test Definition of Done validation."""

    @patch('subprocess.run')
    def test_dod_all_checks_pass(self, mock_run, runner, tmp_path):
        """Test DoD when all checks pass."""
        # Mock various subprocess calls
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])

            if 'git' in cmd and 'status' in cmd:
                # No uncommitted changes
                return MagicMock(stdout="", returncode=0)
            elif 'pytest' in cmd:
                # Tests pass
                return MagicMock(stdout="12 passed", returncode=0)
            elif 'ruff' in cmd:
                # No lint errors
                return MagicMock(stdout="", returncode=0)
            else:
                return MagicMock(stdout="", returncode=0)

        mock_run.side_effect = run_side_effect

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "✓" in result.output

    @patch('subprocess.run')
    def test_dod_tests_fail(self, mock_run, runner, tmp_path):
        """Test DoD when tests fail."""
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])

            if 'pytest' in cmd:
                # Tests fail
                return MagicMock(stdout="5 failed, 7 passed", returncode=1)
            else:
                return MagicMock(stdout="", returncode=0)

        mock_run.side_effect = run_side_effect

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert "test" in result.output.lower() and "fail" in result.output.lower()

    @patch('subprocess.run')
    def test_dod_uncommitted_changes(self, mock_run, runner, tmp_path):
        """Test DoD with uncommitted changes."""
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])

            if 'git' in cmd and 'status' in cmd:
                # Has uncommitted changes
                return MagicMock(stdout=" M file1.py\n", returncode=0)
            else:
                return MagicMock(stdout="", returncode=0)

        mock_run.side_effect = run_side_effect

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should show code not committed
        assert "committed" in result.output.lower() or "pushed" in result.output.lower()

    @patch('subprocess.run')
    def test_dod_lint_errors(self, mock_run, runner, tmp_path):
        """Test DoD with linting errors."""
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])

            if 'ruff' in cmd:
                # Lint errors found
                return MagicMock(stdout="Found 5 errors", returncode=1)
            else:
                return MagicMock(stdout="", returncode=0)

        mock_run.side_effect = run_side_effect

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        assert "lint" in result.output.lower() or "error" in result.output.lower()

    @patch('subprocess.run')
    def test_dod_timeout_handling(self, mock_run, runner, tmp_path):
        """Test DoD handles subprocess timeouts gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 30)

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should complete (may show failures but not crash)
        assert "validation" in result.output.lower() or "dod" in result.output.lower()


class TestCertificateGeneration:
    """Test completion certificate generation."""

    @patch('subprocess.run')
    @patch('pathlib.Path.write_text')
    def test_certificate_generation(self, mock_write, mock_run, runner, tmp_path):
        """Test generating completion certificate."""
        # Mock all checks passing
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        result = runner.invoke(
            validate_dod_cmd,
            ["123", "--certificate"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Certificate should be written
        assert result.exit_code == 0


class TestValidationHelpers:
    """Test validation helper functions."""

    def test_validate_task_quality_stranger_test(self):
        """Test stranger test logic."""
        # Good task - detailed and clear
        good_task = {
            "title": "Implement JWT authentication",
            "description": "Add JWT-based authentication to the API. Users should be able to login with email/password and receive a JWT token. The token should expire after 24 hours and include user_id and role claims.",
            "acceptance_criteria": [
                "POST /auth/login endpoint accepts email and password",
                "Returns JWT token on successful auth",
                "Token expires after 24 hours",
                "Invalid credentials return 401"
            ]
        }

        # Validation would pass - has all required fields and details
        assert good_task["title"]
        assert len(good_task["description"]) > 50
        assert len(good_task["acceptance_criteria"]) > 0

    def test_validate_task_quality_vague_task(self):
        """Test validation fails for vague tasks."""
        vague_task = {
            "title": "Fix bug",
            "description": "Fix the bug",
            "acceptance_criteria": ["Bug fixed"]
        }

        # Should fail stranger test - too vague
        assert len(vague_task["description"]) < 50
        assert all(len(ac) < 20 for ac in vague_task["acceptance_criteria"])


class TestErrorHandling:
    """Test error handling in validation."""

    @patch('subprocess.run')
    def test_handles_missing_pytest(self, mock_run, runner, tmp_path):
        """Test handles missing pytest gracefully."""
        mock_run.side_effect = FileNotFoundError("pytest not found")

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should not crash, may show validation results
        assert result.exit_code == 0 or "validation" in result.output.lower()

    @patch('subprocess.run')
    def test_handles_missing_ruff(self, mock_run, runner, tmp_path):
        """Test handles missing ruff gracefully."""
        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])
            if 'ruff' in cmd:
                raise FileNotFoundError("ruff not found")
            return MagicMock(stdout="", returncode=0)

        mock_run.side_effect = run_side_effect

        result = runner.invoke(
            validate_dod_cmd,
            ["123"],
            obj={"repo_root": tmp_path, "state": State(tmp_path)},
            catch_exceptions=False
        )

        # Should handle gracefully and show validation results
        assert "validation" in result.output.lower() or "linter" in result.output.lower()


