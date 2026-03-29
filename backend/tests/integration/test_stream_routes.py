"""
test_stream_routes.py - Tests d'intégration TDD pour l'endpoint SSE
Uses: FastAPI TestClient, unittest.mock, pytest
Couvre : POST /api/chat/stream - événements SSE token/sources/done
TDD Phase Red : ces tests échouent tant que l'endpoint n'existe pas.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def mock_retrieve_result():
    """Résultat de retrieve_with_confidence mocké."""
    sources = [
        {"content": "La limite de taux est 100 req/min.", "source": "api.pdf",
         "page": 1, "score": 0.87, "type": "pdf"}
    ]
    return sources, 0.87


def _make_stream_mock(tokens: list[str]):
    """
    Crée un async generator qui yield des chunks LangChain depuis une liste de tokens.
    Compatible avec llm.astream().
    """
    async def _gen(*args, **kwargs):
        for token in tokens:
            chunk = MagicMock()
            chunk.content = token
            yield chunk
    return _gen


# ── Structure de la réponse SSE ────────────────────────────────────────────────

class TestStreamEndpointExists:
    def test_stream_endpoint_returns_200(self, client, mock_retrieve_result):
        """POST /api/chat/stream doit exister et retourner 200."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Bonjour", " monde"])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Quelle est la limite ?"},
                headers={"Accept": "text/event-stream"},
            )
        assert response.status_code == 200

    def test_stream_endpoint_content_type_is_sse(self, client, mock_retrieve_result):
        """Content-Type doit être text/event-stream."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Hello"])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test"},
                headers={"Accept": "text/event-stream"},
            )
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_empty_question_returns_422(self, client):
        """Question vide doit retourner 422 - même validation que /api/chat."""
        response = client.post("/api/chat/stream", json={"question": ""})
        assert response.status_code == 422

    def test_stream_missing_question_returns_422(self, client):
        """Body sans question doit retourner 422."""
        response = client.post("/api/chat/stream", json={})
        assert response.status_code == 422


# ── Format des événements SSE ──────────────────────────────────────────────────

class TestStreamEventFormat:
    def _collect_events(self, response_text: str) -> list[dict]:
        """Parse les lignes SSE 'data: {...}' en liste de dicts."""
        events = []
        for line in response_text.splitlines():
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def test_stream_contains_token_events(self, client, mock_retrieve_result):
        """La réponse doit contenir des événements de type 'token'."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["La ", "limite ", "est ", "100."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Quelle est la limite ?"},
            )
        events = self._collect_events(response.text)
        token_events = [e for e in events if e.get("type") == "token"]
        assert len(token_events) > 0

    def test_stream_token_events_have_content_field(self, client, mock_retrieve_result):
        """Chaque événement token doit avoir un champ 'content'."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Token1", "Token2"])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test"},
            )
        events = self._collect_events(response.text)
        token_events = [e for e in events if e.get("type") == "token"]
        for event in token_events:
            assert "content" in event

    def test_stream_contains_sources_event(self, client, mock_retrieve_result):
        """La réponse doit contenir un événement de type 'sources'."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Réponse."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test sources"},
            )
        events = self._collect_events(response.text)
        sources_events = [e for e in events if e.get("type") == "sources"]
        assert len(sources_events) == 1

    def test_stream_sources_event_has_sources_list(self, client, mock_retrieve_result):
        """L'événement sources doit contenir une liste de sources."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Réponse."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test"},
            )
        events = self._collect_events(response.text)
        sources_event = next(e for e in events if e.get("type") == "sources")
        assert "sources" in sources_event
        assert isinstance(sources_event["sources"], list)

    def test_stream_sources_event_has_confidence(self, client, mock_retrieve_result):
        """L'événement sources doit contenir confidence et session_id."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Réponse."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test"},
            )
        events = self._collect_events(response.text)
        sources_event = next(e for e in events if e.get("type") == "sources")
        assert "confidence" in sources_event
        assert "session_id" in sources_event

    def test_stream_ends_with_done_event(self, client, mock_retrieve_result):
        """Le dernier événement doit être de type 'done'."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Fin."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test"},
            )
        events = self._collect_events(response.text)
        assert events[-1].get("type") == "done"

    def test_stream_tokens_reconstruct_full_answer(self, client, mock_retrieve_result):
        """La concaténation des tokens doit former la réponse complète."""
        sources, confidence = mock_retrieve_result
        expected_tokens = ["La ", "limite ", "est ", "100 req/min."]
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(expected_tokens)
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Limite ?"},
            )
        events = self._collect_events(response.text)
        token_events = [e for e in events if e.get("type") == "token"]
        full_answer = "".join(e["content"] for e in token_events)
        assert full_answer == "La limite est 100 req/min."

    def test_stream_session_id_auto_generated(self, client, mock_retrieve_result):
        """Sans session_id, un ID doit être auto-généré dans l'événement sources."""
        sources, confidence = mock_retrieve_result
        with patch("backend.api.routes_chat_stream.retrieve_with_confidence",
                   return_value=(sources, confidence)), \
             patch("backend.api.routes_chat_stream.settings") as mock_settings:
            mock_settings.memory_window = 5
            mock_settings.history_db_path = "/tmp/test_stream.db"
            mock_settings.get_llm.return_value = MagicMock(
                astream=_make_stream_mock(["Réponse."])
            )
            response = client.post(
                "/api/chat/stream",
                json={"question": "Test sans session"},
            )
        events = self._collect_events(response.text)
        sources_event = next(e for e in events if e.get("type") == "sources")
        assert len(sources_event["session_id"]) > 0
