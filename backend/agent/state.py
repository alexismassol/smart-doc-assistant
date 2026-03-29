"""
agent/state.py - État typé de l'agent LangGraph (AgentState)
Uses: LangGraph (TypedDict state management), Python typing
L'AgentState est le seul objet qui transite entre tous les nœuds du graph.
"""
import uuid
from typing import List, Dict, Any
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    État partagé entre tous les nœuds du graph LangGraph.

    Chaque nœud reçoit cet état en entrée et retourne un dict
    avec les champs à mettre à jour (mise à jour partielle).

    Fields:
        question: Question posée par l'utilisateur.
        context: Chunks récupérés par retrieve_node (liste de dicts source+score).
        answer: Réponse générée par generate_node.
        sources: Sources formatées pour le frontend (subset de context).
        history: Historique de conversation [{role, content}, ...].
        confidence: Score moyen de pertinence des chunks retenus (0.0 à 1.0).
        session_id: Identifiant de session pour isoler les historiques.
    """
    question: str
    context: List[Dict[str, Any]]
    answer: str
    sources: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    confidence: float
    session_id: str


def create_initial_state(question: str, session_id: str | None = None) -> AgentState:
    """
    Crée un état initial valide pour une nouvelle question.

    Args:
        question: Question de l'utilisateur.
        session_id: ID de session (auto-généré si absent).

    Returns:
        AgentState prêt à être injecté dans le graph.
    """
    return AgentState(
        question=question,
        context=[],
        answer="",
        sources=[],
        history=[],
        confidence=0.0,
        session_id=session_id or str(uuid.uuid4()),
    )
