"""
main.py — Point d'entrée FastAPI pour Smart Doc Assistant
Uses: FastAPI (app, CORS, lifespan), Uvicorn (ASGI server),
      Pydantic Settings v2 (config.py), LangGraph agent (agent/graph.py)
Routes : /api/chat, /api/upload, /api/ingest-url, /api/documents, /api/health
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_chat import router as chat_router
from backend.api.routes_chat_stream import router as chat_stream_router
from backend.api.routes_ingest import router as ingest_router, get_collection_count
from backend.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan FastAPI — exécuté au démarrage et à l'arrêt.
    Initialise la connexion ChromaDB au boot pour détecter les erreurs tôt.
    """
    # Démarrage : vérification ChromaDB
    try:
        count = get_collection_count()
        logger.info(f"ChromaDB connecté — {count} chunks dans '{settings.chroma_collection}'")
    except Exception as e:
        logger.warning(f"ChromaDB non disponible au démarrage : {e}")

    yield  # L'app tourne ici

    # Arrêt
    logger.info("Smart Doc Assistant arrêté")


# ── Application FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Doc Assistant API",
    description="""
Agent RAG conversationnel — interrogez vos documents en langage naturel.

**Stack** : LangGraph · LangChain · ChromaDB · Mistral/Ollama · FastAPI

**Endpoints principaux** :
- `POST /api/chat` — Question → réponse + sources citées
- `POST /api/upload` — Upload document (PDF, CSV, MD)
- `POST /api/ingest-url` — Ingestion page web
- `GET /api/documents` — Liste des documents indexés
""",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# allow_origin_regex couvre tout le réseau local (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
# pour permettre l'accès depuis téléphone/tablette sur le même Wi-Fi.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_origin_regex=r"http://(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(chat_router)
app.include_router(chat_stream_router)
app.include_router(ingest_router)


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health():
    """
    Vérification de l'état du service.
    Retourne le provider LLM actif et le nombre de documents indexés.
    """
    try:
        from backend.api.routes_ingest import get_collection_count
        count = get_collection_count()
    except Exception:
        count = -1

    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "chroma_collection": settings.chroma_collection,
        "documents_count": count,
    }
