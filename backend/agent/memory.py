"""
agent/memory.py - Gestion de la mémoire de conversation (fenêtre glissante)
Uses: LangGraph state (history field), fenêtre glissante configurable
La mémoire garde les N derniers échanges pour maintenir le contexte conversationnel.
"""
from typing import List, Dict, Any


def add_exchange(
    history: List[Dict[str, Any]],
    question: str,
    answer: str,
) -> List[Dict[str, Any]]:
    """
    Ajoute un échange (question + réponse) à l'historique.

    Args:
        history: Historique existant.
        question: Question de l'utilisateur.
        answer: Réponse de l'assistant.

    Returns:
        Nouvel historique avec l'échange ajouté.

    Raises:
        ValueError: Si question ou answer est vide.
    """
    if not question or not question.strip():
        raise ValueError("La question ne peut pas être vide.")
    if not answer or not answer.strip():
        raise ValueError("La réponse ne peut pas être vide.")

    return history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]


def apply_sliding_window(
    history: List[Dict[str, Any]],
    window: int = 5,
) -> List[Dict[str, Any]]:
    """
    Applique une fenêtre glissante sur l'historique.

    Conserve uniquement les N derniers échanges (window × 2 messages)
    pour éviter que le contexte LLM ne devienne trop long.

    Args:
        history: Historique complet (liste de messages {role, content}).
        window: Nombre d'échanges (paires user/assistant) à conserver.

    Returns:
        Historique tronqué aux window derniers échanges.
    """
    if not history:
        return []

    max_messages = window * 2  # 1 échange = 2 messages (user + assistant)
    return history[-max_messages:]


def format_history_for_prompt(
    history: List[Dict[str, Any]],
) -> str:
    """
    Formate l'historique de conversation en string lisible pour le prompt LLM.

    Args:
        history: Liste de messages {role, content}.

    Returns:
        String formatée, vide si historique vide.
    """
    if not history:
        return ""

    lines = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"Utilisateur : {content}")
        elif role == "assistant":
            lines.append(f"Assistant : {content}")

    return "\n".join(lines)
