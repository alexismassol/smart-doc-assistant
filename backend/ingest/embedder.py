"""
embedder.py — Génération d'embeddings et stockage dans ChromaDB
Uses: LangChain OllamaEmbeddings (nomic-embed-text via Ollama),
      ChromaDB (base vectorielle persistante)
"""
import hashlib
from datetime import datetime, timezone
from typing import List

import chromadb
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from backend.config import settings


def embed_and_store(
    documents: List[Document],
    collection_name: str | None = None,
    chroma_path: str | None = None,
) -> int:
    """
    Génère les embeddings et stocke les Documents dans ChromaDB.

    Pipeline :
    1. Génère les vecteurs via nomic-embed-text (Ollama)
    2. Crée ou ouvre la collection ChromaDB
    3. Stocke textes + vecteurs + métadonnées

    Args:
        documents: Liste de Documents LangChain à embedder.
        collection_name: Nom de la collection ChromaDB (défaut: settings).
        chroma_path: Chemin de persistance ChromaDB (défaut: settings).

    Returns:
        Nombre de chunks stockés.
    """
    if not documents:
        return 0

    col_name = collection_name or settings.chroma_collection
    path = chroma_path or settings.chroma_persist_dir

    # LangChain OllamaEmbeddings — modèle nomic-embed-text (dim 768)
    embeddings_model = OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )

    # Génération des vecteurs
    texts = [doc.page_content for doc in documents]
    vectors = embeddings_model.embed_documents(texts)

    # ChromaDB — client persistant local
    client = chromadb.PersistentClient(path=path)
    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},  # similarité cosinus
    )

    # Préparation des données pour ChromaDB
    ids = []
    metadatas = []
    timestamp = datetime.now(timezone.utc).isoformat()

    for doc in documents:
        # ID déterministe basé sur le contenu (évite les doublons)
        doc_id = hashlib.md5(
            (doc.page_content + doc.metadata.get("source", "")).encode()
        ).hexdigest()
        ids.append(doc_id)

        meta = {
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page", 0),
            "type": doc.metadata.get("type", "unknown"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "timestamp": timestamp,
        }
        metadatas.append(meta)

    # Stockage dans ChromaDB (upsert = écrase si déjà présent)
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=vectors,
        metadatas=metadatas,
    )

    return len(documents)
