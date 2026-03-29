"""
routes_chat.py - Endpoints FastAPI pour le chat avec l'agent RAG
Uses: FastAPI (APIRouter, Pydantic models), LangGraph agent (graph.py),
      agent/state.py (create_initial_state), history/store.py (SQLite persistance),
      time (latency_ms)
Endpoints:
  POST   /api/chat
  GET    /api/history/{session_id}
  DELETE /api/history/{session_id}
  GET    /api/sessions
"""
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.agent.graph import agent_graph
from backend.agent.state import create_initial_state
from backend.config import settings
from backend.history.store import HistoryStore

router = APIRouter(prefix="/api", tags=["chat"])

# ── Stockage en mémoire pour la fenêtre glissante agent (volatil, performance) ─
_session_histories: dict = {}

# ── Persistance SQLite (survie aux redémarrages) ──────────────────────────────
_history_store = HistoryStore(db_path=settings.history_db_path)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Corps de la requête POST /api/chat."""
    question: str = Field(..., min_length=1, description="Question de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session (auto-généré si absent)")

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La question ne peut pas être vide ou contenir uniquement des espaces.")
        return v.strip()


class SourceItem(BaseModel):
    """Source citée dans la réponse."""
    content: str
    source: str
    page: int
    score: float
    type: str


class ChatResponse(BaseModel):
    """Corps de la réponse POST /api/chat."""
    answer: str
    sources: List[SourceItem]
    confidence: float
    latency_ms: int
    session_id: str


class HistoryMessage(BaseModel):
    """Message dans l'historique persistant."""
    id: int
    session_id: str
    role: str
    content: str
    timestamp: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Envoie une question à l'agent LangGraph et retourne la réponse avec sources.

    L'agent exécute : retrieve_node → memory_node → generate_node.
    Deux niveaux de persistance :
    - En mémoire : fenêtre glissante pour le contexte LangGraph (window=5)
    - SQLite      : historique complet persistant (survie redémarrage)

    Args:
        request: ChatRequest avec question et session_id optionnel.

    Returns:
        ChatResponse avec answer, sources, confidence, latency_ms, session_id.
    """
    session_id = request.session_id or str(uuid.uuid4())
    history = _session_histories.get(session_id, [])

    # Création de l'état initial LangGraph
    state = create_initial_state(request.question, session_id)
    state["history"] = history

    # Invocation du graph LangGraph - mesure de latence
    start = time.monotonic()
    result = agent_graph.invoke(state)
    latency_ms = int((time.monotonic() - start) * 1000)

    answer = result["answer"]

    # ── Mise à jour mémoire in-process (contexte agent, fenêtre glissante) ───
    from backend.agent.memory import add_exchange, apply_sliding_window
    updated_history = add_exchange(history, request.question, answer)
    _session_histories[session_id] = apply_sliding_window(
        updated_history,
        window=settings.memory_window,
    )

    # ── Persistance SQLite (historique complet) ───────────────────────────────
    _history_store.save_message(session_id, "user", request.question)
    _history_store.save_message(session_id, "assistant", answer)

    sources = [SourceItem(**s) for s in result.get("sources", [])]

    return ChatResponse(
        answer=answer,
        sources=sources,
        confidence=result.get("confidence", 0.0),
        latency_ms=latency_ms,
        session_id=session_id,
    )


@router.get("/history/{session_id}")
async def get_history(session_id: str, limit: Optional[int] = None):
    """
    Retourne l'historique persistant SQLite d'une session.

    Args:
        session_id: Identifiant de session.
        limit: Nombre max de messages à retourner (les plus récents).

    Returns:
        Dict avec session_id, messages et count.
    """
    messages = _history_store.get_session_history(session_id, limit=limit)
    return {
        "session_id": session_id,
        "messages": messages,
        "count": len(messages),
    }


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    Efface l'historique SQLite et la mémoire in-process d'une session.

    Args:
        session_id: Identifiant de session.
    """
    _history_store.clear_session(session_id)
    _session_histories.pop(session_id, None)
    return {"session_id": session_id, "status": "cleared"}


@router.get("/sessions")
async def list_sessions():
    """
    Retourne la liste des sessions avec métadonnées (depuis SQLite).

    Returns:
        Liste de {session_id, message_count, last_message_at}.
    """
    sessions = _history_store.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}
