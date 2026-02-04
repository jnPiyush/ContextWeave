"""
Tests for Context.md CLI

Run with: pytest tests/ -v
"""

import pytest
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from context_md.cli import cli, find_repo_root
from context_md.state import State, WorktreeInfo
from context_md.config import Config
from context_md.commands.context import (
    load_role_instructions,
    load_skills,
    format_acceptance_criteria,
    format_dependencies,
    format_references,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary Git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_dir = Path(temp_dir) / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True, check=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True, check=True)
    
    yield repo_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestState:
    """Tests for State management."""
    
    def test_default_state(self, temp_git_repo):
        """Test default state creation."""
        state = State(temp_git_repo)
        assert state.mode == "local"
        assert state.worktrees == []
        assert state.github.enabled == False
    
    def test_save_and_load(self, temp_git_repo):
        """Test state persistence."""
        state = State(temp_git_repo)
        state.mode = "github"
        state.save()
        
        # Load fresh instance
        state2 = State(temp_git_repo)
        assert state2.mode == "github"
    
    def test_worktree_management(self, temp_git_repo):
        """Test worktree tracking."""
        state = State(temp_git_repo)
        
        # Add worktree
        wt = WorktreeInfo(issue=123, branch="issue-123-test", path="../wt/123", role="engineer")
        state.add_worktree(wt)
        state.save()
        
        # Verify
        assert len(state.worktrees) == 1
        assert state.get_worktree(123) is not None
        assert state.get_worktree(456) is None
        
        # Remove
        removed = state.remove_worktree(123)
        assert removed is not None
        assert len(state.worktrees) == 0
    
    def test_get_issue_branches(self, temp_git_repo):
        """Test getting issue branches from Git."""
        # Create an issue branch
        subprocess.run(["git", "branch", "issue-100-test"], cwd=temp_git_repo, capture_output=True, check=True)
        subprocess.run(["git", "branch", "issue-200-another"], cwd=temp_git_repo, capture_output=True, check=True)
        subprocess.run(["git", "branch", "feature-xyz"], cwd=temp_git_repo, capture_output=True, check=True)
        
        state = State(temp_git_repo)
        branches = state.get_issue_branches()
        
        assert "issue-100-test" in branches
        assert "issue-200-another" in branches
        assert "feature-xyz" not in branches


class TestConfig:
    """Tests for Config management."""
    
    def test_default_config(self, temp_git_repo):
        """Test default configuration."""
        config = Config(temp_git_repo)
        assert config.mode == "local"
        assert config.worktree_base == "../worktrees"
    
    def test_skill_routing(self, temp_git_repo):
        """Test skill routing for labels."""
        config = Config(temp_git_repo)
        
        skills = config.get_skills_for_labels(["api", "security"])
        assert "#04" in skills  # Security is in both
        assert "#09" in skills  # API design
        
        # Default skills when no match
        skills = config.get_skills_for_labels(["unknown-label"])
        assert "#02" in skills  # Testing
        assert "#04" in skills  # Security
    
    def test_get_set(self, temp_git_repo):
        """Test get/set with dot notation."""
        config = Config(temp_git_repo)
        
        # Get nested value
        threshold = config.get("validation.stuck_threshold_hours.bug")
        assert threshold == 12
        
        # Set value
        config.set("validation.stuck_threshold_hours.bug", 6)
        assert config.get("validation.stuck_threshold_hours.bug") == 6


class TestCLI:
    """Tests for CLI commands."""
    
    def test_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "context-md" in result.output
    
    def test_init_command(self, runner, temp_git_repo):
        """Test init command."""
        with runner.isolated_filesystem():
            # Copy temp repo structure
            subprocess.run(["git", "init"], capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True, check=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True, check=True)
            
            result = runner.invoke(cli, ["init", "--mode", "local"])
            
            assert result.exit_code == 0
            assert "initialized successfully" in result.output
            assert Path(".agent-context/state.json").exists()
            assert Path(".agent-context/config.json").exists()
    
    def test_config_list(self, runner, temp_git_repo):
        """Test config list command."""
        with runner.isolated_filesystem():
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True)
            
            # Initialize first
            runner.invoke(cli, ["init"])
            
            # List config
            result = runner.invoke(cli, ["config", "--list"])
            assert result.exit_code == 0
            assert "mode" in result.output
    
    def test_status_not_initialized(self, runner):
        """Test status when not initialized shows default state."""
        with runner.isolated_filesystem():
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True)
            
            result = runner.invoke(cli, ["status"])
            # Status command works even without init, shows default local mode
            assert "mode" in result.output.lower() or "subagent" in result.output.lower()


