"""
test_nodes.py - Tests unitaires pour agent/nodes.py
TDD Phase Red : LLM et ChromaDB mockés - tests purement unitaires.
Uses: pytest, unittest.mock, LangGraph AgentState
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def base_state():
    """État de base valide pour tous les tests de nodes."""
    return {
        "question": "Quelle est la limite de l'API ?",
        "context": [],
        "answer": "",
        "sources": [],
        "history": [],
        "confidence": 0.0,
        "session_id": "test-session-123",
    }


@pytest.fixture
def state_with_context(base_state):
    """État avec contexte pré-rempli (après retrieve_node)."""
    return {
        **base_state,
        "context": [
            {
                "content": "La limite de taux est 100 req/min.",
                "source": "api.pdf",
                "page": 5,
                "type": "pdf",
                "score": 0.87,
                "chunk_index": 12,
            },
            {
                "content": "Les requêtes sont limitées par IP.",
                "source": "api.pdf",
                "page": 6,
                "type": "pdf",
                "score": 0.72,
                "chunk_index": 13,
            },
        ],
        "confidence": 0.795,
    }


# ── Tests retrieve_node ───────────────────────────────────────────────────────

class TestRetrieveNode:
    """Tests pour retrieve_node - appel au retriever."""

    def test_adds_context_to_state(self, base_state):
        """retrieve_node doit ajouter des résultats dans state['context']."""
        mock_results = [
            {"content": "Chunk pertinent.", "source": "doc.pdf",
             "page": 1, "type": "pdf", "score": 0.85, "chunk_index": 0}
        ]
        with patch("backend.agent.nodes.retrieve_with_confidence",
                   return_value=(mock_results, 0.85)):
            from backend.agent.nodes import retrieve_node
            new_state = retrieve_node(base_state)
            assert "context" in new_state
            assert len(new_state["context"]) == 1

    def test_updates_confidence(self, base_state):
        """retrieve_node doit mettre à jour state['confidence']."""
        mock_results = [
            {"content": "Texte.", "source": "doc.pdf",
             "page": 1, "type": "pdf", "score": 0.9, "chunk_index": 0}
        ]
        with patch("backend.agent.nodes.retrieve_with_confidence",
                   return_value=(mock_results, 0.9)):
            from backend.agent.nodes import retrieve_node
            new_state = retrieve_node(base_state)
            assert new_state["confidence"] == 0.9

    def test_empty_results_sets_empty_context(self, base_state):
        """Aucun résultat → context vide, confidence 0."""
        with patch("backend.agent.nodes.retrieve_with_confidence",
                   return_value=([], 0.0)):
            from backend.agent.nodes import retrieve_node
            new_state = retrieve_node(base_state)
            assert new_state["context"] == []
            assert new_state["confidence"] == 0.0

    def test_returns_dict(self, base_state):
        """retrieve_node doit retourner un dict (mise à jour partielle du state)."""
        with patch("backend.agent.nodes.retrieve_with_confidence",
                   return_value=([], 0.0)):
            from backend.agent.nodes import retrieve_node
            result = retrieve_node(base_state)
            assert isinstance(result, dict)


# ── Tests memory_node ─────────────────────────────────────────────────────────

class TestMemoryNode:
    """Tests pour memory_node - injection de l'historique."""

    def test_applies_sliding_window(self, base_state):
        """memory_node doit appliquer la fenêtre glissante sur l'historique."""
        # Historique de 7 échanges = 14 messages
        history = []
        for i in range(7):
            history.extend([
                {"role": "user", "content": f"q{i}"},
                {"role": "assistant", "content": f"r{i}"},
            ])
        state = {**base_state, "history": history}
        from backend.agent.nodes import memory_node
        new_state = memory_node(state)
        # Fenêtre de 5 échanges = 10 messages max
        assert len(new_state["history"]) <= 10

    def test_empty_history_unchanged(self, base_state):
        """Historique vide → reste vide."""
        from backend.agent.nodes import memory_node
        new_state = memory_node(base_state)
        assert new_state["history"] == []

    def test_returns_dict(self, base_state):
        """memory_node doit retourner un dict."""
        from backend.agent.nodes import memory_node
        assert isinstance(memory_node(base_state), dict)


# ── Tests generate_node ───────────────────────────────────────────────────────

class TestGenerateNode:
    """Tests pour generate_node - appel LLM (mocké)."""

    def test_returns_answer_in_state(self, state_with_context):
        """generate_node doit remplir state['answer']."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "La limite est 100 req/min."
        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.get_llm.return_value = mock_llm
            mock_settings.memory_window = 5
            from backend.agent.nodes import generate_node
            new_state = generate_node(state_with_context)
            assert "answer" in new_state
            assert len(new_state["answer"]) > 0

    def test_no_context_returns_fallback_answer(self, base_state):
        """Sans contexte, generate_node doit retourner un message d'absence de documents."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Je n'ai pas trouvé cette information."
        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.get_llm.return_value = mock_llm
            mock_settings.memory_window = 5
            from backend.agent.nodes import generate_node
            new_state = generate_node(base_state)
            assert "answer" in new_state

    def test_populates_sources_from_context(self, state_with_context):
        """generate_node doit copier le contexte dans sources pour le frontend."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Réponse."
        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.get_llm.return_value = mock_llm
            mock_settings.memory_window = 5
            from backend.agent.nodes import generate_node
            new_state = generate_node(state_with_context)
            assert "sources" in new_state
            assert isinstance(new_state["sources"], list)

    def test_returns_dict(self, state_with_context):
        """generate_node doit retourner un dict."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Réponse."
        with patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.get_llm.return_value = mock_llm
            mock_settings.memory_window = 5
            from backend.agent.nodes import generate_node
            assert isinstance(generate_node(state_with_context), dict)


# ── Tests graph flow ──────────────────────────────────────────────────────────

class TestGraphFlow:
    """Tests pour graph.py - construction et exécution du StateGraph."""

    def test_graph_can_be_compiled(self):
        """Le StateGraph doit pouvoir être compilé sans erreur."""
        from backend.agent.graph import build_graph
        graph = build_graph()
        assert graph is not None

    def test_graph_invoke_returns_state(self):
        """graph.invoke() doit retourner un état avec answer et sources."""
        mock_results = [
            {"content": "La limite est 100 req/min.", "source": "api.pdf",
             "page": 5, "type": "pdf", "score": 0.87, "chunk_index": 0}
        ]
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "La limite est 100 req/min."

        with patch("backend.agent.nodes.retrieve_with_confidence",
                   return_value=(mock_results, 0.87)), \
             patch("backend.agent.nodes.settings") as mock_settings:
            mock_settings.get_llm.return_value = mock_llm
            mock_settings.memory_window = 5

            from backend.agent.graph import build_graph
            from backend.agent.state import create_initial_state
            graph = build_graph()
            initial = create_initial_state("Quelle est la limite ?", "test-session")
            result = graph.invoke(initial)

            assert "answer" in result
            assert "sources" in result
            assert "confidence" in result
