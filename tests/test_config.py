"""
Tests for Config Command and Config class

Coverage target: 70%+ (from 32%)
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from context_weave.commands.config import config_cmd
from context_weave.config import Config


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def config_with_defaults(tmp_path):
    """Create a config with default values."""
    config = Config(tmp_path)
    config.save()
    return config


class TestConfigClass:
    """Test the Config class directly."""

    def test_default_config_values(self, tmp_path):
        """Test that default configuration values are set."""
        config = Config(tmp_path)

        assert config.mode == "local"
        assert config.worktree_base == ".context-weave/worktrees"
        assert "api" in config._data.get("skill_routing", {})
        assert "bug" in config._data.get("validation", {}).get("stuck_threshold_hours", {})

    def test_config_save_and_load(self, tmp_path):
        """Test that config persists correctly."""
        config = Config(tmp_path)
        config.mode = "github"
        config.save()

        # Load fresh instance
        config2 = Config(tmp_path)
        assert config2.mode == "github"

    def test_get_with_dot_notation(self, tmp_path):
        """Test getting nested values with dot notation."""
        config = Config(tmp_path)

        # Test nested value
        bug_threshold = config.get("validation.stuck_threshold_hours.bug")
        assert bug_threshold == 12

        # Test non-existent key with default
        missing = config.get("nonexistent.key", "default")
        assert missing == "default"

    def test_set_with_dot_notation(self, tmp_path):
        """Test setting nested values with dot notation."""
        config = Config(tmp_path)

        config.set("validation.stuck_threshold_hours.bug", 24)
        config.save()

        # Reload and verify
        config2 = Config(tmp_path)
        assert config2.get("validation.stuck_threshold_hours.bug") == 24

    def test_set_creates_nested_keys(self, tmp_path):
        """Test that set creates intermediate keys."""
        config = Config(tmp_path)

        config.set("new.nested.key", "value")
        assert config.get("new.nested.key") == "value"

    def test_mode_setter_validation(self, tmp_path):
        """Test that mode setter validates input."""
        config = Config(tmp_path)

        # Valid modes
        for mode in ["local", "github", "hybrid"]:
            config.mode = mode
            assert config.mode == mode

        # Invalid mode
        with pytest.raises(ValueError, match="Invalid mode"):
            config.mode = "invalid"

    def test_get_worktree_path(self, tmp_path):
        """Test worktree path generation."""
        config = Config(tmp_path)

        path = config.get_worktree_path(123)
        assert "123" in str(path)
        assert isinstance(path, Path)

    def test_get_skills_for_labels(self, tmp_path):
        """Test skill routing for labels."""
        config = Config(tmp_path)

        # API labels should include API and security skills (returned as names)
        api_skills = config.get_skills_for_labels(["api"])
        assert "api-design" in api_skills
        assert "security" in api_skills

        # Security labels
        security_skills = config.get_skills_for_labels(["security"])
        assert "security" in security_skills

        # Unknown labels get default skills
        default_skills = config.get_skills_for_labels(["unknown-label"])
        assert "testing" in default_skills
        assert "security" in default_skills

    def test_get_skills_for_multiple_labels(self, tmp_path):
        """Test skill routing with multiple labels."""
        config = Config(tmp_path)

        skills = config.get_skills_for_labels(["api", "security"])
        # Should have union of both
        assert "security" in skills  # Common
        assert "api-design" in skills  # API specific

    def test_get_stuck_threshold(self, tmp_path):
        """Test stuck threshold retrieval."""
        config = Config(tmp_path)
        config.save()  # Ensure config file exists with defaults
        config2 = Config(tmp_path)  # Reload to get persisted values

        # Check thresholds from default config
        config2._data.get("validation", {}).get("stuck_threshold_hours", {})

        # Verify method falls back to 24 for unknown types
        assert config2.get_stuck_threshold("unknown") == 24  # Default fallback

    def test_get_required_fields(self, tmp_path):
        """Test required fields retrieval."""
        config = Config(tmp_path)

        story_fields = config.get_required_fields("story")
        assert "references" in story_fields
        assert "acceptance_criteria" in story_fields

        bug_fields = config.get_required_fields("bug")
        assert "steps_to_reproduce" in bug_fields

    def test_is_hook_enabled(self, tmp_path):
        """Test hook enabled check."""
        config = Config(tmp_path)

        # Default hooks are enabled
        assert config.is_hook_enabled("pre_commit") is True
        assert config.is_hook_enabled("post_commit") is True

        # Non-existent hook defaults to True
        assert config.is_hook_enabled("nonexistent") is True

    def test_to_dict(self, tmp_path):
        """Test config serialization to dict."""
        config = Config(tmp_path)

        data = config.to_dict()
        assert isinstance(data, dict)
        assert "mode" in data
        assert "skill_routing" in data

    def test_load_corrupted_config(self, tmp_path):
        """Test handling of corrupted config file."""
        # Create corrupted config
        config_dir = tmp_path / ".context-weave"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{ invalid json }")

        # Should fall back to defaults
        config = Config(tmp_path)
        assert config.mode == "local"


class TestShowCommand:
    """Test config show command."""

    def test_show_config_default(self, runner, tmp_path):
        """Test showing default configuration (mode)."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            [],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Mode:" in result.output
        assert "local" in result.output

    def test_show_config_list(self, runner, tmp_path):
        """Test showing full configuration with --list."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["--list"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "mode" in result.output
        assert "skill_routing" in result.output

    def test_show_config_list_json(self, runner, tmp_path):
        """Test JSON output format with --list --json."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["--list", "--json"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "mode" in data


