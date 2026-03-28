"""
test_retriever.py — Tests unitaires pour retrieval/retriever.py
TDD Phase Red : matrice de conformité complète — similarity search, reranking, bornes.
Uses: pytest, unittest.mock, LangChain Document
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_chroma_results():
    """Résultats ChromaDB simulés — format réel de l'API ChromaDB."""
    return {
        "documents": [
            ["La limite de taux est 100 req/min."],
            ["FastAPI supporte async nativement."],
            ["ChromaDB stocke des vecteurs d'embedding."],
            ["LangGraph orchestre les agents LLM."],
            ["nomic-embed-text génère des vecteurs de dim 768."],
        ],
        "metadatas": [
            [{"source": "api.pdf", "page": 5, "type": "pdf", "chunk_index": 12}],
            [{"source": "tech.md", "page": 0, "type": "markdown", "chunk_index": 3}],
            [{"source": "doc.pdf", "page": 2, "type": "pdf", "chunk_index": 7}],
            [{"source": "guide.md", "page": 0, "type": "markdown", "chunk_index": 1}],
            [{"source": "notes.md", "page": 0, "type": "markdown", "chunk_index": 9}],
        ],
        "distances": [[0.12, 0.25, 0.38, 0.45, 0.55]],
    }


@pytest.fixture
def mock_embeddings():
    """Mock OllamaEmbeddings pour éviter les appels réseau."""
    with patch("backend.retrieval.retriever.OllamaEmbeddings") as mock:
        instance = MagicMock()
        instance.embed_query.return_value = [0.1] * 768
        mock.return_value = instance
        yield mock


# ── Tests similarity_search ───────────────────────────────────────────────────

class TestSimilaritySearch:
    """Tests pour similarity_search() — requête ChromaDB."""

    def test_returns_list_of_documents(self, mock_embeddings, mock_chroma_results):
        """similarity_search() doit retourner une liste de Documents LangChain."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            results = similarity_search("Quelle est la limite de l'API ?")
            assert isinstance(results, list)
            assert all(isinstance(r, dict) for r in results)

    def test_result_has_required_fields(self, mock_embeddings, mock_chroma_results):
        """Chaque résultat doit avoir content, source, score, page, type."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            results = similarity_search("limite API")
            for r in results:
                assert "content" in r
                assert "source" in r
                assert "score" in r
                assert "page" in r
                assert "type" in r

    def test_score_is_float_between_0_and_1(self, mock_embeddings, mock_chroma_results):
        """Les scores de similarité doivent être des floats entre 0 et 1."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            results = similarity_search("test")
            for r in results:
                assert isinstance(r["score"], float)
                assert 0.0 <= r["score"] <= 1.0

    def test_respects_top_k(self, mock_embeddings, mock_chroma_results):
        """similarity_search() doit passer n_results=top_k à ChromaDB."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            similarity_search("test", top_k=3)
            call_kwargs = mock_col.return_value.query.call_args[1]
            assert call_kwargs.get("n_results") == 3

    def test_default_top_k_from_settings(self, mock_embeddings, mock_chroma_results):
        """Le top_k par défaut doit venir de settings.retrieval_top_k."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            from backend.config import settings
            import inspect
            sig = inspect.signature(similarity_search)
            # top_k default doit être None (résolu depuis settings) ou == settings.retrieval_top_k
            default = sig.parameters["top_k"].default
            assert default is None or default == settings.retrieval_top_k

    def test_empty_query_returns_empty(self, mock_embeddings):
        """Une query vide doit retourner une liste vide sans appeler ChromaDB."""
        from backend.retrieval.retriever import similarity_search
        results = similarity_search("")
        assert results == []

    def test_empty_collection_returns_empty(self, mock_embeddings):
        """Une collection vide doit retourner une liste vide."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = {
                "documents": [[]], "metadatas": [[]], "distances": [[]]
            }
            from backend.retrieval.retriever import similarity_search
            results = similarity_search("une question")
            assert results == []

    def test_results_sorted_by_score_descending(self, mock_embeddings, mock_chroma_results):
        """Les résultats doivent être triés par score décroissant (plus pertinent en premier)."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import similarity_search
            results = similarity_search("test")
            if len(results) > 1:
                scores = [r["score"] for r in results]
                assert scores == sorted(scores, reverse=True)


# ── Tests rerank ──────────────────────────────────────────────────────────────

class TestRerank:
    """Tests pour rerank() — filtrage par score threshold."""

    def test_filters_below_threshold(self):
        """rerank() doit supprimer les résultats sous le score_threshold."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "bon", "score": 0.85, "source": "a.pdf", "page": 0, "type": "pdf"},
            {"content": "moyen", "score": 0.50, "source": "b.pdf", "page": 0, "type": "pdf"},
            {"content": "mauvais", "score": 0.20, "source": "c.pdf", "page": 0, "type": "pdf"},
        ]
        filtered = rerank(results, score_threshold=0.4)
        assert len(filtered) == 2
        assert all(r["score"] >= 0.4 for r in filtered)

    def test_keeps_all_above_threshold(self):
        """Tous les résultats au-dessus du seuil doivent être conservés."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "a", "score": 0.9, "source": "a.pdf", "page": 0, "type": "pdf"},
            {"content": "b", "score": 0.8, "source": "b.pdf", "page": 0, "type": "pdf"},
            {"content": "c", "score": 0.7, "source": "c.pdf", "page": 0, "type": "pdf"},
        ]
        filtered = rerank(results, score_threshold=0.4)
        assert len(filtered) == 3

    def test_empty_input_returns_empty(self):
        """Une liste vide doit retourner une liste vide."""
        from backend.retrieval.retriever import rerank
        assert rerank([], score_threshold=0.4) == []

    def test_all_below_threshold_returns_empty(self):
        """Si tous les scores sont sous le seuil → liste vide."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "a", "score": 0.1, "source": "a.pdf", "page": 0, "type": "pdf"},
            {"content": "b", "score": 0.2, "source": "b.pdf", "page": 0, "type": "pdf"},
        ]
        assert rerank(results, score_threshold=0.4) == []

    def test_threshold_zero_keeps_all(self):
        """Seuil à 0 → tous les résultats conservés."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "a", "score": 0.05, "source": "a.pdf", "page": 0, "type": "pdf"},
        ]
        assert len(rerank(results, score_threshold=0.0)) == 1

    def test_threshold_one_keeps_none(self):
        """Seuil à 1.0 → aucun résultat (score jamais exactement 1.0)."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "a", "score": 0.99, "source": "a.pdf", "page": 0, "type": "pdf"},
        ]
        assert rerank(results, score_threshold=1.0) == []

    def test_default_threshold_from_settings(self):
        """Le score_threshold par défaut doit venir de settings."""
        from backend.retrieval.retriever import rerank
        from backend.config import settings
        import inspect
        sig = inspect.signature(rerank)
        default = sig.parameters["score_threshold"].default
        assert default is None or default == settings.retrieval_score_threshold

    def test_output_sorted_by_score_descending(self):
        """Les résultats filtrés doivent rester triés par score décroissant."""
        from backend.retrieval.retriever import rerank
        results = [
            {"content": "c", "score": 0.6, "source": "c.pdf", "page": 0, "type": "pdf"},
            {"content": "a", "score": 0.9, "source": "a.pdf", "page": 0, "type": "pdf"},
            {"content": "b", "score": 0.75, "source": "b.pdf", "page": 0, "type": "pdf"},
        ]
        filtered = rerank(results, score_threshold=0.4)
        scores = [r["score"] for r in filtered]
        assert scores == sorted(scores, reverse=True)


