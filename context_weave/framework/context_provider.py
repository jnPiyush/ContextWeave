"""
Context Provider for Agent Framework integration.

Injects ContextWeave's 4-layer context architecture into every
agent invocation via the Agent Framework's ContextProvider lifecycle:
- invoking() -- inject context BEFORE agent processes
- invoked() -- hook AFTER agent responds
"""

import logging
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class ContextWeaveProvider:
    """Injects ContextWeave's 4-layer context into Agent Framework agents.

    Before each agent invocation, this provider assembles:
    1. Role instructions (Layer 1: System Context)
    2. Enhanced prompt (Layer 2: User Prompt)
    3. Memory context (Layer 3: Memory)
    4. Skills content (Layer 4: Retrieval Context)

    Implements the ContextProvider protocol expected by Agent Framework.
    """

    def __init__(
        self,
        repo_root: Path,
        issue: int,
        role: str,
        issue_type: str = "story",
        labels: Optional[List[str]] = None,
    ):
        self.repo_root = repo_root
        self.issue = issue
        self.role = role
        self.issue_type = issue_type
        self.labels = labels or []

    async def invoking(self, *args: Any, **kwargs: Any) -> Any:
        """Called before each model invocation.

        Assembles the 4-layer context and returns it as additional
        instructions for the agent.

        Returns a Context object if the framework is available,
        otherwise returns the context string.
        """
        context_text = self._build_system_instructions()

        # Try to return a proper Context object
        try:
            from agent_framework import Context
            return Context(instructions=context_text)
        except ImportError:
            return context_text

    async def invoked(self, *args: Any, **kwargs: Any) -> None:
        """Called after model response.

        Memory recording is handled by MemoryRecordingMiddleware
        for cleaner separation of concerns.
        """

    async def thread_created(self, *args: Any, **kwargs: Any) -> None:
        """Called when a new thread is created."""

    async def __aenter__(self) -> "ContextWeaveProvider":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def _build_system_instructions(self) -> str:
        """Assemble the full system instructions from all 4 layers."""
        sections = []

        # Layer 1: System Context -- Role instructions
        try:
            from context_weave.commands.context import load_role_instructions
            role_instructions = load_role_instructions(self.repo_root, self.role)
            if role_instructions:
                sections.append(
                    "## Layer 1: System Context (Role Instructions)\n\n"
                    + role_instructions
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load role instructions: %s", e)

        # Layer 2: Enhanced prompt (handled by AgentFactory, skip here to avoid duplication)
        # The AgentFactory already injects the enhanced prompt into the agent's
        # system message. Adding it again here would duplicate.

        # Layer 3: Memory -- Lessons, sessions, metrics
        try:
            from context_weave.memory import Memory

            memory = Memory(self.repo_root)
            categories = [
                label.replace("type:", "") for label in self.labels if ":" in label
            ]
            if not categories:
                categories = [self.issue_type]

            memory_context = memory.get_memory_context(
                self.issue, self.issue_type, self.role, categories
            )
            if memory_context and memory_context != "_No memory context available yet._":
                sections.append(
                    "## Layer 3: Memory (Persistent Knowledge)\n\n"
                    + memory_context
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load memory context: %s", e)

        # Layer 4: Retrieval Context -- Skills
        try:
            from context_weave.commands.context import load_skills
            from context_weave.config import Config

            config = Config(self.repo_root)
            skill_numbers = config.get_skills_for_labels(self.labels)
            if skill_numbers:
                skills_content = load_skills(
                    self.repo_root, skill_numbers, verbose=False
                )
                if skills_content and skills_content != "No skills loaded.":
                    sections.append(
                        "## Layer 4: Retrieval Context (Skills)\n\n"
                        + skills_content
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load skills context: %s", e)

        return "\n\n---\n\n".join(sections) if sections else ""
