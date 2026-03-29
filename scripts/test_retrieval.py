"""
test_retrieval.py - Script CLI de test du retrieval sémantique
Uses: ChromaDB (similarity search), nomic-embed-text (Ollama), retriever.py
Usage: python scripts/test_retrieval.py
Prérequis : Ollama doit tourner, nomic-embed-text disponible,
            ChromaDB doit contenir des documents (lancer test_ingest.py d'abord)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.retrieval.retriever import retrieve_with_confidence
from backend.retrieval.vectorstore import get_collection_count, list_sources


QUESTIONS_TEST = [
    "Quelle est la limite de taux de l'API ?",
    "Comment configurer le provider LLM ?",
    "Quels formats de documents sont supportés ?",
]


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║    Smart Doc Assistant - Test Retrieval       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # ── État de la collection ──────────────────────────────────────────────────
    count = get_collection_count()
    sources = list_sources()
    print(f"📊 Collection ChromaDB : {count} chunks | {len(sources)} document(s)")
    for src in sources:
        print(f"   - {src['source']} ({src['type']}, {src['chunk_count']} chunks)")
    print()

    if count == 0:
        print("⚠️  Collection vide - lancer d'abord : python scripts/test_ingest.py")
        return

    # ── 3 questions de test ────────────────────────────────────────────────────
    for i, question in enumerate(QUESTIONS_TEST, 1):
        print(f"❓ Question {i} : {question}")
        results, confidence = retrieve_with_confidence(question)

        if not results:
            print("   → Aucun résultat pertinent (score < threshold)")
        else:
            print(f"   → {len(results)} chunk(s) | confiance : {confidence:.2f}")
            for j, r in enumerate(results[:3], 1):
                print(f"   [{j}] score={r['score']:.3f} | {r['source']} p.{r['page']}")
                print(f"       {r['content'][:100]}...")
        print()

    print("╔══════════════════════════════════════════════╗")
    print("║  ✅  Retrieval validé !                       ║")
    print("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