# ── Tests retrieve (fonction principale) ─────────────────────────────────────

class TestRetrieve:
    """Tests pour retrieve() — pipeline complet search + rerank."""

    def test_returns_list(self, mock_embeddings, mock_chroma_results):
        """retrieve() doit retourner une liste."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import retrieve
            results = retrieve("question test")
            assert isinstance(results, list)

    def test_empty_query_returns_empty(self, mock_embeddings):
        """Query vide → liste vide, pas d'appel ChromaDB."""
        from backend.retrieval.retriever import retrieve
        results = retrieve("")
        assert results == []

    def test_low_scores_filtered_out(self, mock_embeddings):
        """Les résultats sous le threshold doivent être filtrés."""
        low_score_results = {
            "documents": [["texte peu pertinent"]],
            "metadatas": [[{"source": "doc.pdf", "page": 0, "type": "pdf", "chunk_index": 0}]],
            "distances": [[0.9]],  # distance élevée = similarité faible
        }
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = low_score_results
            from backend.retrieval.retriever import retrieve
            # score_threshold=0.4 → résultats avec score < 0.4 éliminés
            results = retrieve("question", score_threshold=0.8)
            # Un distance de 0.9 en cosinus = score de 0.1 → filtré
            assert len(results) == 0

    def test_confidence_score_returned(self, mock_embeddings, mock_chroma_results):
        """retrieve() doit aussi retourner un score de confiance moyen."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = mock_chroma_results
            from backend.retrieval.retriever import retrieve_with_confidence
            results, confidence = retrieve_with_confidence("test")
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_confidence_zero_when_no_results(self, mock_embeddings):
        """Confidence = 0.0 quand aucun résultat."""
        with patch("backend.retrieval.retriever.get_collection") as mock_col:
            mock_col.return_value.query.return_value = {
                "documents": [[]], "metadatas": [[]], "distances": [[]]
            }
            from backend.retrieval.retriever import retrieve_with_confidence
            results, confidence = retrieve_with_confidence("test")
            assert confidence == 0.0
