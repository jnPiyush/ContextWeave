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


@pytest.fixture
def temp_git_repo():
    """Create a temporary Git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_dir = Path(temp_dir) / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True)
    
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
        subprocess.run(["git", "branch", "issue-100-test"], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "branch", "issue-200-another"], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "branch", "feature-xyz"], cwd=temp_git_repo, capture_output=True)
        
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
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True)
            
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
        """Test status when not initialized."""
        with runner.isolated_filesystem():
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True)
            
            result = runner.invoke(cli, ["status"])
            assert "not initialized" in result.output.lower() or "run: context-md init" in result.output.lower()


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
            
            # Spawn SubAgent
            result = runner.invoke(cli, ["subagent", "spawn", "100", "--role", "engineer", "--title", "test-task"])
            assert result.exit_code == 0
            assert "spawned successfully" in result.output
            
            # List SubAgents
            result = runner.invoke(cli, ["subagent", "list"])
            assert result.exit_code == 0
            assert "100" in result.output
            
            # Generate context
            result = runner.invoke(cli, ["context", "generate", "100"])
            assert result.exit_code == 0
            assert Path(".agent-context/context-100.md").exists()
            
            # Status
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "100" in result.output
            
            # Complete SubAgent
            result = runner.invoke(cli, ["subagent", "complete", "100", "--force"])
            assert result.exit_code == 0
            assert "completed" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
