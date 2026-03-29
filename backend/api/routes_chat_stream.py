"""
routes_chat_stream.py - Endpoint SSE pour le streaming de réponses
Uses: FastAPI (StreamingResponse), LangChain (llm.astream()),
      retrieval/retriever.py, history/store.py (SQLite),
      agent/memory.py (fenêtre glissante)

Endpoint :
  POST /api/chat/stream - Streaming token-by-token via Server-Sent Events

Format SSE :
  data: {"type": "token",   "content": "La "}
  data: {"type": "token",   "content": "limite "}
  data: {"type": "sources", "sources": [...], "confidence": 0.87, "session_id": "uuid"}
  data: {"type": "done"}
"""
import json
import uuid
from typing import AsyncIterator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from backend.agent.memory import add_exchange, apply_sliding_window, format_history_for_prompt
from backend.config import settings
from backend.history.store import HistoryStore
from backend.retrieval.retriever import retrieve_with_confidence

router = APIRouter(prefix="/api", tags=["chat-stream"])

# ── Stockage en mémoire (fenêtre glissante agent) ─────────────────────────────
_stream_session_histories: dict = {}

# ── Persistance SQLite ────────────────────────────────────────────────────────
_history_store = HistoryStore(db_path=settings.history_db_path)

# ── Prompt système (identique à routes_chat.py) ───────────────────────────────
_SYSTEM_PROMPT = """Tu es un assistant expert en analyse documentaire.
Tu réponds UNIQUEMENT en te basant sur les documents fournis dans le contexte ci-dessous.
Si la réponse n'est pas dans les documents, réponds exactement :
"Je n'ai pas trouvé cette information dans les documents chargés."

Ne génère jamais d'informations absentes du contexte.
Cite toujours la source (nom du fichier) que tu utilises.
Réponds en français."""


class StreamChatRequest(BaseModel):
    """Corps de la requête POST /api/chat/stream."""
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(None)

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La question ne peut pas être vide.")
        return v.strip()


def _build_prompt(question: str, context: list[dict], history: list) -> list:
    """
    Construit les messages LangChain pour la génération.

    Args:
        question: Question de l'utilisateur.
        context: Chunks récupérés depuis ChromaDB.
        history: Historique de conversation fenêtré.

    Returns:
        Liste de messages [SystemMessage, HumanMessage].
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    if context:
        context_str = "\n\n".join([
            f"[Source: {r['source']}, page {r['page']}, score: {r['score']:.2f}]\n{r['content']}"
            for r in context
        ])
    else:
        context_str = "Aucun document pertinent trouvé."

    history_str = format_history_for_prompt(history)
    human_content = f"""Contexte documentaire :
{context_str}

{f"Historique de conversation :{chr(10)}{history_str}{chr(10)}" if history_str else ""}
Question : {question}"""

    return [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


async def _stream_response(request: StreamChatRequest) -> AsyncIterator[str]:
    """
    Générateur async qui yield les événements SSE.

    Séquence :
        1. Retrieve → ChromaDB similarity search
        2. Stream LLM → yield événements 'token' un par un
        3. Persist → SQLite + mémoire in-process
        4. yield événement 'sources' avec métadonnées
        5. yield événement 'done'

    Args:
        request: StreamChatRequest avec question et session_id optionnel.

    Yields:
        Chaînes formatées SSE : "data: {...}\n\n"
    """
    session_id = request.session_id or str(uuid.uuid4())
    history = _stream_session_histories.get(session_id, [])

    # ── Étape 1 : Retrieve ─────────────────────────────────────────────────────
    context, confidence = retrieve_with_confidence(request.question)

    # Sources formatées pour le frontend
    sources = [
        {"content": r["content"], "source": r["source"],
         "page": r["page"], "score": r["score"], "type": r["type"]}
        for r in context
    ]

    # ── Étape 2 : Fenêtre mémoire ─────────────────────────────────────────────
    windowed_history = apply_sliding_window(history, window=settings.memory_window)
    messages = _build_prompt(request.question, context, windowed_history)

    # ── Étape 3 : Streaming LLM token par token ───────────────────────────────
    llm = settings.get_llm()
    full_answer = ""

    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    # ── Étape 4 : Persistance ─────────────────────────────────────────────────
    updated_history = add_exchange(history, request.question, full_answer)
    _stream_session_histories[session_id] = apply_sliding_window(
        updated_history, window=settings.memory_window
    )
    _history_store.save_message(session_id, "user", request.question)
    _history_store.save_message(session_id, "assistant", full_answer)

    # ── Étape 5 : Événement sources ───────────────────────────────────────────
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'confidence': confidence, 'session_id': session_id})}\n\n"

    # ── Étape 6 : Événement done ──────────────────────────────────────────────
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat/stream")
async def stream_chat(request: StreamChatRequest) -> StreamingResponse:
    """
    Streaming token-by-token de la réponse LLM via Server-Sent Events.

    Contrairement à POST /api/chat (réponse complète), cet endpoint stream
    chaque token dès qu'il est généré, pour un effet "typewriter" dans l'UI.

    Événements SSE émis :
        - type=token   : un token de la réponse, champ 'content'
        - type=sources : sources CitéEs + confidence + session_id (une fois, à la fin)
        - type=done    : signal de fin de stream

    Args:
        request: StreamChatRequest avec question et session_id optionnel.

    Returns:
        StreamingResponse text/event-stream.
    """
    return StreamingResponse(
        _stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Désactive le buffering nginx
        },
    )
