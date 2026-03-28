"""
test_vectorstore.py — Tests unitaires pour retrieval/vectorstore.py
TDD Phase Red : matrice de conformité complète (nominal, bornes, erreurs, contrats).
Uses: pytest, unittest.mock, ChromaDB
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestGetCollection:
    """Tests pour get_collection() — accès à la collection ChromaDB."""

    def test_returns_chroma_collection(self):
        """get_collection() doit retourner un objet collection ChromaDB."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            from backend.retrieval.vectorstore import get_collection
            result = get_collection()
            assert result == mock_collection

    def test_uses_settings_collection_name(self):
        """get_collection() doit utiliser le nom de collection depuis settings."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_client.return_value.get_or_create_collection.return_value = MagicMock()
            from backend.retrieval.vectorstore import get_collection
            from backend.config import settings
            get_collection()
            call_args = mock_client.return_value.get_or_create_collection.call_args
            assert call_args[1]["name"] == settings.chroma_collection or \
                   call_args[0][0] == settings.chroma_collection

    def test_uses_cosine_similarity(self):
        """La collection doit être configurée avec similarité cosinus."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_client.return_value.get_or_create_collection.return_value = MagicMock()
            from backend.retrieval.vectorstore import get_collection
            get_collection()
            call_kwargs = mock_client.return_value.get_or_create_collection.call_args[1]
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("hnsw:space") == "cosine"

    def test_collection_count_returns_int(self):
        """get_collection_count() doit retourner un entier."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_col = MagicMock()
            mock_col.count.return_value = 42
            mock_client.return_value.get_or_create_collection.return_value = mock_col
            from backend.retrieval.vectorstore import get_collection_count
            count = get_collection_count()
            assert isinstance(count, int)
            assert count == 42

    def test_collection_count_empty_returns_zero(self):
        """Une collection vide doit retourner 0."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_col = MagicMock()
            mock_col.count.return_value = 0
            mock_client.return_value.get_or_create_collection.return_value = mock_col
            from backend.retrieval.vectorstore import get_collection_count
            assert get_collection_count() == 0

    def test_delete_document_calls_collection_delete(self):
        """delete_document() doit appeler collection.delete() avec le bon filtre."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_col = MagicMock()
            mock_col.get.return_value = {"ids": ["id1", "id2"], "metadatas": []}
            mock_client.return_value.get_or_create_collection.return_value = mock_col
            from backend.retrieval.vectorstore import delete_document
            delete_document("rapport.pdf")
            mock_col.delete.assert_called_once()
            call_kwargs = mock_col.delete.call_args[1]
            assert "where" in call_kwargs

    def test_list_sources_returns_unique_sources(self):
        """list_sources() doit retourner une liste de sources uniques."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_col = MagicMock()
            mock_col.get.return_value = {
                "metadatas": [
                    {"source": "doc1.pdf", "type": "pdf"},
                    {"source": "doc1.pdf", "type": "pdf"},  # doublon
                    {"source": "doc2.csv", "type": "csv"},
                ]
            }
            mock_client.return_value.get_or_create_collection.return_value = mock_col
            from backend.retrieval.vectorstore import list_sources
            sources = list_sources()
            assert isinstance(sources, list)
            assert len(sources) == 2  # doublons supprimés
            source_names = [s["source"] for s in sources]
            assert "doc1.pdf" in source_names
            assert "doc2.csv" in source_names

    def test_list_sources_empty_collection_returns_empty(self):
        """Une collection vide doit retourner une liste vide."""
        with patch("backend.retrieval.vectorstore.chromadb.PersistentClient") as mock_client:
            mock_col = MagicMock()
            mock_col.get.return_value = {"metadatas": []}
            mock_client.return_value.get_or_create_collection.return_value = mock_col
            from backend.retrieval.vectorstore import list_sources
            assert list_sources() == []
