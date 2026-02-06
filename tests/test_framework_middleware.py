"""Tests for context_weave.framework.middleware -- Middleware stack."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_weave.framework.middleware import (
    MemoryRecordingMiddleware,
    SecurityMiddleware,
    TokenBudgetMiddleware,
    ValidationMiddleware,
    create_middleware_stack,
)


class TestSecurityMiddleware:
    @pytest.mark.asyncio
    async def test_passes_safe_request(self, tmp_path):
        middleware = SecurityMiddleware(tmp_path, "engineer")
        context = MagicMock(spec=[])  # No tool_call attribute
        next_handler = AsyncMock(return_value="ok")

        result = await middleware.process(context, next_handler)
        assert result == "ok"
        next_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_blocks_dangerous_command(self, tmp_path):
        # Setup security config
        security_dir = tmp_path / ".github" / "security"
        security_dir.mkdir(parents=True)

        middleware = SecurityMiddleware(tmp_path, "engineer")

        # Simulate a tool call with a blocked command
        tool_call = MagicMock()
        tool_call.name = "run_command"
        tool_call.arguments = {"command": "rm -rf /"}

        context = MagicMock()
        context.tool_call = tool_call

        next_handler = AsyncMock()

        with pytest.raises(ValueError, match="blocked"):
            await middleware.process(context, next_handler)

        next_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_safe_command(self, tmp_path):
        security_dir = tmp_path / ".github" / "security"
        security_dir.mkdir(parents=True)

        middleware = SecurityMiddleware(tmp_path, "engineer")

        tool_call = MagicMock()
        tool_call.name = "run_command"
        tool_call.arguments = {"command": "git status"}

        context = MagicMock()
        context.tool_call = tool_call

        next_handler = AsyncMock(return_value="ok")
        result = await middleware.process(context, next_handler)
        assert result == "ok"


class TestMemoryRecordingMiddleware:
    @pytest.mark.asyncio
    async def test_records_success(self, tmp_path):
        (tmp_path / ".context-weave").mkdir(parents=True)

        middleware = MemoryRecordingMiddleware(tmp_path, issue=1, role="engineer")
        context = MagicMock()
        next_handler = AsyncMock(return_value="completed")

        result = await middleware.process(context, next_handler)
        assert result == "completed"

        # Check memory was updated
        memory_file = tmp_path / ".context-weave" / "memory.json"
        if memory_file.exists():
            data = json.loads(memory_file.read_text())
            executions = data.get("executions", [])
            assert len(executions) >= 1
            assert executions[-1]["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_records_failure(self, tmp_path):
        (tmp_path / ".context-weave").mkdir(parents=True)

        middleware = MemoryRecordingMiddleware(tmp_path, issue=1, role="engineer")
        context = MagicMock()
        next_handler = AsyncMock(side_effect=RuntimeError("Agent crashed"))

        with pytest.raises(RuntimeError, match="crashed"):
            await middleware.process(context, next_handler)

        # Check failure was recorded
        memory_file = tmp_path / ".context-weave" / "memory.json"
        if memory_file.exists():
            data = json.loads(memory_file.read_text())
            executions = data.get("executions", [])
            assert len(executions) >= 1
            assert executions[-1]["outcome"] == "failure"


class TestValidationMiddleware:
    @pytest.mark.asyncio
    async def test_passes_through(self, tmp_path):
        middleware = ValidationMiddleware(tmp_path, issue=1, role="engineer")
        context = MagicMock()
        next_handler = AsyncMock(return_value="output")

        result = await middleware.process(context, next_handler)
        assert result == "output"

    @pytest.mark.asyncio
    async def test_checks_artifacts(self, tmp_path):
        """Validation logs missing artifacts but doesn't block."""
        middleware = ValidationMiddleware(tmp_path, issue=42, role="pm")
        context = MagicMock()
        next_handler = AsyncMock(return_value="prd output")

        # PM should check for PRD file
        result = await middleware.process(context, next_handler)
        assert result == "prd output"  # Doesn't block

    def test_role_artifacts_defined(self):
        assert "pm" in ValidationMiddleware.ROLE_ARTIFACTS
        assert "engineer" in ValidationMiddleware.ROLE_ARTIFACTS
        assert "reviewer" in ValidationMiddleware.ROLE_ARTIFACTS


class TestTokenBudgetMiddleware:
    @pytest.mark.asyncio
    async def test_allows_within_budget(self):
        middleware = TokenBudgetMiddleware(max_tokens_per_call=8192, max_tokens_per_workflow=100000)
        context = MagicMock()
        next_handler = AsyncMock(return_value=MagicMock(spec=[]))

        result = await middleware.process(context, next_handler)
        assert result is not None

    @pytest.mark.asyncio
    async def test_blocks_when_budget_exceeded(self):
        middleware = TokenBudgetMiddleware(max_tokens_per_workflow=100)
        middleware.total_tokens_used = 200  # Already exceeded

        context = MagicMock()
        next_handler = AsyncMock()

        with pytest.raises(ValueError, match="Token budget exceeded"):
            await middleware.process(context, next_handler)

        next_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self):
        middleware = TokenBudgetMiddleware()

        usage = MagicMock()
        usage.total_tokens = 500
        response = MagicMock()
        response.usage = usage

        context = MagicMock()
        next_handler = AsyncMock(return_value=response)

        await middleware.process(context, next_handler)
        assert middleware.total_tokens_used == 500


class TestCreateMiddlewareStack:
    def test_creates_four_middleware(self, tmp_path):
        stack = create_middleware_stack(tmp_path, issue=1, role="engineer")
        assert len(stack) == 4
        assert isinstance(stack[0], SecurityMiddleware)
        assert isinstance(stack[1], MemoryRecordingMiddleware)
        assert isinstance(stack[2], ValidationMiddleware)
        assert isinstance(stack[3], TokenBudgetMiddleware)

    def test_custom_token_limits(self, tmp_path):
        stack = create_middleware_stack(
            tmp_path, issue=1, role="pm",
            max_tokens_per_call=4096,
            max_tokens_per_workflow=50000,
        )
        budget = stack[3]
        assert isinstance(budget, TokenBudgetMiddleware)
        assert budget.max_tokens_per_call == 4096
        assert budget.max_tokens_per_workflow == 50000
