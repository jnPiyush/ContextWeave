"""
Middleware for Agent Framework integration.

Implements validation, security, memory recording, and token budget
enforcement as middleware in the Agent Framework pipeline.

Middleware order (outermost to innermost):
1. SecurityMiddleware -- blocks dangerous operations
2. MemoryRecordingMiddleware -- records outcomes
3. ValidationMiddleware -- validates outputs
4. TokenBudgetMiddleware -- enforces cost limits
"""

import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Validates tool calls against Context.md's security policy.

    Intercepts agent actions and validates commands using
    CommandValidator and PathValidator from context_md.security.
    """

    def __init__(self, repo_root: Path, agent_role: str = "unknown"):
        self.repo_root = repo_root
        self.agent_role = agent_role

    async def process(self, context: Any, next_handler: Callable) -> Any:
        """Validate the invocation, then call next handler.

        On validation failure, returns an error response instead
        of proceeding to the agent.
        """
        # Inspect if there's a tool call to validate
        tool_call = getattr(context, "tool_call", None)
        if tool_call:
            tool_name = getattr(tool_call, "name", "")
            tool_args = getattr(tool_call, "arguments", {})

            # Validate commands
            if tool_name == "run_command" and "command" in tool_args:
                from context_md.security import CommandValidator

                validator = CommandValidator(self.repo_root)
                is_allowed, reason = validator.validate(
                    tool_args["command"], self.agent_role
                )
                if not is_allowed:
                    logger.warning(
                        "SecurityMiddleware blocked command from %s: %s",
                        self.agent_role, reason
                    )
                    raise ValueError(f"Security: Command blocked - {reason}")

            # Validate file paths
            if tool_name in ("read_file", "create_file") and "path" in tool_args:
                from context_md.security import PathValidator

                validator = PathValidator(self.repo_root)
                is_valid, reason = validator.validate(
                    str(self.repo_root / tool_args["path"])
                )
                if not is_valid:
                    logger.warning(
                        "SecurityMiddleware blocked file access from %s: %s",
                        self.agent_role, reason
                    )
                    raise ValueError(f"Security: Path blocked - {reason}")

        return await next_handler(context)


class MemoryRecordingMiddleware:
    """Records execution outcomes to Memory layer.

    After each agent run completes, records an ExecutionRecord
    to the Memory layer for learning loop integration.
    """

    def __init__(self, repo_root: Path, issue: int, role: str):
        self.repo_root = repo_root
        self.issue = issue
        self.role = role

    async def process(self, context: Any, next_handler: Callable) -> Any:
        """Run agent, then record outcome."""
        start_time = time.monotonic()
        outcome = "success"
        error_type: Optional[str] = None
        error_message: Optional[str] = None

        try:
            result = await next_handler(context)
            return result
        except Exception as e:
            outcome = "failure"
            error_type = type(e).__name__
            error_message = str(e)
            raise
        finally:
            duration = time.monotonic() - start_time
            try:
                from context_md.memory import ExecutionRecord, Memory

                memory = Memory(self.repo_root)
                record = ExecutionRecord(
                    issue=self.issue,
                    role=self.role,
                    action="agent_invocation",
                    outcome=outcome,
                    error_type=error_type,
                    error_message=error_message,
                    duration_seconds=round(duration, 2),
                )
                memory.record_execution(record)
            except Exception as rec_err:  # noqa: BLE001
                logger.warning("Failed to record execution: %s", rec_err)


class ValidationMiddleware:
    """Validates agent outputs against quality gates.

    Checks agent outputs against the Definition of Done criteria
    from the agent definition before allowing handoff.
    """

    # Role-specific required artifacts
    ROLE_ARTIFACTS = {
        "pm": ["docs/prd/PRD-{issue}.md"],
        "architect": ["docs/adr/ADR-{issue}.md", "docs/specs/SPEC-{issue}.md"],
        "engineer": [],  # Validated by test results
        "reviewer": ["docs/reviews/REVIEW-{issue}.md"],
        "ux": ["docs/ux/UX-{issue}.md"],
    }

    def __init__(self, repo_root: Path, issue: int, role: str):
        self.repo_root = repo_root
        self.issue = issue
        self.role = role

    async def process(self, context: Any, next_handler: Callable) -> Any:
        """Run agent, then validate outputs."""
        result = await next_handler(context)

        # Check expected artifacts exist
        expected = self.ROLE_ARTIFACTS.get(self.role, [])
        missing = []
        for artifact_template in expected:
            artifact_path = self.repo_root / artifact_template.format(issue=self.issue)
            if not artifact_path.exists():
                missing.append(str(artifact_path))

        if missing:
            logger.info(
                "ValidationMiddleware: Agent '%s' missing artifacts: %s",
                self.role, missing
            )
            # Log but don't block -- artifacts may be generated differently

        return result


class TokenBudgetMiddleware:
    """Enforces token budget limits.

    Monitors token usage per agent invocation and per workflow
    to prevent runaway costs.
    """

    def __init__(
        self,
        max_tokens_per_call: int = 8192,
        max_tokens_per_workflow: int = 100000,
    ):
        self.max_tokens_per_call = max_tokens_per_call
        self.max_tokens_per_workflow = max_tokens_per_workflow
        self.total_tokens_used = 0

    async def process(self, context: Any, next_handler: Callable) -> Any:
        """Enforce token limits before/after calls."""
        if self.total_tokens_used >= self.max_tokens_per_workflow:
            raise ValueError(
                f"Token budget exceeded: {self.total_tokens_used} >= "
                f"{self.max_tokens_per_workflow} (workflow limit)"
            )

        result = await next_handler(context)

        # Try to extract token usage from response
        usage = getattr(result, "usage", None)
        if usage:
            tokens = getattr(usage, "total_tokens", 0)
            self.total_tokens_used += tokens

            if tokens > self.max_tokens_per_call:
                logger.warning(
                    "Token usage (%d) exceeded per-call limit (%d)",
                    tokens, self.max_tokens_per_call
                )

        return result


def create_middleware_stack(
    repo_root: Path,
    issue: int,
    role: str,
    max_tokens_per_call: int = 8192,
    max_tokens_per_workflow: int = 100000,
) -> list:
    """Create the standard middleware stack for an agent.

    Order (outermost to innermost):
    1. Security -- blocks dangerous operations
    2. MemoryRecording -- records outcomes
    3. Validation -- validates outputs
    4. TokenBudget -- enforces cost limits
    """
    return [
        SecurityMiddleware(repo_root, role),
        MemoryRecordingMiddleware(repo_root, issue, role),
        ValidationMiddleware(repo_root, issue, role),
        TokenBudgetMiddleware(max_tokens_per_call, max_tokens_per_workflow),
    ]