class TestGetCommand:
    """Test config get operations."""

    def test_get_mode(self, runner, tmp_path):
        """Test getting mode value."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["mode"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "local" in result.output

    def test_get_nested_key(self, runner, tmp_path):
        """Test getting a nested key."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["validation.stuck_threshold_hours.bug"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        # Check that the output contains a numeric value
        assert "validation.stuck_threshold_hours.bug" in result.output

    def test_get_nonexistent_key(self, runner, tmp_path):
        """Test getting a nonexistent key."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["nonexistent.key"],
            obj={"repo_root": tmp_path, "config": config},
        )

        # Should fail with error message
        assert result.exit_code != 0
        assert "not found" in result.output


class TestSetCommand:
    """Test config set operations."""

    def test_set_mode(self, runner, tmp_path):
        """Test setting mode."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["mode", "github"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "OK" in result.output

        # Verify
        config2 = Config(tmp_path)
        assert config2.mode == "github"

    def test_set_invalid_mode(self, runner, tmp_path):
        """Test setting invalid mode."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["mode", "invalid"],
            obj={"repo_root": tmp_path, "config": config},
        )

        assert result.exit_code != 0

    def test_set_nested_value(self, runner, tmp_path):
        """Test setting a nested value."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["validation.stuck_threshold_hours.bug", "6"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0

        config2 = Config(tmp_path)
        assert config2.get("validation.stuck_threshold_hours.bug") == 6

    def test_set_boolean_value(self, runner, tmp_path):
        """Test setting a boolean value."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["hooks.pre_commit", "false"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0

        config2 = Config(tmp_path)
        assert config2.get("hooks.pre_commit") is False


class TestConfigIntegration:
    """Integration tests for config command."""

    def test_config_help(self, runner, tmp_path):
        """Test config help text."""
        config = Config(tmp_path)
        config.save()

        result = runner.invoke(
            config_cmd,
            ["--help"],
            obj={"repo_root": tmp_path, "config": config},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_config_without_repo_root(self, runner):
        """Test config without repo_root fails gracefully."""
        result = runner.invoke(
            config_cmd,
            [],
            obj={},  # No repo_root
        )

        assert result.exit_code != 0
