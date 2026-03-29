"""
test_agent.py - Session CLI interactive avec l'agent LangGraph
Uses: LangGraph StateGraph (agent/graph.py), ChromaDB, LLM (ollama/mistral/anthropic)
Usage: python scripts/test_agent.py
Prérequis : Ollama doit tourner, ChromaDB doit contenir des documents.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.agent.graph import build_graph
from backend.agent.state import create_initial_state
from backend.agent.memory import add_exchange
from backend.retrieval.vectorstore import get_collection_count


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║    Smart Doc Assistant - Agent CLI            ║")
    print("║    LangGraph + ChromaDB + Mistral/Ollama      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    count = get_collection_count()
    if count == 0:
        print("⚠️  ChromaDB vide - lancer d'abord : python scripts/test_ingest.py")
        return

    print(f"📊 {count} chunks disponibles dans ChromaDB")
    print("💬 Session interactive (Ctrl+C ou 'exit' pour quitter)\n")

    graph = build_graph()
    session_id = "cli-session"
    history = []

    while True:
        try:
            question = input("Vous : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Au revoir !")
            break

        if question.lower() in ("exit", "quit", "q"):
            print("👋 Au revoir !")
            break
        if not question:
            continue

        state = create_initial_state(question, session_id)
        state["history"] = history

        print("🤔 Traitement en cours...")
        result = graph.invoke(state)

        print(f"\n🤖 Assistant : {result['answer']}")
        print(f"   Confiance : {result['confidence']:.0%}")

        if result["sources"]:
            print(f"   Sources ({len(result['sources'])}) :")
            for s in result["sources"][:3]:
                print(f"   - {s['source']} p.{s['page']} (score: {s['score']:.2f})")

        print()
        history = add_exchange(history, question, result["answer"])


if __name__ == "__main__":
    main()
