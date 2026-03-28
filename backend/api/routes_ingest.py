"""
routes_ingest.py — Endpoints FastAPI pour l'ingestion de documents
Uses: FastAPI (APIRouter, UploadFile, File), LangChain loaders (ingest/loader.py),
      ChromaDB (ingest/embedder.py, retrieval/vectorstore.py)
Endpoints: POST /api/upload, POST /api/ingest-url, GET /api/documents, DELETE /api/documents/{source}
"""
import os
import re
import tempfile
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, HttpUrl, field_validator

from backend.ingest.chunker import chunk_documents
from backend.ingest.embedder import embed_and_store
from backend.ingest.loader import load_document, load_url
from backend.retrieval.vectorstore import get_collection_count, list_sources, delete_document

router = APIRouter(prefix="/api", tags=["ingest"])

# Formats de fichiers acceptés
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".md", ".txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Pydantic models ───────────────────────────────────────────────────────────

class IngestUrlRequest(BaseModel):
    """Corps de la requête POST /api/ingest-url."""
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v) -> HttpUrl:
        url_str = str(v)
        if not url_str.startswith(("http://", "https://")):
            raise ValueError("L'URL doit commencer par http:// ou https://")
        return v


class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    status: str


class IngestUrlResponse(BaseModel):
    url: str
    chunks_created: int
    status: str


class DocumentItem(BaseModel):
    source: str
    type: str
    chunk_count: int


class DocumentsResponse(BaseModel):
    documents: List[DocumentItem]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload et ingestion d'un fichier (PDF, CSV, Markdown, TXT).

    Pipeline : fichier → temp disk → loader → chunker → embedder → ChromaDB.

    Args:
        file: Fichier uploadé via multipart/form-data.

    Returns:
        UploadResponse avec filename, chunks_created, status.

    Raises:
        400: Format non supporté ou fichier vide.
        500: Erreur interne lors de l'ingestion.
    """
    # Sanitisation du nom de fichier — supprime les caractères dangereux (path traversal, null bytes)
    raw_name = file.filename or "unknown"
    filename = re.sub(r'[^a-zA-Z0-9._\-]', '_', os.path.basename(raw_name))[:255]
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {ext}. Formats acceptés : {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Lecture et validation taille
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 MB).")

    # Sauvegarde temporaire sur disque (loaders LangChain lisent depuis le filesystem)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        docs = load_document(tmp_path)
        # Correction du nom de source (utiliser le vrai nom, pas le path temp)
        for doc in docs:
            doc.metadata["source"] = filename

        chunks = chunk_documents(docs)
        count = embed_and_store(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion : {str(e)}")
    finally:
        os.unlink(tmp_path)

    return UploadResponse(filename=filename, chunks_created=count, status="ingested")


@router.post("/ingest-url", response_model=IngestUrlResponse)
async def ingest_url(request: IngestUrlRequest) -> IngestUrlResponse:
    """
    Ingestion d'une page web via son URL.

    Pipeline : URL → httpx+BeautifulSoup4 → chunker → embedder → ChromaDB.

    Args:
        request: IngestUrlRequest avec url validée.

    Returns:
        IngestUrlResponse avec url, chunks_created, status.

    Raises:
        400: URL inaccessible ou contenu vide.
    """
    url_str = str(request.url)
    try:
        docs = load_url(url_str)
        chunks = chunk_documents(docs)
        count = embed_and_store(chunks)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion URL : {str(e)}")

    return IngestUrlResponse(url=url_str, chunks_created=count, status="ingested")


@router.get("/documents", response_model=DocumentsResponse)
async def get_documents() -> DocumentsResponse:
    """
    Liste tous les documents ingérés dans ChromaDB.

    Returns:
        DocumentsResponse avec liste des documents et total.
    """
    sources = list_sources()
    items = [DocumentItem(**s) for s in sources]
    return DocumentsResponse(documents=items, total=len(items))


@router.delete("/documents/{source}")
async def delete_doc(source: str):
    """
    Supprime un document et tous ses chunks de ChromaDB.

    Args:
        source: Nom du fichier source (ex: "rapport.pdf").

    Returns:
        Confirmation avec nombre de chunks supprimés.

    Raises:
        404: Document non trouvé dans ChromaDB.
    """
    deleted_count = delete_document(source)
    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{source}' non trouvé dans la base vectorielle."
        )
    return {"deleted": source, "chunks_removed": deleted_count, "status": "ok"}
