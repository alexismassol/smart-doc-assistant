"""
config.py — Configuration centralisée Smart Doc Assistant
Uses: Pydantic Settings v2 (validation .env typée), python-dotenv
Gère : LLM provider switchable (ollama | mistral | anthropic), ChromaDB, agent params.
"""
from typing import Literal, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration principale chargée depuis .env.
    Pydantic Settings v2 valide chaque champ au démarrage.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────────
    llm_provider: Literal["ollama", "mistral", "anthropic"] = "ollama"

    # Ollama (local, dev — gratuit, offline)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Mistral API (prod)
    mistral_api_key: Optional[str] = None
    mistral_model: str = "mistral-small-latest"

    # Anthropic Claude (alternatif, démo multi-provider)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-haiku-4-5"

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = "nomic-embed-text"
    embedding_provider: str = "ollama"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection: str = "smart_docs"

    # ── Backend ───────────────────────────────────────────────────────────────
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # ── Agent RAG ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.4
    memory_window: int = 5

    # ── Historique persistant SQLite ──────────────────────────────────────────
    history_db_path: str = "./data/history.db"

    def get_llm(self):
        """
        Retourne l'instance LLM configurée selon llm_provider.

        Returns:
            ChatOllama | ChatMistralAI | ChatAnthropic selon le provider.

        Raises:
            ValueError: si la clé API requise est absente.
        """
        if self.llm_provider == "ollama":
            # LangChain + Ollama — inférence locale Mistral 7B
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_base_url,
            )

        elif self.llm_provider == "mistral":
            # LangChain + Mistral API — mistral-small-latest
            if not self.mistral_api_key:
                raise ValueError(
                    "MISTRAL_API_KEY est requis quand LLM_PROVIDER=mistral. "
                    "Ajoutez-la dans votre fichier .env"
                )
            from langchain_mistralai import ChatMistralAI
            return ChatMistralAI(
                api_key=self.mistral_api_key,
                model=self.mistral_model,
            )

        elif self.llm_provider == "anthropic":
            # LangChain + Anthropic — Claude Haiku (démo multi-provider)
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY est requis quand LLM_PROVIDER=anthropic. "
                    "Ajoutez-la dans votre fichier .env"
                )
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=self.anthropic_api_key,
                model=self.anthropic_model,
            )

    def get_cors_origins_list(self) -> list[str]:
        """Retourne la liste des origines CORS autorisées (depuis .env CORS_ORIGINS)."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Instance globale — importée par les autres modules
settings = Settings()
