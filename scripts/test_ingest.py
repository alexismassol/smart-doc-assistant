"""
test_ingest.py — Script CLI de test du pipeline d'ingestion complet
Uses: LangChain loaders, RecursiveCharacterTextSplitter, nomic-embed-text, ChromaDB
Usage: python scripts/test_ingest.py
Prérequis: Ollama doit tourner avec nomic-embed-text disponible
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.ingest.loader import load_markdown, load_csv
from backend.ingest.chunker import chunk_documents
from backend.ingest.embedder import embed_and_store


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║    Smart Doc Assistant — Test Ingestion       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    sample_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sample_docs")

    # ── 1. Chargement ─────────────────────────────────────────────────────────
    print("📄 Chargement des documents...")
    all_docs = []

    md_path = os.path.join(sample_dir, "example.md")
    if os.path.exists(md_path):
        md_docs = load_markdown(md_path)
        all_docs.extend(md_docs)
        print(f"   ✅ Markdown : {len(md_docs)} document(s)")

    csv_path = os.path.join(sample_dir, "example.csv")
    if os.path.exists(csv_path):
        csv_docs = load_csv(csv_path)
        all_docs.extend(csv_docs)
        print(f"   ✅ CSV      : {len(csv_docs)} document(s)")

    print(f"   Total chargé : {len(all_docs)} document(s)")
    print()

    # ── 2. Chunking ────────────────────────────────────────────────────────────
    print("✂️  Découpage en chunks (size=500, overlap=50)...")
    chunks = chunk_documents(all_docs)
    print(f"   ✅ {len(chunks)} chunks créés")
    print(f"   Exemple chunk 0 : {chunks[0].page_content[:100]}...")
    print()

    # ── 3. Embedding + ChromaDB ────────────────────────────────────────────────
    print("🧠 Génération des embeddings (nomic-embed-text) → ChromaDB...")
    print("   (peut prendre 30-60s selon les ressources disponibles)")
    count = embed_and_store(chunks)
    print(f"   ✅ {count} chunks stockés dans ChromaDB")
    print()

    print("╔══════════════════════════════════════════════╗")
    print("║  ✅  Pipeline d'ingestion validé !            ║")
    print("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
