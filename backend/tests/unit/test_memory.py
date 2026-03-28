"""
test_memory.py — Tests unitaires pour agent/memory.py
TDD Phase Red : fenêtre glissante, ajout historique, troncature.
Uses: pytest
"""
import pytest


class TestConversationMemory:
    """Tests pour la gestion de la mémoire de conversation."""

    def test_add_exchange_increases_history(self):
        """add_exchange() doit ajouter une paire user/assistant à l'historique."""
        from backend.agent.memory import add_exchange
        history = []
        history = add_exchange(history, "question", "réponse")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "question"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "réponse"

    def test_add_exchange_preserves_existing(self):
        """add_exchange() doit conserver les échanges précédents."""
        from backend.agent.memory import add_exchange
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "r1"},
        ]
        history = add_exchange(history, "q2", "r2")
        assert len(history) == 4
        assert history[0]["content"] == "q1"

    def test_sliding_window_truncates_old_exchanges(self):
        """La fenêtre glissante doit tronquer les anciens échanges (window=5 échanges = 10 messages)."""
        from backend.agent.memory import add_exchange, apply_sliding_window
        history = []
        for i in range(7):
            history = add_exchange(history, f"q{i}", f"r{i}")
        # 7 échanges = 14 messages
        windowed = apply_sliding_window(history, window=5)
        # 5 échanges = 10 messages max
        assert len(windowed) <= 10

    def test_sliding_window_keeps_most_recent(self):
        """La fenêtre glissante doit garder les échanges les plus récents."""
        from backend.agent.memory import add_exchange, apply_sliding_window
        history = []
        for i in range(7):
            history = add_exchange(history, f"q{i}", f"r{i}")
        windowed = apply_sliding_window(history, window=5)
        # Le dernier échange doit être présent
        assert windowed[-1]["content"] == "r6"
        assert windowed[-2]["content"] == "q6"

    def test_sliding_window_empty_history(self):
        """Fenêtre glissante sur historique vide → liste vide."""
        from backend.agent.memory import apply_sliding_window
        assert apply_sliding_window([], window=5) == []

    def test_sliding_window_below_limit(self):
        """Si l'historique est sous la limite, rien n'est tronqué."""
        from backend.agent.memory import add_exchange, apply_sliding_window
        history = []
        history = add_exchange(history, "q", "r")
        windowed = apply_sliding_window(history, window=5)
        assert len(windowed) == 2

    def test_format_history_for_prompt(self):
        """format_history_for_prompt() doit retourner une string lisible."""
        from backend.agent.memory import format_history_for_prompt
        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour, comment puis-je vous aider ?"},
        ]
        result = format_history_for_prompt(history)
        assert isinstance(result, str)
        assert "Bonjour" in result
        assert "user" in result.lower() or "humain" in result.lower() or "utilisateur" in result.lower()

    def test_format_history_empty_returns_empty_string(self):
        """Historique vide → chaîne vide."""
        from backend.agent.memory import format_history_for_prompt
        assert format_history_for_prompt([]) == ""

    def test_add_exchange_empty_question_raises(self):
        """Question vide doit lever ValueError."""
        from backend.agent.memory import add_exchange
        with pytest.raises(ValueError):
            add_exchange([], "", "réponse")

    def test_add_exchange_empty_answer_raises(self):
        """Réponse vide doit lever ValueError."""
        from backend.agent.memory import add_exchange
        with pytest.raises(ValueError):
            add_exchange([], "question", "")
