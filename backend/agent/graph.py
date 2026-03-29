"""
agent/graph.py - StateGraph LangGraph complet pour l'agent RAG
Uses: LangGraph (StateGraph, START, END, edges), agent/nodes.py, agent/state.py
Flow : START → retrieve_node → memory_node → generate_node → END
"""
from langgraph.graph import StateGraph, START, END

from backend.agent.nodes import retrieve_node, memory_node, generate_node
from backend.agent.state import AgentState


def build_graph():
    """
    Construit et compile le StateGraph LangGraph de l'agent RAG.

    Architecture du graph :
        START
          ↓
        retrieve_node  - similarity search ChromaDB (top-k, score filter)
          ↓
        memory_node    - fenêtre glissante sur l'historique (window=5)
          ↓
        generate_node  - génération LLM avec contexte + historique
          ↓
        END

    Returns:
        Graph compilé prêt à être invoqué avec graph.invoke(state).
    """
    # LangGraph StateGraph - state typé AgentState
    graph = StateGraph(AgentState)

    # ── Ajout des nœuds ────────────────────────────────────────────────────────
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("memory", memory_node)
    graph.add_node("generate", generate_node)

    # ── Edges (séquentiels) ────────────────────────────────────────────────────
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "memory")
    graph.add_edge("memory", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Instance globale - importée par les routes FastAPI
agent_graph = build_graph()
