"""
test_state.py — Tests unitaires pour agent/state.py
TDD Phase Red : vérifie le contrat du TypedDict AgentState.
Uses: pytest, LangGraph TypedDict
"""
import pytest
from langchain_core.documents import Document


class TestAgentState:
    """Tests pour AgentState TypedDict."""

    def test_agent_state_can_be_instantiated(self):
        """AgentState doit pouvoir être instancié avec tous ses champs."""
        from backend.agent.state import AgentState
        state: AgentState = {
            "question": "Quelle est la limite de l'API ?",
            "context": [],
            "answer": "",
            "sources": [],
            "history": [],
            "confidence": 0.0,
            "session_id": "test-session",
        }
        assert state["question"] == "Quelle est la limite de l'API ?"

    def test_all_required_fields_present(self):
        """AgentState doit avoir tous les champs requis."""
        from backend.agent.state import AgentState
        import typing
        hints = typing.get_type_hints(AgentState)
        required_fields = {"question", "context", "answer", "sources", "history", "confidence", "session_id"}
        for field in required_fields:
            assert field in hints, f"Champ manquant : {field}"

    def test_question_is_str(self):
        """question doit être de type str."""
        from backend.agent.state import AgentState
        import typing
        hints = typing.get_type_hints(AgentState)
        assert hints["question"] == str

    def test_confidence_is_float(self):
        """confidence doit être de type float."""
        from backend.agent.state import AgentState
        import typing
        hints = typing.get_type_hints(AgentState)
        assert hints["confidence"] == float

    def test_history_is_list(self):
        """history doit être une liste."""
        from backend.agent.state import AgentState
        import typing
        hints = typing.get_type_hints(AgentState)
        assert "list" in str(hints["history"]).lower()

    def test_create_initial_state(self):
        """create_initial_state() doit retourner un état valide."""
        from backend.agent.state import create_initial_state
        state = create_initial_state("Ma question", session_id="abc")
        assert state["question"] == "Ma question"
        assert state["context"] == []
        assert state["answer"] == ""
        assert state["sources"] == []
        assert state["history"] == []
        assert state["confidence"] == 0.0
        assert state["session_id"] == "abc"

    def test_create_initial_state_default_session(self):
        """create_initial_state() sans session_id doit générer un ID automatique."""
        from backend.agent.state import create_initial_state
        state = create_initial_state("Question")
        assert isinstance(state["session_id"], str)
        assert len(state["session_id"]) > 0
