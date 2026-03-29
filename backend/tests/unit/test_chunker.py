"""
test_chunker.py - Tests unitaires pour ingest/chunker.py
TDD Phase Red : définit le contrat du text splitter LangChain.
Uses: pytest, LangChain Document, RecursiveCharacterTextSplitter
"""
import pytest
from langchain_core.documents import Document


class TestChunkDocuments:
    """Tests pour la fonction chunk_documents."""

    def test_returns_list_of_documents(self, sample_documents):
        """chunk_documents() doit retourner une liste de Documents."""
        from backend.ingest.chunker import chunk_documents
        chunks = chunk_documents(sample_documents)
        assert isinstance(chunks, list)
        assert all(isinstance(c, Document) for c in chunks)

    def test_chunks_not_empty(self, sample_documents):
        """La liste de chunks ne doit pas être vide."""
        from backend.ingest.chunker import chunk_documents
        chunks = chunk_documents(sample_documents)
        assert len(chunks) > 0

    def test_chunk_size_respected(self):
        """Les chunks ne doivent pas dépasser chunk_size (en caractères approximatifs)."""
        from backend.ingest.chunker import chunk_documents
        long_text = "mot " * 300  # ~1200 caractères
        docs = [Document(page_content=long_text, metadata={"source": "test.md"})]
        chunks = chunk_documents(docs, chunk_size=500, chunk_overlap=50)
        for chunk in chunks:
            assert len(chunk.page_content) <= 600  # marge pour les mots

    def test_metadata_preserved(self, sample_documents):
        """Les métadonnées des documents originaux doivent être préservées dans les chunks."""
        from backend.ingest.chunker import chunk_documents
        chunks = chunk_documents(sample_documents)
        for chunk in chunks:
            assert "source" in chunk.metadata

    def test_empty_documents_returns_empty(self):
        """Une liste vide de documents doit retourner une liste vide."""
        from backend.ingest.chunker import chunk_documents
        chunks = chunk_documents([])
        assert chunks == []

    def test_chunk_overlap_creates_continuity(self):
        """Avec overlap, le contenu doit se chevaucher entre chunks consécutifs."""
        from backend.ingest.chunker import chunk_documents
        # Texte assez long pour générer plusieurs chunks
        text = "A " * 400  # 800 caractères
        docs = [Document(page_content=text, metadata={"source": "test.md"})]
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=50)
        if len(chunks) > 1:
            # Le début du chunk 2 doit partager du contenu avec la fin du chunk 1
            end_chunk1 = chunks[0].page_content[-60:]
            start_chunk2 = chunks[1].page_content[:60:]
            # Au moins quelques caractères en commun
            assert len(set(end_chunk1.split()) & set(start_chunk2.split())) > 0

    def test_chunk_adds_chunk_index_metadata(self, sample_documents):
        """Chaque chunk doit avoir un index dans ses métadonnées."""
        from backend.ingest.chunker import chunk_documents
        chunks = chunk_documents(sample_documents)
        for i, chunk in enumerate(chunks):
            assert "chunk_index" in chunk.metadata

    def test_default_chunk_size_is_500(self, sample_documents):
        """Le chunk_size par défaut doit être 500."""
        from backend.ingest.chunker import chunk_documents
        import inspect
        sig = inspect.signature(chunk_documents)
        assert sig.parameters["chunk_size"].default == 500

    def test_default_chunk_overlap_is_50(self, sample_documents):
        """Le chunk_overlap par défaut doit être 50."""
        from backend.ingest.chunker import chunk_documents
        import inspect
        sig = inspect.signature(chunk_documents)
        assert sig.parameters["chunk_overlap"].default == 50
