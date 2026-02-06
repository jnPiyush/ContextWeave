"""Tests for context_md.framework.config -- LLM provider configuration."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from context_md.framework.config import (
    LLMConfig,
    LLMProvider,
    load_llm_config,
    resolve_api_key,
    save_llm_config,
)


class TestLLMProvider:
    def test_provider_values(self):
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"


class TestLLMConfig:
    def test_default_config(self):
        config = LLMConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4o"
        assert config.api_key_env_var == "OPENAI_API_KEY"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_to_dict(self):
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
        data = config.to_dict()
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o-mini"
        assert "azure_endpoint" not in data  # Not included when None

    def test_to_dict_azure(self):
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            azure_endpoint="https://myendpoint.openai.azure.com",
            azure_deployment="gpt-4o",
        )
        data = config.to_dict()
        assert data["azure_endpoint"] == "https://myendpoint.openai.azure.com"
        assert data["azure_deployment"] == "gpt-4o"

    def test_to_dict_anthropic(self):
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            anthropic_model="claude-sonnet-4-20250514",
        )
        data = config.to_dict()
        assert data["anthropic_model"] == "claude-sonnet-4-20250514"

    def test_from_dict(self):
        data = {
            "provider": "anthropic",
            "model": "unused",
            "anthropic_model": "claude-opus-4-20250514",
            "api_key_env_var": "ANTHROPIC_API_KEY",
        }
        config = LLMConfig.from_dict(data)
        assert config.provider == LLMProvider.ANTHROPIC
        assert config.anthropic_model == "claude-opus-4-20250514"

    def test_from_dict_unknown_provider(self):
        data = {"provider": "unknown_provider"}
        config = LLMConfig.from_dict(data)
        assert config.provider == LLMProvider.OPENAI  # Falls back to default

    def test_roundtrip(self):
        original = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model="gpt-4o",
            azure_endpoint="https://example.openai.azure.com",
            temperature=0.5,
        )
        restored = LLMConfig.from_dict(original.to_dict())
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.azure_endpoint == original.azure_endpoint
        assert restored.temperature == original.temperature


class TestLoadSaveLLMConfig:
    def test_load_default(self, tmp_path):
        config = load_llm_config(tmp_path)
        assert config.provider == LLMProvider.OPENAI

    def test_load_from_file(self, tmp_path):
        config_dir = tmp_path / ".agent-context"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "version": "1.0",
            "llm": {
                "provider": "anthropic",
                "api_key_env_var": "ANTHROPIC_API_KEY",
                "anthropic_model": "claude-sonnet-4-20250514",
            }
        }))

        config = load_llm_config(tmp_path)
        assert config.provider == LLMProvider.ANTHROPIC

    def test_save_config(self, tmp_path):
        config_dir = tmp_path / ".agent-context"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0"}))

        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        save_llm_config(tmp_path, llm_config)

        data = json.loads(config_file.read_text())
        assert data["llm"]["provider"] == "openai"
        assert data["llm"]["model"] == "gpt-4o-mini"


class TestResolveApiKey:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-123")
        config = LLMConfig(api_key_env_var="TEST_API_KEY")
        key = resolve_api_key(config)
        assert key == "sk-test-123"

    def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        config = LLMConfig(api_key_env_var="MISSING_KEY")
        with pytest.raises(ValueError, match="No API key found"):
            resolve_api_key(config)

    def test_from_keyring(self, monkeypatch):
        monkeypatch.delenv("MY_KEY", raising=False)
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "keyring-key-123"
        with patch.dict(sys.modules, {"keyring": mock_keyring}):
            config = LLMConfig(api_key_env_var="MY_KEY")
            key = resolve_api_key(config)
            assert key == "keyring-key-123"


class TestGetChatClient:
    @patch("context_md.framework.config.resolve_api_key", return_value="test-key")
    def test_openai_import_error(self, mock_key):
        """When agent_framework is not installed, get_chat_client raises ImportError."""
        from context_md.framework.config import get_chat_client

        config = LLMConfig(provider=LLMProvider.OPENAI)
        # This will fail if agent_framework is not installed
        with pytest.raises(ImportError):
            get_chat_client(config)

    @patch("context_md.framework.config.resolve_api_key", return_value="test-key")
    def test_unsupported_provider(self, mock_key):
        from context_md.framework.config import get_chat_client

        config = LLMConfig()
        # Monkeypatch an invalid provider
        config.provider = "invalid"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Unsupported"):
            get_chat_client(config)

    @patch("context_md.framework.config.resolve_api_key", return_value="test-key")
    def test_azure_missing_endpoint(self, mock_key):
        from context_md.framework.config import get_chat_client

        config = LLMConfig(provider=LLMProvider.AZURE_OPENAI)
        with pytest.raises((ValueError, ImportError)):
            get_chat_client(config)
