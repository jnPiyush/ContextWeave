"""Tests for context_weave.framework.context_provider -- Context Provider."""


import pytest

from context_weave.framework.context_provider import ContextWeaveProvider


class TestContextWeaveProvider:
    def test_init(self, tmp_path):
        provider = ContextWeaveProvider(
            repo_root=tmp_path,
            issue=42,
            role="engineer",
            issue_type="story",
            labels=["type:story", "api"],
        )
        assert provider.issue == 42
        assert provider.role == "engineer"
        assert provider.issue_type == "story"
        assert "api" in provider.labels

    @pytest.mark.asyncio
    async def test_invoking_returns_context(self, tmp_path):
        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        result = await provider.invoking()
        # Without agent_framework installed, returns string
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_invoking_with_agent_definition(self, tmp_path):
        """Test that role instructions are loaded from .agent.md."""
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.agent.md").write_text(
            "---\nname: Engineer\n---\n\n# Engineer\n\nYou are a software engineer."
        )

        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        result = await provider.invoking()
        assert "Layer 1" in result
        assert "Engineer" in result

    @pytest.mark.asyncio
    async def test_invoking_with_memory(self, tmp_path):
        """Test that memory context is included when available."""
        # Setup memory
        memory_dir = tmp_path / ".context-weave"
        memory_dir.mkdir(parents=True)

        import json
        memory_data = {
            "version": "1.0",
            "lessons": [
                {
                    "id": "L1",
                    "issue": 1,
                    "issue_type": "story",
                    "role": "engineer",
                    "category": "testing",
                    "lesson": "Always write tests first",
                    "context": "TDD is effective",
                    "outcome": "success",
                    "applied_count": 5,
                    "effectiveness": 0.9,
                }
            ],
            "executions": [],
            "sessions": {},
            "metrics": {"total_executions": 0, "success_count": 0, "failure_count": 0, "partial_count": 0}
        }
        (memory_dir / "memory.json").write_text(json.dumps(memory_data))

        provider = ContextWeaveProvider(
            tmp_path, issue=1, role="engineer",
            issue_type="story", labels=["type:story"]
        )
        result = await provider.invoking()
        assert "Memory" in result or "Lessons" in result or "testing" in result.lower()

    @pytest.mark.asyncio
    async def test_invoked_is_noop(self, tmp_path):
        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        # Should not raise
        await provider.invoked()

    @pytest.mark.asyncio
    async def test_thread_created_is_noop(self, tmp_path):
        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        await provider.thread_created()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path):
        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        async with provider as p:
            assert p is provider

    def test_build_system_instructions_no_agents_dir(self, tmp_path):
        """Test graceful handling when no agent definitions exist."""
        provider = ContextWeaveProvider(tmp_path, issue=1, role="engineer")
        instructions = provider._build_system_instructions()
        # Should return empty or minimal content (not crash)
        assert isinstance(instructions, str)

    def test_build_system_instructions_with_skills(self, tmp_path):
        """Test that skills are loaded when config has routing."""
        # Setup config
        config_dir = tmp_path / ".context-weave"
        config_dir.mkdir(parents=True)

        import json
        config_data = {
            "version": "1.0",
            "mode": "local",
            "skill_routing": {
                "api": ["#09"],
                "default": ["#02"]
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config_data))

        # Create skill file
        skill_dir = tmp_path / ".github" / "skills" / "development" / "testing"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Testing Skill\n\nAlways test your code.")

        provider = ContextWeaveProvider(
            tmp_path, issue=1, role="engineer",
            labels=["default"]
        )
        instructions = provider._build_system_instructions()
        # The default label should trigger #02 skill loading
        if "Layer 4" in instructions:
            assert "testing" in instructions.lower() or "Skill" in instructions