class TestContextHelpers:
    """Tests for context helper functions."""

    def test_load_role_instructions_fallback(self, tmp_path):
        """Fallback text should be used when agent file is missing."""
        content = load_role_instructions(tmp_path, "engineer")
        assert "Engineer" in content
        assert "Follow the standard" in content

    def test_load_role_instructions_from_file(self, tmp_path):
        """Load role instructions from .github/agents when present."""
        agent_dir = tmp_path / ".github" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agent_dir / "engineer.agent.md"
        agent_file.write_text("# Engineer Agent", encoding="utf-8")

        content = load_role_instructions(tmp_path, "engineer")
        assert content == "# Engineer Agent"

    def test_load_skills_with_missing_and_present_files(self, tmp_path, capsys):
        """Load skills should include existing files and warn for missing ones."""
        skills_dir = tmp_path / ".github" / "skills" / "development" / "testing"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skills_dir / "SKILL.md"
        skill_file.write_text("# Testing Skill", encoding="utf-8")

        content = load_skills(tmp_path, ["#02", "#99"], verbose=True)

        assert "Testing Skill" in content
        captured = capsys.readouterr()
        assert "Unknown skill" in captured.out or "Warning" in captured.out

    def test_format_acceptance_criteria(self):
        """Acceptance criteria should be formatted as checklist."""
        formatted = format_acceptance_criteria(["Do thing", "Validate thing"])
        assert "- [ ] Do thing" in formatted

    def test_format_dependencies(self):
        """Dependencies should be formatted consistently."""
        deps = [{"issue": 1, "title": "Dep", "provides": "API"}]
        formatted = format_dependencies(deps)
        assert "#1" in formatted
        assert "Provides" in formatted

    def test_format_references(self):
        """References should render as markdown list."""
        refs = [{"path": "README.md", "purpose": "Overview"}]
        formatted = format_references(refs)
        assert "README.md" in formatted


class TestWorkflows:
    """Integration tests for common workflows."""
    
    def test_full_subagent_workflow(self, runner):
        """Test complete SubAgent workflow: spawn → work → complete."""
        with runner.isolated_filesystem():
            # Setup repo
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True)
            
            # Initialize
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            
            # Spawn SubAgent (mock git worktree operations and notes)
            with patch("context_md.commands.subagent.subprocess.run") as mock_run, \
                 patch("context_md.state.State.set_branch_note", return_value=True):
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = runner.invoke(
                    cli,
                    [
                        "subagent",
                        "spawn",
                        "100",
                        "--role",
                        "engineer",
                        "--title",
                        "test-task",
                    ],
                )

                assert result.exit_code == 0
                assert "spawned successfully" in result.output

    def test_issue_to_context_generation(self, runner):
        """End-to-end: init → branch note → context generation."""
        with runner.isolated_filesystem():
            # Setup repo
            subprocess.run(["git", "init"], capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True, check=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True, check=True)

            # Minimal agent/skill files
            agents_dir = Path(".github") / "agents"
            skills_dir = Path(".github") / "skills" / "development" / "testing"
            agents_dir.mkdir(parents=True, exist_ok=True)
            skills_dir.mkdir(parents=True, exist_ok=True)
            (agents_dir / "engineer.agent.md").write_text("# Engineer")
            (skills_dir / "SKILL.md").write_text("# Testing Skill")

            # Initialize Context.md
            result = runner.invoke(cli, ["init", "--mode", "local"])
            assert result.exit_code == 0

            # Create issue branch and metadata
            subprocess.run(["git", "branch", "issue-101-test"], capture_output=True, check=True)

            state = State(Path.cwd())
            metadata = {
                "issue": 101,
                "type": "story",
                "labels": ["type:story", "testing"],
                "description": "Add test context generation",
                "references": [
                    {"path": "README.md", "purpose": "Project overview"}
                ],
            }
            assert state.set_branch_note("issue-101-test", metadata)

            # Generate context
            result = runner.invoke(cli, ["context", "generate", "101"])
            assert result.exit_code == 0

            output_path = Path(".agent-context") / "context-101.md"
            assert output_path.exists()
            content = output_path.read_text(encoding="utf-8")
            assert "Layer 1: System Context" in content
            assert "Layer 4: Retrieval Context" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
