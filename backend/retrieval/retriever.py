"""
retriever.py — Retrieval sémantique avec reranking pour le pipeline RAG
Uses: ChromaDB (similarity search via vectorstore.py),
      LangChain OllamaEmbeddings (nomic-embed-text),
      Pydantic Settings v2 (top_k, score_threshold)
Pipeline : query → embedding → ChromaDB top-k → rerank (score ≥ threshold) → résultats triés
"""
from typing import List, Dict, Any, Tuple

from langchain_ollama import OllamaEmbeddings

from backend.config import settings
from backend.retrieval.vectorstore import get_collection


def similarity_search(
    query: str,
    top_k: int | None = None,
    collection_name: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Recherche sémantique dans ChromaDB par similarité cosinus.

    Pipeline :
    1. Embed la query via nomic-embed-text (Ollama)
    2. Requête ChromaDB top-k
    3. Convertit distances cosinus en scores [0, 1]
    4. Retourne les résultats triés par score décroissant

    Args:
        query: Question ou texte à rechercher.
        top_k: Nombre de résultats à retourner (défaut: settings.retrieval_top_k).
        collection_name: Collection ChromaDB (défaut: settings.chroma_collection).

    Returns:
        Liste de dicts avec content, source, page, type, score, chunk_index.
        Liste vide si query vide ou collection vide.
    """
    if not query or not query.strip():
        return []

    k = top_k or settings.retrieval_top_k

    # Embedding de la query — même modèle que l'ingestion (cohérence obligatoire)
    embeddings_model = OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    query_vector = embeddings_model.embed_query(query)

    # Requête ChromaDB — retourne distances cosinus (0 = identique, 2 = opposé)
    collection = get_collection(collection_name)
    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    if not documents:
        return []

    results = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Conversion distance cosinus → score similarité [0, 1]
        # ChromaDB cosinus : distance ∈ [0, 2] → score = 1 - distance/2
        score = round(max(0.0, 1.0 - dist / 2.0), 4)
        results.append({
            "content": doc,
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", 0),
            "type": meta.get("type", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "score": score,
        })

    # Tri par score décroissant — le plus pertinent en premier
    return sorted(results, key=lambda x: x["score"], reverse=True)


def rerank(
    results: List[Dict[str, Any]],
    score_threshold: float | None = None,
) -> List[Dict[str, Any]]:
    """
    Filtre les résultats de similarity_search par score minimum.

    Supprime les chunks peu pertinents (score < threshold) pour éviter
    que le LLM génère des réponses basées sur du contexte non pertinent.

    Args:
        results: Liste de résultats issus de similarity_search().
        score_threshold: Score minimum (défaut: settings.retrieval_score_threshold).

    Returns:
        Liste filtrée et triée par score décroissant.
    """
    threshold = score_threshold if score_threshold is not None \
        else settings.retrieval_score_threshold

    filtered = [r for r in results if r["score"] >= threshold]
    return sorted(filtered, key=lambda x: x["score"], reverse=True)


def retrieve(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
    collection_name: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Pipeline complet de retrieval : similarity search + rerank.

    Fonction principale utilisée par l'agent LangGraph.

    Args:
        query: Question de l'utilisateur.
        top_k: Nombre de candidats à récupérer (défaut: settings.retrieval_top_k).
        score_threshold: Score minimum pour garder un chunk (défaut: settings).
        collection_name: Collection ChromaDB (défaut: settings.chroma_collection).

    Returns:
        Liste de chunks pertinents (filtrés, triés par score).
        Liste vide si query vide ou aucun résultat pertinent.
    """
    if not query or not query.strip():
        return []

    candidates = similarity_search(query, top_k=top_k, collection_name=collection_name)
    return rerank(candidates, score_threshold=score_threshold)


def retrieve_with_confidence(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
    collection_name: str | None = None,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Pipeline retrieve avec score de confiance moyen.

    Retourne les chunks pertinents ET un score de confiance global
    (moyenne des scores des chunks retenus), utilisé par l'agent pour
    décider si la réponse est fiable.

    Args:
        query: Question de l'utilisateur.
        top_k: Nombre de candidats (défaut: settings).
        score_threshold: Seuil de filtrage (défaut: settings).
        collection_name: Collection ChromaDB (défaut: settings).

    Returns:
        Tuple (résultats, confidence) où confidence ∈ [0.0, 1.0].
    """
    results = retrieve(query, top_k=top_k, score_threshold=score_threshold,
                       collection_name=collection_name)

    if not results:
        return [], 0.0

    confidence = round(sum(r["score"] for r in results) / len(results), 4)
    return results, confidence
