"""
vectorstore.py - Client ChromaDB persistant pour Smart Doc Assistant
Uses: ChromaDB (PersistentClient, collection cosinus), Pydantic Settings v2
Fournit : accès collection, comptage, suppression, listing des sources.
"""
from typing import List, Dict, Any

import chromadb

from backend.config import settings


def get_collection(
    collection_name: str | None = None,
    chroma_path: str | None = None,
) -> chromadb.Collection:
    """
    Retourne la collection ChromaDB configurée (crée si inexistante).

    Utilise la similarité cosinus pour le calcul de distance - standard
    pour les modèles d'embedding de texte (nomic-embed-text dim 768).

    Args:
        collection_name: Nom de la collection (défaut: settings.chroma_collection).
        chroma_path: Chemin de persistance (défaut: settings.chroma_persist_dir).

    Returns:
        Collection ChromaDB prête à l'emploi.
    """
    col_name = collection_name or settings.chroma_collection
    path = chroma_path or settings.chroma_persist_dir

    # ChromaDB PersistentClient - données survivent aux redémarrages
    client = chromadb.PersistentClient(path=path)

    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},  # similarité cosinus pour embeddings texte
    )
    return collection


def get_collection_count(
    collection_name: str | None = None,
    chroma_path: str | None = None,
) -> int:
    """
    Retourne le nombre total de chunks stockés dans la collection.

    Args:
        collection_name: Nom de la collection (défaut: settings).
        chroma_path: Chemin ChromaDB (défaut: settings).

    Returns:
        Nombre de documents (chunks) dans la collection.
    """
    collection = get_collection(collection_name, chroma_path)
    return collection.count()


def delete_document(
    source: str,
    collection_name: str | None = None,
    chroma_path: str | None = None,
) -> int:
    """
    Supprime tous les chunks d'un document par son nom de source.

    Args:
        source: Nom du fichier source (ex: "rapport.pdf").
        collection_name: Nom de la collection (défaut: settings).
        chroma_path: Chemin ChromaDB (défaut: settings).

    Returns:
        Nombre de chunks supprimés.

    Raises:
        ValueError: Si source est vide.
    """
    if not source or not source.strip():
        raise ValueError("Le nom de la source ne peut pas être vide.")

    collection = get_collection(collection_name, chroma_path)

    # Récupère les IDs des chunks à supprimer
    results = collection.get(where={"source": source})
    ids_to_delete = results.get("ids", [])

    if ids_to_delete:
        collection.delete(where={"source": source})

    return len(ids_to_delete)


def list_sources(
    collection_name: str | None = None,
    chroma_path: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Liste les documents uniques indexés dans ChromaDB.

    Déduplique par nom de source - retourne une entrée par document,
    pas par chunk.

    Args:
        collection_name: Nom de la collection (défaut: settings).
        chroma_path: Chemin ChromaDB (défaut: settings).

    Returns:
        Liste de dicts avec source, type, chunk_count pour chaque document.
    """
    collection = get_collection(collection_name, chroma_path)
    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas", [])

    if not metadatas:
        return []

    # Déduplique et agrège les chunks par source
    sources: Dict[str, Dict[str, Any]] = {}
    for meta in metadatas:
        source = meta.get("source", "unknown")
        if source not in sources:
            sources[source] = {
                "source": source,
                "type": meta.get("type", "unknown"),
                "chunk_count": 0,
            }
        sources[source]["chunk_count"] += 1

    return list(sources.values())
