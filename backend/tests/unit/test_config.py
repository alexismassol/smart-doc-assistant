"""
test_config.py — Tests unitaires pour config.py
TDD Phase Red : ces tests définissent le contrat de config.py avant son implémentation.
Uses: pytest, pydantic-settings
"""
import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Tests pour la classe Settings (Pydantic Settings v2)."""

    def test_default_llm_provider_is_ollama(self):
        """Le provider LLM par défaut doit être 'ollama'."""
        with patch.dict(os.environ, {}, clear=False):
            from backend.config import Settings
            s = Settings()
            assert s.llm_provider == "ollama"

    def test_valid_providers(self):
        """Les providers valides sont : ollama, mistral, anthropic."""
        from backend.config import Settings
        for provider in ["ollama", "mistral", "anthropic"]:
            s = Settings(llm_provider=provider)
            assert s.llm_provider == provider

    def test_invalid_provider_raises(self):
        """Un provider inconnu doit lever une ValidationError."""
        from pydantic import ValidationError
        from backend.config import Settings
        with pytest.raises(ValidationError):
            Settings(llm_provider="openai")

    def test_retrieval_top_k_default(self):
        """top_k par défaut = 5."""
        from backend.config import Settings
        s = Settings()
        assert s.retrieval_top_k == 5

    def test_retrieval_score_threshold_default(self):
        """score_threshold par défaut = 0.4."""
        from backend.config import Settings
        s = Settings()
        assert s.retrieval_score_threshold == 0.4

    def test_memory_window_default(self):
        """memory_window par défaut = 5."""
        from backend.config import Settings
        s = Settings()
        assert s.memory_window == 5

    def test_chroma_collection_default(self):
        """Collection ChromaDB par défaut = 'smart_docs'."""
        from backend.config import Settings
        s = Settings()
        assert s.chroma_collection == "smart_docs"

    def test_get_llm_returns_chat_ollama(self):
        """get_llm() avec provider=ollama retourne un ChatOllama."""
        from backend.config import Settings
        from langchain_ollama import ChatOllama
        s = Settings(llm_provider="ollama")
        llm = s.get_llm()
        assert isinstance(llm, ChatOllama)

    def test_get_llm_mistral_without_key_raises(self):
        """get_llm() avec provider=mistral sans API key doit lever une ValueError."""
        from backend.config import Settings
        s = Settings(llm_provider="mistral", mistral_api_key=None)
        with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
            s.get_llm()

    def test_get_llm_anthropic_without_key_raises(self):
        """get_llm() avec provider=anthropic sans API key doit lever une ValueError."""
        from backend.config import Settings
        s = Settings(llm_provider="anthropic", anthropic_api_key=None)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            s.get_llm()

    def test_env_override_from_environment(self):
        """Les variables d'env doivent overrider les valeurs par défaut."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "mistral", "MISTRAL_API_KEY": "test_key"}):
            from importlib import reload
            import backend.config as config_module
            reload(config_module)
            s = config_module.Settings()
            assert s.llm_provider == "mistral"
