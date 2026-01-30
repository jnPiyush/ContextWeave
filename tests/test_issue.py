"""
Tests for Issue Command

Coverage target: 70%+ (from 19%)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from context_md.commands.issue import (
    issue_cmd,
    create_cmd,
    list_cmd,
    show_cmd,
    close_cmd,
    reopen_cmd,
    edit_cmd,
    _sanitize_text,
    _sanitize_label,
    MAX_TITLE_LENGTH,
    MAX_BODY_LENGTH,
    MAX_LABEL_LENGTH,
)
from context_md.state import State


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_state(tmp_path):
    """Create a state with initialized directory."""
    state_dir = tmp_path / ".agent-context"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = State(tmp_path)
    state.save()
    return state


class TestInputSanitization:
    """Test input sanitization functions."""

    def test_sanitize_text_basic(self):
        """Test basic text sanitization."""
        result = _sanitize_text("Hello World", MAX_TITLE_LENGTH, "title")
        assert result == "Hello World"

    def test_sanitize_text_strips_whitespace(self):
        """Test whitespace stripping."""
        result = _sanitize_text("  Hello World  ", MAX_TITLE_LENGTH, "title")
        assert result == "Hello World"

    def test_sanitize_text_removes_control_chars(self):
        """Test control character removal."""
        result = _sanitize_text("Hello\x00World\x1f", MAX_TITLE_LENGTH, "title")
        assert result == "HelloWorld"
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_sanitize_text_preserves_newlines_in_body(self):
        """Test that newlines are preserved in body text."""
        result = _sanitize_text("Line1\nLine2\tTabbed", MAX_BODY_LENGTH, "body")
        assert "\n" in result
        assert "\t" in result

    def test_sanitize_text_enforces_max_length(self):
        """Test maximum length enforcement."""
        long_text = "A" * 500
        result = _sanitize_text(long_text, MAX_TITLE_LENGTH, "title")
        assert len(result) <= MAX_TITLE_LENGTH

    def test_sanitize_text_empty_returns_empty(self):
        """Test that empty text returns empty (for optional fields)."""
        result = _sanitize_text("", MAX_TITLE_LENGTH, "title")
        assert result == ""

    def test_sanitize_text_whitespace_only_raises_error(self):
        """Test that whitespace-only text raises error."""
        import click
        with pytest.raises(click.BadParameter, match="cannot be empty"):
            _sanitize_text("   \t\n   ", MAX_TITLE_LENGTH, "title")

    def test_sanitize_label_basic(self):
        """Test basic label sanitization."""
        result = _sanitize_label("type:bug")
        assert result == "type:bug"

    def test_sanitize_label_removes_special_chars(self):
        """Test that special characters are removed from labels."""
        result = _sanitize_label("type:bug!@#$%")
        assert result == "type:bug"

    def test_sanitize_label_allows_dash_underscore(self):
        """Test that dashes and underscores are allowed."""
        result = _sanitize_label("priority-p1_high")
        assert result == "priority-p1_high"

    def test_sanitize_label_enforces_max_length(self):
        """Test label length enforcement."""
        long_label = "a" * 100
        result = _sanitize_label(long_label)
        assert len(result) <= MAX_LABEL_LENGTH


class TestCreateCommand:
    """Test issue create command."""

    def test_create_basic_issue(self, runner, tmp_path):
        """Test creating a basic issue."""
        # Setup state
        state_dir = tmp_path / ".agent-context"
        state_dir.mkdir(parents=True, exist_ok=True)
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            create_cmd,
            ["Test Issue Title"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created issue #1" in result.output
        assert "Test Issue Title" in result.output

    def test_create_issue_with_options(self, runner, tmp_path):
        """Test creating an issue with all options."""
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            create_cmd,
            [
                "Bug in login",
                "--body", "Steps to reproduce: ...",
                "--type", "bug",
                "--label", "priority:p0",
                "--role", "engineer"
            ],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created issue #1" in result.output
        assert "bug" in result.output.lower()

        # Verify stored data
        state2 = State(tmp_path)
        issue = state2.local_issues.get("1")
        assert issue is not None
        assert issue["title"] == "Bug in login"
        assert issue["type"] == "bug"
        assert "type:bug" in issue["labels"]
        assert issue["role"] == "engineer"

    def test_create_issue_increments_number(self, runner, tmp_path):
        """Test that issue numbers increment properly."""
        state = State(tmp_path)
        state.save()

        # Create first issue
        runner.invoke(
            create_cmd,
            ["First Issue"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        # Create second issue
        state2 = State(tmp_path)
        result = runner.invoke(
            create_cmd,
            ["Second Issue"],
            obj={"repo_root": tmp_path, "state": state2},
            catch_exceptions=False
        )

        assert "Created issue #2" in result.output

    def test_create_issue_sanitizes_title(self, runner, tmp_path):
        """Test that title is sanitized."""
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            create_cmd,
            ["  Title with\x00control chars  "],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        issue = state2.local_issues.get("1")
        assert "\x00" not in issue["title"]
        assert issue["title"] == "Title withcontrol chars"

    def test_create_issue_no_repo(self, runner):
        """Test error when not in a repository."""
        result = runner.invoke(
            create_cmd,
            ["Test Issue"],
            obj={},  # No repo_root
            catch_exceptions=False
        )

        assert result.exit_code != 0
        assert "Not in a Context.md repository" in result.output


class TestListCommand:
    """Test issue list command."""

    def test_list_empty(self, runner, tmp_path):
        """Test listing when no issues exist."""
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            list_cmd,
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_list_shows_issues(self, runner, tmp_path):
        """Test listing existing issues."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "First Issue", "state": "open", "labels": ["type:story"]},
            "2": {"number": 2, "title": "Second Issue", "state": "open", "labels": ["type:bug"]}
        }
        state.save()

        result = runner.invoke(
            list_cmd,
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "First Issue" in result.output
        assert "Second Issue" in result.output
        assert "#1" in result.output
        assert "#2" in result.output

    def test_list_filter_by_state(self, runner, tmp_path):
        """Test filtering issues by state."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Open Issue", "state": "open", "labels": []},
            "2": {"number": 2, "title": "Closed Issue", "state": "closed", "labels": []}
        }
        state.save()

        result = runner.invoke(
            list_cmd,
            ["--state", "closed"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert "Closed Issue" in result.output
        assert "Open Issue" not in result.output

    def test_list_filter_by_type(self, runner, tmp_path):
        """Test filtering issues by type."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Bug", "state": "open", "type": "bug", "labels": []},
            "2": {"number": 2, "title": "Feature", "state": "open", "type": "feature", "labels": []}
        }
        state.save()

        result = runner.invoke(
            list_cmd,
            ["--type", "bug"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert "Bug" in result.output
        assert "Feature" not in result.output

    def test_list_json_output(self, runner, tmp_path):
        """Test JSON output format."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open", "labels": []}
        }
        state.save()

        result = runner.invoke(
            list_cmd,
            ["--json"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Test"


class TestShowCommand:
    """Test issue show command."""

    def test_show_issue(self, runner, tmp_path):
        """Test showing an issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {
                "number": 1,
                "title": "Test Issue",
                "body": "Description here",
                "state": "open",
                "type": "story",
                "labels": ["type:story", "priority:p1"],
                "created_at": "2026-01-30T00:00:00Z"
            }
        }
        state.save()

        result = runner.invoke(
            show_cmd,
            ["1"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Test Issue" in result.output
        assert "Description here" in result.output
        assert "open" in result.output

    def test_show_nonexistent_issue(self, runner, tmp_path):
        """Test showing a nonexistent issue."""
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            show_cmd,
            ["999"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show_json_output(self, runner, tmp_path):
        """Test JSON output format."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open"}
        }
        state.save()

        result = runner.invoke(
            show_cmd,
            ["1", "--json"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "Test"


class TestCloseCommand:
    """Test issue close command."""

    def test_close_issue(self, runner, tmp_path):
        """Test closing an issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open"}
        }
        state.save()

        result = runner.invoke(
            close_cmd,
            ["1"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Closed issue #1" in result.output

        # Verify state
        state2 = State(tmp_path)
        assert state2.local_issues["1"]["state"] == "closed"

    def test_close_with_reason(self, runner, tmp_path):
        """Test closing with a reason."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open"}
        }
        state.save()

        result = runner.invoke(
            close_cmd,
            ["1", "--reason", "Completed"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert state2.local_issues["1"]["close_reason"] == "Completed"

    def test_close_already_closed(self, runner, tmp_path):
        """Test closing an already closed issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "closed"}
        }
        state.save()

        result = runner.invoke(
            close_cmd,
            ["1"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert "already closed" in result.output


class TestReopenCommand:
    """Test issue reopen command."""

    def test_reopen_issue(self, runner, tmp_path):
        """Test reopening a closed issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "closed", "closed_at": "2026-01-30T00:00:00Z"}
        }
        state.save()

        result = runner.invoke(
            reopen_cmd,
            ["1"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Reopened issue #1" in result.output

        state2 = State(tmp_path)
        assert state2.local_issues["1"]["state"] == "open"
        assert "closed_at" not in state2.local_issues["1"]

    def test_reopen_already_open(self, runner, tmp_path):
        """Test reopening an already open issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open"}
        }
        state.save()

        result = runner.invoke(
            reopen_cmd,
            ["1"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert "already open" in result.output


class TestEditCommand:
    """Test issue edit command."""

    def test_edit_title(self, runner, tmp_path):
        """Test editing issue title."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Old Title", "state": "open", "labels": []}
        }
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["1", "--title", "New Title"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert state2.local_issues["1"]["title"] == "New Title"

    def test_edit_body(self, runner, tmp_path):
        """Test editing issue body."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "body": "Old", "state": "open", "labels": []}
        }
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["1", "--body", "New Description"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert state2.local_issues["1"]["body"] == "New Description"

    def test_edit_add_labels(self, runner, tmp_path):
        """Test adding labels to an issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open", "labels": ["type:story"]}
        }
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["1", "--add-label", "priority:p0"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert "priority:p0" in state2.local_issues["1"]["labels"]
        assert "type:story" in state2.local_issues["1"]["labels"]

    def test_edit_remove_labels(self, runner, tmp_path):
        """Test removing labels from an issue."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open", "labels": ["type:story", "needs-review"]}
        }
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["1", "--remove-label", "needs-review"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert "needs-review" not in state2.local_issues["1"]["labels"]

    def test_edit_sanitizes_input(self, runner, tmp_path):
        """Test that edit sanitizes input."""
        state = State(tmp_path)
        state.local_issues = {
            "1": {"number": 1, "title": "Test", "state": "open", "labels": []}
        }
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["1", "--title", "Title with\x00null"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        state2 = State(tmp_path)
        assert "\x00" not in state2.local_issues["1"]["title"]

    def test_edit_nonexistent_issue(self, runner, tmp_path):
        """Test editing a nonexistent issue."""
        state = State(tmp_path)
        state.save()

        result = runner.invoke(
            edit_cmd,
            ["999", "--title", "New Title"],
            obj={"repo_root": tmp_path, "state": state},
            catch_exceptions=False
        )

        assert result.exit_code != 0
        assert "not found" in result.output
