"""
test_api_routes.py — Tests d'intégration FastAPI (tous les endpoints)
TDD Phase Red : httpx AsyncClient + FastAPI TestClient.
Uses: FastAPI TestClient, pytest-asyncio, unittest.mock
Couvre : /api/health, /api/chat, /api/upload, /api/ingest-url, /api/documents,
         /api/history/{session_id}, DELETE /api/history/{session_id}, /api/sessions
"""
import pytest
import io
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Client de test FastAPI synchrone."""
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def history_store_tmp(tmp_path):
    """HistoryStore isolé sur fichier temporaire — injecté dans routes_chat."""
    from backend.history.store import HistoryStore
    db = HistoryStore(db_path=str(tmp_path / "test_history.db"))
    return db


@pytest.fixture
def mock_agent():
    """Mock du graph LangGraph pour éviter les appels LLM/ChromaDB."""
    mock_result = {
        "answer": "La limite est 100 req/min.",
        "sources": [
            {"content": "La limite de taux est 100 req/min.",
             "source": "api.pdf", "page": 5, "score": 0.87, "type": "pdf"}
        ],
        "confidence": 0.87,
        "question": "Quelle est la limite ?",
        "context": [],
        "history": [],
        "session_id": "test-session",
    }
    return mock_result


# ── GET /api/health ────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        """GET /api/health doit retourner 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_has_status_ok(self, client):
        """La réponse health doit contenir status=ok."""
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_has_llm_provider(self, client):
        """La réponse health doit indiquer le provider LLM actif."""
        response = client.get("/api/health")
        data = response.json()
        assert "llm_provider" in data

    def test_health_has_documents_count(self, client):
        """La réponse health doit indiquer le nombre de documents."""
        with patch("backend.api.routes_ingest.get_collection_count", return_value=42):
            response = client.get("/api/health")
            data = response.json()
            assert "documents_count" in data


# ── POST /api/chat ─────────────────────────────────────────────────────────────

