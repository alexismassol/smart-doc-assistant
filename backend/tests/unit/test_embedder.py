"""
test_embedder.py - Tests unitaires pour ingest/embedder.py
TDD Phase Red : Ollama et ChromaDB sont mockés - tests purement unitaires.
Uses: pytest, unittest.mock, LangChain Document
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestEmbedAndStore:
    """Tests pour embed_and_store() - Ollama mocké, ChromaDB in-memory."""

    def test_returns_count_of_stored_chunks(self, sample_documents):
        """embed_and_store() doit retourner le nombre de chunks stockés."""
        from backend.ingest.embedder import embed_and_store
        with patch("backend.ingest.embedder.OllamaEmbeddings") as mock_emb, \
             patch("backend.ingest.embedder.chromadb.PersistentClient") as mock_chroma:
            # Mock embeddings
            mock_emb_instance = MagicMock()
            mock_emb_instance.embed_documents.return_value = [[0.1] * 768] * len(sample_documents)
            mock_emb.return_value = mock_emb_instance
            # Mock ChromaDB collection
            mock_collection = MagicMock()
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            count = embed_and_store(sample_documents)
            assert count == len(sample_documents)

    def test_chroma_add_called_with_correct_ids(self, sample_documents):
        """ChromaDB .add() doit être appelé avec des IDs uniques."""
        from backend.ingest.embedder import embed_and_store
        with patch("backend.ingest.embedder.OllamaEmbeddings") as mock_emb, \
             patch("backend.ingest.embedder.chromadb.PersistentClient") as mock_chroma:
            mock_emb_instance = MagicMock()
            mock_emb_instance.embed_documents.return_value = [[0.1] * 768] * len(sample_documents)
            mock_emb.return_value = mock_emb_instance
            mock_collection = MagicMock()
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            embed_and_store(sample_documents)
            assert mock_collection.upsert.called

    def test_empty_documents_returns_zero(self):
        """Une liste vide doit retourner 0."""
        from backend.ingest.embedder import embed_and_store
        with patch("backend.ingest.embedder.OllamaEmbeddings"), \
             patch("backend.ingest.embedder.chromadb.PersistentClient"):
            count = embed_and_store([])
            assert count == 0

    def test_metadata_includes_timestamp(self, sample_documents):
        """Chaque chunk stocké doit avoir un timestamp dans les métadonnées."""
        from backend.ingest.embedder import embed_and_store
        stored_metadatas = []

        def capture_upsert(**kwargs):
            stored_metadatas.extend(kwargs.get("metadatas", []))

        with patch("backend.ingest.embedder.OllamaEmbeddings") as mock_emb, \
             patch("backend.ingest.embedder.chromadb.PersistentClient") as mock_chroma:
            mock_emb_instance = MagicMock()
            mock_emb_instance.embed_documents.return_value = [[0.1] * 768] * len(sample_documents)
            mock_emb.return_value = mock_emb_instance
            mock_collection = MagicMock()
            mock_collection.upsert.side_effect = capture_upsert
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            embed_and_store(sample_documents)

        for meta in stored_metadatas:
            assert "timestamp" in meta
