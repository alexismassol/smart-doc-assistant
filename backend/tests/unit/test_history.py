"""
test_history.py - Tests TDD pour le module history SQLite (Red → Green → Refactor)
Uses: pytest, sqlite3 (in-memory via tmp_path)

Matrice de conformité :
- Nominal    : save_message, get_session_history, list_sessions
- Bornes     : session vide, très long contenu, 0 messages, 100 messages
- Erreurs    : session_id inexistant → liste vide (pas d'exception)
- Métadonnées: timestamp auto-généré, role présent et typé
- Contrats   : pagination (limit), ordre chronologique, idempotence
- Suppression: clear_session efface uniquement la bonne session
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


# ─── Fixture : base SQLite temporaire ─────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path):
    """Crée un chemin de base SQLite temporaire pour chaque test."""
    return str(tmp_path / "test_history.db")


@pytest.fixture
def history_store(db_path):
    """Instance HistoryStore avec base temporaire."""
    from history.store import HistoryStore
    store = HistoryStore(db_path=db_path)
    return store


# ─── Tests d'initialisation ───────────────────────────────────────────────────

class TestHistoryStoreInit:
    def test_creates_db_file_on_init(self, db_path):
        from history.store import HistoryStore
        HistoryStore(db_path=db_path)
        assert os.path.exists(db_path)

    def test_creates_messages_table(self, db_path):
        from history.store import HistoryStore
        HistoryStore(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent_init(self, db_path):
        """Deux initialisations successives ne cassent pas la table."""
        from history.store import HistoryStore
        HistoryStore(db_path=db_path)
        HistoryStore(db_path=db_path)  # Ne doit pas lever d'exception
        assert os.path.exists(db_path)


# ─── Tests save_message ───────────────────────────────────────────────────────

class TestSaveMessage:
    def test_save_user_message(self, history_store):
        history_store.save_message("session1", "user", "Ma question test")
        messages = history_store.get_session_history("session1")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Ma question test"

    def test_save_assistant_message(self, history_store):
        history_store.save_message("session1", "assistant", "Ma réponse")
        messages = history_store.get_session_history("session1")
        assert messages[0]["role"] == "assistant"

    def test_save_multiple_messages_same_session(self, history_store):
        history_store.save_message("session1", "user", "Q1")
        history_store.save_message("session1", "assistant", "R1")
        history_store.save_message("session1", "user", "Q2")
        messages = history_store.get_session_history("session1")
        assert len(messages) == 3

    def test_message_has_timestamp(self, history_store):
        history_store.save_message("session1", "user", "Question")
        messages = history_store.get_session_history("session1")
        assert "timestamp" in messages[0]
        assert messages[0]["timestamp"] is not None

    def test_message_has_session_id(self, history_store):
        history_store.save_message("session1", "user", "Question")
        messages = history_store.get_session_history("session1")
        assert messages[0]["session_id"] == "session1"

    def test_save_long_content(self, history_store):
        long_content = "A" * 10_000
        history_store.save_message("session1", "assistant", long_content)
        messages = history_store.get_session_history("session1")
        assert len(messages[0]["content"]) == 10_000


# ─── Tests get_session_history ────────────────────────────────────────────────

class TestGetSessionHistory:
    def test_returns_empty_list_for_unknown_session(self, history_store):
        messages = history_store.get_session_history("unknown-session")
        assert messages == []

    def test_returns_chronological_order(self, history_store):
        history_store.save_message("session1", "user", "First")
        history_store.save_message("session1", "assistant", "Second")
        history_store.save_message("session1", "user", "Third")
        messages = history_store.get_session_history("session1")
        assert messages[0]["content"] == "First"
        assert messages[2]["content"] == "Third"

    def test_limit_parameter(self, history_store):
        for i in range(10):
            history_store.save_message("session1", "user", f"Question {i}")
        messages = history_store.get_session_history("session1", limit=5)
        assert len(messages) == 5

    def test_limit_returns_most_recent(self, history_store):
        for i in range(5):
            history_store.save_message("session1", "user", f"Q{i}")
        messages = history_store.get_session_history("session1", limit=2)
        assert messages[-1]["content"] == "Q4"

    def test_isolation_between_sessions(self, history_store):
        history_store.save_message("session_A", "user", "Question A")
        history_store.save_message("session_B", "user", "Question B")
        messages_a = history_store.get_session_history("session_A")
        assert len(messages_a) == 1
        assert messages_a[0]["content"] == "Question A"

    def test_zero_messages_session(self, history_store):
        messages = history_store.get_session_history("empty-session")
        assert isinstance(messages, list)
        assert len(messages) == 0


# ─── Tests list_sessions ──────────────────────────────────────────────────────

class TestListSessions:
    def test_returns_empty_if_no_sessions(self, history_store):
        sessions = history_store.list_sessions()
        assert sessions == []

    def test_returns_unique_session_ids(self, history_store):
        history_store.save_message("s1", "user", "Q")
        history_store.save_message("s1", "assistant", "R")
        history_store.save_message("s2", "user", "Q")
        sessions = history_store.list_sessions()
        session_ids = [s["session_id"] for s in sessions]
        assert "s1" in session_ids
        assert "s2" in session_ids
        assert len(session_ids) == 2  # pas de doublons

    def test_session_includes_message_count(self, history_store):
        history_store.save_message("s1", "user", "Q1")
        history_store.save_message("s1", "assistant", "R1")
        sessions = history_store.list_sessions()
        s1 = next(s for s in sessions if s["session_id"] == "s1")
        assert s1["message_count"] == 2

    def test_session_includes_last_message_at(self, history_store):
        history_store.save_message("s1", "user", "Q")
        sessions = history_store.list_sessions()
        assert "last_message_at" in sessions[0]


# ─── Tests clear_session ──────────────────────────────────────────────────────

class TestClearSession:
    def test_clears_only_target_session(self, history_store):
        history_store.save_message("s1", "user", "Q")
        history_store.save_message("s2", "user", "Q")
        history_store.clear_session("s1")
        assert history_store.get_session_history("s1") == []
        assert len(history_store.get_session_history("s2")) == 1

    def test_clear_nonexistent_session_no_error(self, history_store):
        # Ne doit pas lever d'exception
        history_store.clear_session("nonexistent-session")

    def test_clear_then_save_works(self, history_store):
        history_store.save_message("s1", "user", "Q1")
        history_store.clear_session("s1")
        history_store.save_message("s1", "user", "Q2")
        messages = history_store.get_session_history("s1")
        assert len(messages) == 1
        assert messages[0]["content"] == "Q2"