class TestChat:
    def test_chat_returns_200(self, client, mock_agent):
        """POST /api/chat doit retourner 200."""
        with patch("backend.api.routes_chat.agent_graph") as mock_graph:
            mock_graph.invoke.return_value = mock_agent
            response = client.post("/api/chat", json={
                "question": "Quelle est la limite ?",
                "session_id": "test-session"
            })
        assert response.status_code == 200

    def test_chat_response_has_required_fields(self, client, mock_agent):
        """La réponse chat doit avoir answer, sources, confidence, latency_ms."""
        with patch("backend.api.routes_chat.agent_graph") as mock_graph:
            mock_graph.invoke.return_value = mock_agent
            response = client.post("/api/chat", json={
                "question": "Question test",
                "session_id": "test"
            })
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        assert "latency_ms" in data

    def test_chat_latency_ms_is_positive_int(self, client, mock_agent):
        """latency_ms doit être un entier positif."""
        with patch("backend.api.routes_chat.agent_graph") as mock_graph:
            mock_graph.invoke.return_value = mock_agent
            response = client.post("/api/chat", json={
                "question": "Question",
                "session_id": "test"
            })
        data = response.json()
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0

    def test_chat_empty_question_returns_422(self, client):
        """Question vide doit retourner 422 (validation Pydantic)."""
        response = client.post("/api/chat", json={
            "question": "",
            "session_id": "test"
        })
        assert response.status_code == 422

    def test_chat_missing_question_returns_422(self, client):
        """Body sans question doit retourner 422."""
        response = client.post("/api/chat", json={"session_id": "test"})
        assert response.status_code == 422

    def test_chat_auto_generates_session_id(self, client, mock_agent):
        """Sans session_id, un ID doit être auto-généré."""
        with patch("backend.api.routes_chat.agent_graph") as mock_graph:
            mock_graph.invoke.return_value = mock_agent
            response = client.post("/api/chat", json={"question": "Test"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_chat_sources_is_list(self, client, mock_agent):
        """sources doit être une liste."""
        with patch("backend.api.routes_chat.agent_graph") as mock_graph:
            mock_graph.invoke.return_value = mock_agent
            response = client.post("/api/chat", json={
                "question": "Test",
                "session_id": "s1"
            })
        assert isinstance(response.json()["sources"], list)


# ── POST /api/upload ───────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_markdown_returns_200(self, client):
        """Upload d'un fichier .md doit retourner 200."""
        with patch("backend.api.routes_ingest.load_document", return_value=[MagicMock(page_content="contenu", metadata={"source": "test.md", "type": "markdown", "page": 0})]), \
             patch("backend.api.routes_ingest.chunk_documents", return_value=[MagicMock(page_content="chunk", metadata={"source": "test.md", "type": "markdown", "page": 0, "chunk_index": 0})]), \
             patch("backend.api.routes_ingest.embed_and_store", return_value=3):
            file_content = b"# Test\n\nContenu markdown."
            response = client.post(
                "/api/upload",
                files={"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
            )
        assert response.status_code == 200

    def test_upload_response_has_chunks_created(self, client):
        """La réponse upload doit indiquer le nombre de chunks créés."""
        with patch("backend.api.routes_ingest.load_document", return_value=[MagicMock(page_content="x", metadata={"source": "f.md", "type": "markdown", "page": 0})]), \
             patch("backend.api.routes_ingest.chunk_documents", return_value=[MagicMock(page_content="c", metadata={"source": "f.md", "type": "markdown", "page": 0, "chunk_index": 0})]), \
             patch("backend.api.routes_ingest.embed_and_store", return_value=5):
            response = client.post(
                "/api/upload",
                files={"file": ("test.md", io.BytesIO(b"# Test"), "text/markdown")}
            )
        data = response.json()
        assert "chunks_created" in data
        assert data["chunks_created"] == 5

    def test_upload_unsupported_format_returns_400(self, client):
        """Un format non supporté (.exe) doit retourner 400."""
        response = client.post(
            "/api/upload",
            files={"file": ("virus.exe", io.BytesIO(b"binary"), "application/octet-stream")}
        )
        assert response.status_code == 400

    def test_upload_empty_file_returns_400(self, client):
        """Un fichier vide doit retourner 400."""
        response = client.post(
            "/api/upload",
            files={"file": ("empty.md", io.BytesIO(b""), "text/markdown")}
        )
        assert response.status_code == 400

    def test_upload_response_has_filename(self, client):
        """La réponse doit contenir le nom du fichier."""
        with patch("backend.api.routes_ingest.load_document", return_value=[MagicMock(page_content="x", metadata={"source": "doc.md", "type": "markdown", "page": 0})]), \
             patch("backend.api.routes_ingest.chunk_documents", return_value=[MagicMock(page_content="c", metadata={"source": "doc.md", "type": "markdown", "page": 0, "chunk_index": 0})]), \
             patch("backend.api.routes_ingest.embed_and_store", return_value=2):
            response = client.post(
                "/api/upload",
                files={"file": ("doc.md", io.BytesIO(b"# Doc"), "text/markdown")}
            )
        assert response.json()["filename"] == "doc.md"


# ── POST /api/ingest-url ───────────────────────────────────────────────────────

class TestIngestUrl:
    def test_ingest_url_returns_200(self, client):
        """POST /api/ingest-url doit retourner 200 avec une URL valide."""
        from langchain_core.documents import Document
        mock_docs = [Document(page_content="Contenu web.", metadata={"source": "http://example.com", "type": "url", "page": 0})]
        mock_chunks = [Document(page_content="Chunk.", metadata={"source": "http://example.com", "type": "url", "page": 0, "chunk_index": 0})]
        with patch("backend.api.routes_ingest.load_url", return_value=mock_docs), \
             patch("backend.api.routes_ingest.chunk_documents", return_value=mock_chunks), \
             patch("backend.api.routes_ingest.embed_and_store", return_value=1):
            response = client.post("/api/ingest-url", json={"url": "http://example.com/doc"})
        assert response.status_code == 200

    def test_ingest_url_invalid_url_returns_422(self, client):
        """Une URL invalide doit retourner 422."""
        response = client.post("/api/ingest-url", json={"url": "pas-une-url"})
        assert response.status_code == 422

    def test_ingest_url_missing_url_returns_422(self, client):
        """Body sans url doit retourner 422."""
        response = client.post("/api/ingest-url", json={})
        assert response.status_code == 422

    def test_ingest_url_response_has_chunks_created(self, client):
        """La réponse doit indiquer le nombre de chunks créés."""
        from langchain_core.documents import Document
        mock_docs = [Document(page_content="x", metadata={"source": "http://ex.com", "type": "url", "page": 0})]
        mock_chunks = [Document(page_content="c", metadata={"source": "http://ex.com", "type": "url", "page": 0, "chunk_index": 0})]
        with patch("backend.api.routes_ingest.load_url", return_value=mock_docs), \
             patch("backend.api.routes_ingest.chunk_documents", return_value=mock_chunks), \
             patch("backend.api.routes_ingest.embed_and_store", return_value=4):
            response = client.post("/api/ingest-url", json={"url": "http://example.com"})
        assert response.json()["chunks_created"] == 4


# ── GET /api/documents ─────────────────────────────────────────────────────────

class TestDocuments:
    def test_get_documents_returns_200(self, client):
        """GET /api/documents doit retourner 200."""
        with patch("backend.api.routes_ingest.list_sources", return_value=[]):
            response = client.get("/api/documents")
        assert response.status_code == 200

    def test_get_documents_has_documents_list(self, client):
        """La réponse doit avoir un champ documents (liste)."""
        with patch("backend.api.routes_ingest.list_sources", return_value=[]):
            response = client.get("/api/documents")
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_get_documents_has_total(self, client):
        """La réponse doit avoir un champ total."""
        with patch("backend.api.routes_ingest.list_sources", return_value=[]):
            response = client.get("/api/documents")
        assert "total" in response.json()

    def test_get_documents_returns_sources(self, client):
        """Les documents retournés doivent correspondre aux sources ChromaDB."""
        sources = [{"source": "doc.pdf", "type": "pdf", "chunk_count": 10}]
        with patch("backend.api.routes_ingest.list_sources", return_value=sources):
            response = client.get("/api/documents")
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["source"] == "doc.pdf"


# ── DELETE /api/documents/{source} ────────────────────────────────────────────

class TestDeleteDocument:
    def test_delete_document_returns_200(self, client):
        """DELETE /api/documents/{source} doit retourner 200."""
        with patch("backend.api.routes_ingest.delete_document", return_value=5):
            response = client.delete("/api/documents/doc.pdf")
        assert response.status_code == 200

    def test_delete_document_not_found_returns_404(self, client):
        """Supprimer un doc inexistant doit retourner 404."""
        with patch("backend.api.routes_ingest.delete_document", return_value=0):
            response = client.delete("/api/documents/inexistant.pdf")
        assert response.status_code == 404


# ── GET /api/history/{session_id} ──────────────────────────────────────────────

class TestGetHistory:
    def test_get_history_returns_200(self, client, history_store_tmp):
        """GET /api/history/{session_id} doit retourner 200."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-abc")
        assert response.status_code == 200

    def test_get_history_has_required_fields(self, client, history_store_tmp):
        """La réponse doit contenir session_id, messages et count."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-abc")
        data = response.json()
        assert "session_id" in data
        assert "messages" in data
        assert "count" in data

    def test_get_history_empty_session_returns_empty_list(self, client, history_store_tmp):
        """Une session sans messages doit retourner une liste vide."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-inexistante")
        data = response.json()
        assert data["messages"] == []
        assert data["count"] == 0

    def test_get_history_returns_saved_messages(self, client, history_store_tmp):
        """Les messages sauvegardés doivent être retournés dans l'ordre chronologique."""
        history_store_tmp.save_message("session-xyz", "user", "Bonjour")
        history_store_tmp.save_message("session-xyz", "assistant", "Bonjour à vous !")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-xyz")
        data = response.json()
        assert data["count"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][0]["content"] == "Bonjour"

    def test_get_history_session_id_matches(self, client, history_store_tmp):
        """Le session_id retourné doit correspondre à celui demandé."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/my-session-42")
        assert response.json()["session_id"] == "my-session-42"

    def test_get_history_with_limit(self, client, history_store_tmp):
        """Le paramètre ?limit=N doit limiter le nombre de messages retournés."""
        for i in range(5):
            history_store_tmp.save_message("session-limit", "user", f"Question {i}")
            history_store_tmp.save_message("session-limit", "assistant", f"Réponse {i}")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-limit?limit=4")
        data = response.json()
        assert data["count"] == 4

    def test_get_history_messages_have_role_and_content(self, client, history_store_tmp):
        """Chaque message doit avoir role, content et timestamp."""
        history_store_tmp.save_message("session-fields", "user", "Test champs")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/history/session-fields")
        msg = response.json()["messages"][0]
        assert "role" in msg
        assert "content" in msg
        assert "timestamp" in msg


# ── DELETE /api/history/{session_id} ───────────────────────────────────────────

class TestClearHistory:
    def test_clear_history_returns_200(self, client, history_store_tmp):
        """DELETE /api/history/{session_id} doit retourner 200."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.delete("/api/history/session-to-clear")
        assert response.status_code == 200

    def test_clear_history_response_has_status_cleared(self, client, history_store_tmp):
        """La réponse doit contenir status=cleared."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.delete("/api/history/session-del")
        data = response.json()
        assert data["status"] == "cleared"
        assert data["session_id"] == "session-del"

    def test_clear_history_actually_removes_messages(self, client, history_store_tmp):
        """Après DELETE, GET /history doit retourner une liste vide."""
        history_store_tmp.save_message("session-purge", "user", "À effacer")
        history_store_tmp.save_message("session-purge", "assistant", "Aussi")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            client.delete("/api/history/session-purge")
            response = client.get("/api/history/session-purge")
        assert response.json()["count"] == 0

    def test_clear_history_nonexistent_session_returns_200(self, client, history_store_tmp):
        """Effacer une session inexistante doit être silencieux (200, pas 404)."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.delete("/api/history/session-jamais-creee")
        assert response.status_code == 200

    def test_clear_history_does_not_affect_other_sessions(self, client, history_store_tmp):
        """Effacer session A ne doit pas toucher session B."""
        history_store_tmp.save_message("session-A", "user", "Message A")
        history_store_tmp.save_message("session-B", "user", "Message B")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            client.delete("/api/history/session-A")
            response = client.get("/api/history/session-B")
        assert response.json()["count"] == 1


# ── GET /api/sessions ──────────────────────────────────────────────────────────

class TestListSessions:
    def test_list_sessions_returns_200(self, client, history_store_tmp):
        """GET /api/sessions doit retourner 200."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        assert response.status_code == 200

    def test_list_sessions_has_sessions_and_count(self, client, history_store_tmp):
        """La réponse doit contenir sessions (liste) et count (entier)."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        data = response.json()
        assert "sessions" in data
        assert "count" in data
        assert isinstance(data["sessions"], list)

    def test_list_sessions_empty_when_no_history(self, client, history_store_tmp):
        """Sans messages enregistrés, sessions doit être vide."""
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        data = response.json()
        assert data["sessions"] == []
        assert data["count"] == 0

    def test_list_sessions_shows_created_sessions(self, client, history_store_tmp):
        """Les sessions avec messages doivent apparaître dans la liste."""
        history_store_tmp.save_message("s1", "user", "Message 1")
        history_store_tmp.save_message("s2", "user", "Message 2")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        data = response.json()
        assert data["count"] == 2
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert "s1" in session_ids
        assert "s2" in session_ids

    def test_list_sessions_has_message_count_per_session(self, client, history_store_tmp):
        """Chaque session doit avoir message_count et last_message_at."""
        history_store_tmp.save_message("s-meta", "user", "Q1")
        history_store_tmp.save_message("s-meta", "assistant", "R1")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        session = response.json()["sessions"][0]
        assert "message_count" in session
        assert "last_message_at" in session
        assert session["message_count"] == 2

    def test_list_sessions_ordered_by_most_recent(self, client, history_store_tmp):
        """Les sessions doivent être ordonnées par dernier message DESC."""
        history_store_tmp.save_message("old-session", "user", "Ancien")
        history_store_tmp.save_message("new-session", "user", "Récent")
        with patch("backend.api.routes_chat._history_store", history_store_tmp):
            response = client.get("/api/sessions")
        sessions = response.json()["sessions"]
        # La session la plus récente doit être en premier
        assert sessions[0]["session_id"] == "new-session"
