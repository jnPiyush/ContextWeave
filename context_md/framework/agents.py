"""
Agent Factory for Agent Framework integration.

Parses .agent.md files (YAML frontmatter + markdown) and creates
ChatAgent instances configured with Context.md's enhanced prompts,
role-filtered tools, context providers, and middleware.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Mapping from role shorthand to .agent.md filename
ROLE_FILE_MAP: Dict[str, str] = {
    "pm": "product-manager.agent.md",
    "architect": "architect.agent.md",
    "engineer": "engineer.agent.md",
    "reviewer": "reviewer.agent.md",
    "ux": "ux-designer.agent.md",
    "devops": "devops-engineer.agent.md",
    "agentx": "agent-x.agent.md",
}


def _parse_yaml_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from a string without requiring pyyaml.

    Handles the subset of YAML used in .agent.md files:
    simple key-value pairs and lists.
    """
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item under current key
        if stripped.startswith("- ") and current_key is not None:
            if not isinstance(result[current_key], list):
                result[current_key] = []
            result[current_key].append(stripped[2:].strip())
            continue

        # Key: value pair
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", stripped)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            current_key = key

            if not value:
                # Value will be a list (next lines are list items)
                result[key] = []
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            elif value.startswith("'") and value.endswith("'"):
                result[key] = value[1:-1]
            elif value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            else:
                result[key] = value

    return result


@dataclass
class AgentDefinition:
    """Parsed agent definition from a .agent.md file."""

    name: str
    description: str
    model: str
    tools: List[str]
    instructions: str  # Markdown body
    file_path: Path
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, file_path: Path) -> "AgentDefinition":
        """Parse an .agent.md file into an AgentDefinition.

        Extracts YAML frontmatter (between --- markers) for metadata
        and the markdown body as instructions.
        """
        content = file_path.read_text(encoding="utf-8")

        # Split frontmatter from body
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            body = parts[2].strip()
        else:
            # No frontmatter found
            frontmatter_text = ""
            body = content

        # Try pyyaml first, fall back to simple parser
        try:
            import yaml
            metadata = yaml.safe_load(frontmatter_text) or {}
        except ImportError:
            metadata = _parse_yaml_frontmatter(frontmatter_text)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to parse YAML in %s, using simple parser", file_path)
            metadata = _parse_yaml_frontmatter(frontmatter_text)

        return cls(
            name=metadata.get("name", file_path.stem),
            description=metadata.get("description", ""),
            model=metadata.get("model", ""),
            tools=metadata.get("tools", []),
            instructions=body,
            file_path=file_path,
            extra_metadata={
                k: v for k, v in metadata.items()
                if k not in ("name", "description", "model", "tools")
            },
        )


class AgentFactory:
    """Creates ChatAgent instances from AgentDefinition objects.

    Bridges Context.md agent definitions with the Agent Framework SDK.
    """

    def __init__(
        self,
        repo_root: Path,
        llm_config: Any,
        tool_registry: Any,
        context_provider: Optional[Any] = None,
        middleware: Optional[list] = None,
    ):
        self.repo_root = repo_root
        self.llm_config = llm_config
        self.tool_registry = tool_registry
        self.context_provider = context_provider
        self.middleware = middleware or []
        self._definitions: Optional[Dict[str, AgentDefinition]] = None

    def load_agent_definitions(self) -> Dict[str, AgentDefinition]:
        """Load all agent definitions from .github/agents/*.agent.md."""
        if self._definitions is not None:
            return self._definitions

        agents_dir = self.repo_root / ".github" / "agents"
        self._definitions = {}

        if not agents_dir.exists():
            logger.warning("Agents directory not found: %s", agents_dir)
            return self._definitions

        for agent_file in agents_dir.glob("*.agent.md"):
            try:
                defn = AgentDefinition.from_file(agent_file)
                # Map filename to role shorthand
                role = self._filename_to_role(agent_file.name)
                self._definitions[role] = defn
                logger.debug("Loaded agent definition: %s -> %s", role, defn.name)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to load agent definition %s: %s", agent_file, e)

        return self._definitions

    def create_agent(
        self,
        role: str,
        issue: Optional[int] = None,
        issue_type: str = "story",
        labels: Optional[List[str]] = None,
        additional_instructions: Optional[str] = None,
    ) -> Any:
        """Create a ChatAgent for a specific role.

        Combines agent definition instructions with Context.md's
        enhanced prompt system, role-filtered tools, and middleware.
        """
        from context_md.framework.config import get_chat_client
        from context_md.prompt import PromptEngineer

        definitions = self.load_agent_definitions()
        defn = definitions.get(role)

        # Build system message
        if defn:
            system_message = defn.instructions
        else:
            system_message = f"You are a {role.title()} agent."

        # Enhance with PromptEngineer if we have issue context
        if issue is not None:
            pe = PromptEngineer()
            enhanced = pe.enhance_prompt(
                raw_prompt=additional_instructions or f"Work on issue #{issue}",
                role=role,
                issue_number=issue,
                issue_type=issue_type,
                labels=labels or [],
            )
            system_message += "\n\n---\n\n" + enhanced.to_markdown()

        if additional_instructions and issue is None:
            system_message += f"\n\n---\n\n{additional_instructions}"

        # Get role-filtered tools
        tools = self.tool_registry.get_tools_for_role(role)

        # Create the ChatAgent
        try:
            from agent_framework import ChatAgent

            chat_client = get_chat_client(self.llm_config)

            agent_kwargs: Dict[str, Any] = {
                "name": role,
                "chat_client": chat_client,
                "instructions": system_message,
                "tools": tools,
            }

            if defn:
                agent_kwargs["description"] = defn.description

            if self.context_provider:
                agent_kwargs["context_provider"] = self.context_provider

            if self.middleware:
                agent_kwargs["middleware"] = self.middleware

            return ChatAgent(**agent_kwargs)

        except ImportError:
            raise ImportError(
                "Agent Framework is required to create agents. "
                "Install with: pip install agent-framework --pre"
            ) from None

    def create_all_agents(
        self,
        issue: Optional[int] = None,
        issue_type: str = "story",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create ChatAgent instances for all defined roles."""
        definitions = self.load_agent_definitions()
        agents = {}
        for role in definitions:
            try:
                agents[role] = self.create_agent(
                    role, issue=issue, issue_type=issue_type, labels=labels
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to create agent for role '%s': %s", role, e)
        return agents

    def _filename_to_role(self, filename: str) -> str:
        """Map .agent.md filename back to role shorthand."""
        reverse_map = {v: k for k, v in ROLE_FILE_MAP.items()}
        return reverse_map.get(filename, filename.replace(".agent.md", ""))

    @staticmethod
    def role_to_filename(role: str) -> str:
        """Map role shorthand to .agent.md filename."""
        return ROLE_FILE_MAP.get(role, f"{role}.agent.md")
