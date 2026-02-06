"""Tests for context_md.framework.tools -- Tool Registry."""


import pytest

from context_md.framework.tools import ROLE_TOOLS, ToolRegistry


class TestToolRegistry:
    def test_init(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        assert registry.repo_root == tmp_path

    def test_get_all_tools(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tools = registry.get_all_tools()
        assert len(tools) > 0
        # All tools should be callable
        for tool in tools:
            assert callable(tool)

    def test_get_tools_for_role(self, tmp_path):
        registry = ToolRegistry(tmp_path)

        # Engineer gets run_command and create_file
        eng_tools = registry.get_tools_for_role("engineer")
        eng_names = [t.__name__ for t in eng_tools]
        assert "run_command" in eng_names
        assert "create_file" in eng_names

        # PM does not get run_command
        pm_tools = registry.get_tools_for_role("pm")
        pm_names = [t.__name__ for t in pm_tools]
        assert "run_command" not in pm_names

    def test_get_tools_unknown_role(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        # Unknown role defaults to engineer tools
        tools = registry.get_tools_for_role("unknown_role")
        assert len(tools) > 0

    def test_get_tool_by_name(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("git_status")
        assert tool is not None
        assert callable(tool)

    def test_get_tool_by_name_unknown(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("nonexistent_tool")
        assert tool is None


class TestToolFunctions:
    @pytest.mark.asyncio
    async def test_git_status(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("git_status")
        result = await tool()
        # tmp_path is not a git repo, so we get an error or empty output
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("read_file")
        result = await tool("test.txt")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("read_file")
        result = await tool("nonexistent.txt")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_list_directory(self, tmp_path):
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "subdir").mkdir()

        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("list_directory")
        result = await tool(".")
        assert "file1.txt" in result
        assert "subdir" in result

    @pytest.mark.asyncio
    async def test_create_file(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("create_file")
        result = await tool("new_file.txt", "file content here")
        assert "created" in result.lower()
        assert (tmp_path / "new_file.txt").read_text() == "file content here"

    @pytest.mark.asyncio
    async def test_create_file_nested(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("create_file")
        result = await tool("sub/dir/file.txt", "nested content")
        assert "created" in result.lower()
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "nested content"

    @pytest.mark.asyncio
    async def test_search_code(self, tmp_path):
        # Create a git repo with a searchable file
        (tmp_path / ".git").mkdir()
        (tmp_path / "code.py").write_text("def hello_world():\n    pass\n")

        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("search_code")
        result = await tool("hello_world")
        # May fail if not a proper git repo, just check it returns string
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_context_no_file(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("get_context")
        result = await tool(999)
        assert "no context file" in result.lower() or "generate" in result.lower()

    @pytest.mark.asyncio
    async def test_get_memory_context(self, tmp_path):
        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("get_memory_context")
        result = await tool(1, "story", "engineer")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_record_execution(self, tmp_path):
        (tmp_path / ".agent-context").mkdir()

        registry = ToolRegistry(tmp_path)
        tool = registry.get_tool_by_name("record_execution")
        result = await tool(1, "engineer", "test_action", "success")
        assert "recorded" in result.lower()


class TestRoleTools:
    def test_all_roles_defined(self):
        expected_roles = ["pm", "architect", "engineer", "reviewer", "ux"]
        for role in expected_roles:
            assert role in ROLE_TOOLS

    def test_engineer_has_run_command(self):
        assert "run_command" in ROLE_TOOLS["engineer"]

    def test_pm_no_run_command(self):
        assert "run_command" not in ROLE_TOOLS["pm"]

    def test_all_roles_have_common_tools(self):
        common = ["git_status", "read_file", "search_code", "get_memory_context"]
        for role, tools in ROLE_TOOLS.items():
            for tool_name in common:
                assert tool_name in tools, f"{role} missing {tool_name}"
