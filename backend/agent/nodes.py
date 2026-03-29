"""
agent/nodes.py - Nœuds du graph LangGraph pour l'agent RAG
Uses: LangGraph (nœuds StateGraph), LangChain (ChatOllama / ChatMistralAI via config.py),
      ChromaDB via retrieval/retriever.py, Pydantic Settings v2
Nœuds : retrieve_node → memory_node → generate_node
"""
from typing import Dict, Any

from backend.agent.memory import apply_sliding_window, format_history_for_prompt
from backend.agent.state import AgentState
from backend.config import settings
from backend.retrieval.retriever import retrieve_with_confidence

# ── Prompt système ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant expert en analyse documentaire.
Tu réponds UNIQUEMENT en te basant sur les documents fournis dans le contexte ci-dessous.
Si la réponse n'est pas dans les documents, réponds exactement :
"Je n'ai pas trouvé cette information dans les documents chargés."

Ne génère jamais d'informations absentes du contexte.
Cite toujours la source (nom du fichier) que tu utilises.
Réponds en français."""


def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    Nœud 1 - Retrieval sémantique dans ChromaDB.

    Embed la question, recherche les chunks les plus proches,
    filtre par score threshold, retourne contexte + confidence.

    Args:
        state: État courant du graph (utilise state['question']).

    Returns:
        Mise à jour partielle : context, confidence.
    """
    question = state["question"]
    results, confidence = retrieve_with_confidence(question)
    return {
        "context": results,
        "confidence": confidence,
    }


def memory_node(state: AgentState) -> Dict[str, Any]:
    """
    Nœud 2 - Application de la fenêtre glissante sur l'historique.

    Tronque l'historique aux N derniers échanges (settings.memory_window)
    pour éviter un contexte LLM trop long.

    Args:
        state: État courant (utilise state['history']).

    Returns:
        Mise à jour partielle : history tronqué.
    """
    windowed = apply_sliding_window(
        state["history"],
        window=settings.memory_window,
    )
    return {"history": windowed}


def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    Nœud 3 - Génération de réponse via LLM (Ollama / Mistral / Claude).

    Construit le prompt avec contexte documentaire + historique,
    appelle le LLM configuré, retourne la réponse et les sources.

    Args:
        state: État courant (utilise context, history, question).

    Returns:
        Mise à jour partielle : answer, sources.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    context = state["context"]
    history_str = format_history_for_prompt(state["history"])

    # ── Construction du contexte documentaire ─────────────────────────────────
    if context:
        context_str = "\n\n".join([
            f"[Source: {r['source']}, page {r['page']}, score: {r['score']:.2f}]\n{r['content']}"
            for r in context
        ])
    else:
        context_str = "Aucun document pertinent trouvé."

    # ── Construction du prompt ─────────────────────────────────────────────────
    human_content = f"""Contexte documentaire :
{context_str}

{f"Historique de conversation :{chr(10)}{history_str}{chr(10)}" if history_str else ""}
Question : {state['question']}"""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    # ── Appel LLM (switchable via LLM_PROVIDER dans .env) ────────────────────
    llm = settings.get_llm()
    response = llm.invoke(messages)
    answer = response.content

    # Sources formatées pour le frontend (uniquement les champs utiles)
    sources = [
        {
            "content": r["content"],
            "source": r["source"],
            "page": r["page"],
            "score": r["score"],
            "type": r["type"],
        }
        for r in context
    ]

    return {
        "answer": answer,
        "sources": sources,
    }
