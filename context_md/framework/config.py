"""
LLM Provider Configuration for Agent Framework integration.

Manages LLM provider settings (OpenAI, Azure OpenAI, Anthropic)
stored in .agent-context/config.json under the 'llm' key.

API keys are NEVER persisted to disk -- resolved at runtime
from environment variables or system keyring.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o"
    api_key_env_var: str = "OPENAI_API_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Azure-specific
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    azure_api_version: str = "2024-12-01-preview"

    # Anthropic-specific
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Additional options
    additional_options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for config storage (excludes sensitive data)."""
        data: Dict[str, Any] = {
            "provider": self.provider.value,
            "model": self.model,
            "api_key_env_var": self.api_key_env_var,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.azure_endpoint:
            data["azure_endpoint"] = self.azure_endpoint
        if self.azure_deployment:
            data["azure_deployment"] = self.azure_deployment
        if self.azure_api_version != "2024-12-01-preview":
            data["azure_api_version"] = self.azure_api_version
        if self.provider == LLMProvider.ANTHROPIC:
            data["anthropic_model"] = self.anthropic_model
        if self.additional_options:
            data["additional_options"] = self.additional_options
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """Create from dict (loaded from config)."""
        provider_str = data.get("provider", "openai")
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            logger.warning("Unknown LLM provider '%s', defaulting to openai", provider_str)
            provider = LLMProvider.OPENAI

        return cls(
            provider=provider,
            model=data.get("model", "gpt-4o"),
            api_key_env_var=data.get("api_key_env_var", "OPENAI_API_KEY"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            azure_endpoint=data.get("azure_endpoint"),
            azure_deployment=data.get("azure_deployment"),
            azure_api_version=data.get("azure_api_version", "2024-12-01-preview"),
            anthropic_model=data.get("anthropic_model", "claude-sonnet-4-20250514"),
            additional_options=data.get("additional_options", {}),
        )


def load_llm_config(repo_root: Path) -> LLMConfig:
    """Load LLM config from .agent-context/config.json under the 'llm' key.

    Falls back to sensible defaults if no config exists.
    """
    from context_md.config import Config

    config = Config(repo_root)
    llm_data = config.get("llm")

    if llm_data and isinstance(llm_data, dict):
        return LLMConfig.from_dict(llm_data)

    return LLMConfig()


def save_llm_config(repo_root: Path, llm_config: LLMConfig) -> None:
    """Save LLM config to .agent-context/config.json under the 'llm' key.

    Never stores API keys in config files.
    """
    from context_md.config import Config

    config = Config(repo_root)
    config.set("llm", llm_config.to_dict())
    config.save()


def resolve_api_key(llm_config: LLMConfig) -> str:
    """Resolve API key from environment variable or keyring.

    Priority:
        1. Environment variable (llm_config.api_key_env_var)
        2. System keyring (service='context-md', username=env_var_name)

    Raises:
        ValueError: If no API key can be found.
    """
    env_var = llm_config.api_key_env_var

    # Try environment variable
    api_key = os.environ.get(env_var)
    if api_key:
        return api_key

    # Try keyring
    try:
        import keyring
        stored_key = keyring.get_password("context-md", env_var)
        if stored_key:
            return stored_key
    except Exception:  # noqa: BLE001
        logger.debug("Keyring not available for API key lookup")

    raise ValueError(
        f"No API key found. Set the {env_var} environment variable "
        f"or store it with: keyring set context-md {env_var}"
    )


def get_chat_client(llm_config: LLMConfig) -> Any:
    """Create the appropriate ChatClient based on provider config.

    Returns an instance compatible with Agent Framework's ChatClientProtocol.

    Raises:
        ImportError: If the provider's package is not installed.
        ValueError: If required config values are missing.
    """
    api_key = resolve_api_key(llm_config)

    if llm_config.provider == LLMProvider.OPENAI:
        try:
            from agent_framework.chat_clients.openai import OpenAIChatClient
        except ImportError:
            raise ImportError(
                "OpenAI chat client requires agent-framework. "
                "Install with: pip install agent-framework --pre"
            ) from None

        return OpenAIChatClient(
            model=llm_config.model,
            api_key=api_key,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )

    elif llm_config.provider == LLMProvider.AZURE_OPENAI:
        if not llm_config.azure_endpoint:
            raise ValueError("Azure OpenAI requires 'azure_endpoint' in config")

        try:
            from agent_framework.chat_clients.azure_openai import AzureOpenAIChatClient
        except ImportError:
            raise ImportError(
                "Azure OpenAI chat client requires agent-framework. "
                "Install with: pip install agent-framework --pre"
            ) from None

        return AzureOpenAIChatClient(
            model=llm_config.azure_deployment or llm_config.model,
            api_key=api_key,
            azure_endpoint=llm_config.azure_endpoint,
            api_version=llm_config.azure_api_version,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )

    elif llm_config.provider == LLMProvider.ANTHROPIC:
        try:
            from agent_framework_anthropic import AnthropicChatClient
        except ImportError:
            raise ImportError(
                "Anthropic chat client requires agent-framework-anthropic. "
                "Install with: pip install agent-framework-anthropic --pre"
            ) from None

        return AnthropicChatClient(
            model=llm_config.anthropic_model,
            api_key=api_key,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")
