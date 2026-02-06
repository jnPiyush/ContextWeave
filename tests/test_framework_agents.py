"""Tests for context_md.framework.agents -- Agent Factory."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from context_md.framework.agents import (
    ROLE_FILE_MAP,
    AgentDefinition,
    AgentFactory,
    _parse_yaml_frontmatter,
)


class TestParseYamlFrontmatter:
    def test_simple_key_value(self):
        text = "name: TestAgent\ndescription: A test agent"
        result = _parse_yaml_frontmatter(text)
        assert result["name"] == "TestAgent"
        assert result["description"] == "A test agent"

    def test_list_values(self):
        text = "tools:\n  - tool_a\n  - tool_b\n  - tool_c"
        result = _parse_yaml_frontmatter(text)
        assert result["tools"] == ["tool_a", "tool_b", "tool_c"]

    def test_boolean_values(self):
        text = "infer: true\nenabled: false"
        result = _parse_yaml_frontmatter(text)
        assert result["infer"] is True
        assert result["enabled"] is False

    def test_quoted_values(self):
        text = "description: 'A quoted description'"
        result = _parse_yaml_frontmatter(text)
        assert result["description"] == "A quoted description"

    def test_empty_input(self):
        result = _parse_yaml_frontmatter("")
        assert result == {}

    def test_comments_ignored(self):
        text = "# This is a comment\nname: TestAgent"
        result = _parse_yaml_frontmatter(text)
        assert result["name"] == "TestAgent"


class TestAgentDefinition:
    def test_from_file(self, tmp_path):
        agent_file = tmp_path / "test.agent.md"
        agent_file.write_text("""---
name: TestEngineer
description: A test engineer agent
model: gpt-4o
tools:
  - read_file
  - run_command
---

# Test Engineer

You are a test engineer agent.
Follow best practices.
""")

        defn = AgentDefinition.from_file(agent_file)
        assert defn.name == "TestEngineer"
        assert defn.description == "A test engineer agent"
        assert defn.model == "gpt-4o"
        assert "read_file" in defn.tools
        assert "run_command" in defn.tools
        assert "test engineer agent" in defn.instructions.lower()

    def test_from_file_no_frontmatter(self, tmp_path):
        agent_file = tmp_path / "simple.agent.md"
        agent_file.write_text("# Simple Agent\n\nJust instructions.")

        defn = AgentDefinition.from_file(agent_file)
        assert defn.name == "simple.agent"  # Uses stem
        assert "Just instructions" in defn.instructions

    def test_from_file_with_extra_metadata(self, tmp_path):
        agent_file = tmp_path / "extra.agent.md"
        agent_file.write_text("""---
name: Extra
description: Extra agent
model: gpt-4o
infer: true
custom_field: custom_value
tools:
  - tool_a
---

Instructions here.
""")

        defn = AgentDefinition.from_file(agent_file)
        assert defn.extra_metadata.get("infer") is True
        assert defn.extra_metadata.get("custom_field") == "custom_value"


class TestAgentFactory:
    @pytest.fixture
    def setup_agents(self, tmp_path):
        """Create test agent definition files."""
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)

        (agents_dir / "engineer.agent.md").write_text("""---
name: Engineer
description: Software Engineer Agent
model: gpt-4o
tools:
  - read_file
  - run_command
---

# Engineer

You are a software engineer.
""")

        (agents_dir / "product-manager.agent.md").write_text("""---
name: ProductManager
description: PM Agent
model: gpt-4o
tools:
  - read_file
---

# PM

You are a product manager.
""")
        return tmp_path

    def test_load_agent_definitions(self, setup_agents):
        factory = AgentFactory(
            repo_root=setup_agents,
            llm_config=MagicMock(),
            tool_registry=MagicMock(),
        )
        definitions = factory.load_agent_definitions()
        assert "engineer" in definitions
        assert "pm" in definitions
        assert definitions["engineer"].name == "Engineer"

    def test_load_definitions_cached(self, setup_agents):
        factory = AgentFactory(
            repo_root=setup_agents,
            llm_config=MagicMock(),
            tool_registry=MagicMock(),
        )
        defs1 = factory.load_agent_definitions()
        defs2 = factory.load_agent_definitions()
        assert defs1 is defs2  # Same object (cached)

    def test_load_definitions_missing_dir(self, tmp_path):
        factory = AgentFactory(
            repo_root=tmp_path,
            llm_config=MagicMock(),
            tool_registry=MagicMock(),
        )
        definitions = factory.load_agent_definitions()
        assert definitions == {}

    @patch("context_md.framework.config.get_chat_client")
    def test_create_agent(self, mock_client, setup_agents):
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = [MagicMock()]

        mock_chat_agent_cls = MagicMock()
        mock_agent_framework = MagicMock(ChatAgent=mock_chat_agent_cls)

        factory = AgentFactory(
            repo_root=setup_agents,
            llm_config=MagicMock(),
            tool_registry=mock_registry,
        )

        with patch.dict(sys.modules, {"agent_framework": mock_agent_framework}):
            agent = factory.create_agent("engineer")
            mock_chat_agent_cls.assert_called_once()
            call_kwargs = mock_chat_agent_cls.call_args[1]
            assert call_kwargs["name"] == "engineer"
            assert "instructions" in call_kwargs

    def test_filename_to_role(self, tmp_path):
        factory = AgentFactory(tmp_path, MagicMock(), MagicMock())
        assert factory._filename_to_role("product-manager.agent.md") == "pm"
        assert factory._filename_to_role("engineer.agent.md") == "engineer"
        assert factory._filename_to_role("ux-designer.agent.md") == "ux"

    def test_role_to_filename(self):
        assert AgentFactory.role_to_filename("pm") == "product-manager.agent.md"
        assert AgentFactory.role_to_filename("engineer") == "engineer.agent.md"
        assert AgentFactory.role_to_filename("ux") == "ux-designer.agent.md"
        assert AgentFactory.role_to_filename("custom") == "custom.agent.md"


class TestRoleFileMap:
    def test_all_standard_roles_mapped(self):
        expected = ["pm", "architect", "engineer", "reviewer", "ux", "devops", "agentx"]
        for role in expected:
            assert role in ROLE_FILE_MAP
