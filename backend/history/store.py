"""
store.py — Persistance SQLite de l'historique de conversation
Uses: sqlite3 (stdlib Python) — aucune dépendance externe requise

Responsabilités :
- Créer et initialiser la table `messages` à l'instanciation
- Sauvegarder chaque échange (question + réponse) avec timestamp auto
- Récupérer l'historique d'une session avec pagination
- Lister toutes les sessions actives
- Effacer l'historique d'une session

Le fichier SQLite est stocké dans data/history.db (configuré via config.py).
En test, on passe db_path=/tmp/xxx pour l'isolation.
"""

import sqlite3
import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# DDL de la table — créée si elle n'existe pas (IF NOT EXISTS = idempotent)
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
    content     TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL
)
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)
"""


class HistoryStore:
    """
    Persistance SQLite des échanges conversationnels.

    Un message = une ligne dans la table `messages`.
    Chaque session est identifiée par un session_id (UUID).

    Args:
        db_path: Chemin vers le fichier SQLite. Créé automatiquement si absent.

    Example:
        store = HistoryStore(db_path="data/history.db")
        store.save_message("abc-123", "user", "Quelle est la limite de taux ?")
        messages = store.get_session_history("abc-123")
    """

    def __init__(self, db_path: str = "data/history.db") -> None:
        self.db_path = db_path
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()
        logger.info("HistoryStore initialisé → %s", db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Retourne une connexion SQLite avec row_factory pour les dicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Crée la table et l'index si absents. Idempotent."""
        with self._get_connection() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.execute(_CREATE_INDEX_SQL)
            conn.commit()

    def save_message(self, session_id: str, role: str, content: str) -> None:
        """
        Persiste un message dans la base.

        Args:
            session_id: Identifiant unique de la session (UUID).
            role: 'user' ou 'assistant'.
            content: Texte du message.

        Raises:
            ValueError: Si role n'est pas 'user' ou 'assistant'.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"role invalide : '{role}'. Doit être 'user' ou 'assistant'.")
        if not content:
            raise ValueError("content ne peut pas être vide.")

        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, timestamp),
            )
            conn.commit()

    def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Retourne les messages d'une session dans l'ordre chronologique.

        Args:
            session_id: Identifiant de la session.
            limit: Nombre max de messages (les plus récents si limit est spécifié).

        Returns:
            Liste de dicts : {id, session_id, role, content, timestamp}.
            Liste vide si la session n'existe pas.
        """
        with self._get_connection() as conn:
            if limit is not None:
                # Récupérer les `limit` plus récents, puis retrier ASC
                rows = conn.execute(
                    """
                    SELECT * FROM (
                        SELECT id, session_id, role, content, timestamp
                        FROM messages
                        WHERE session_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                    ) ORDER BY id ASC
                    """,
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, session_id, role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
                    (session_id,),
                ).fetchall()
        return [dict(row) for row in rows]

    def list_sessions(self) -> list[dict]:
        """
        Retourne la liste des sessions avec métadonnées.

        Returns:
            Liste de dicts : {session_id, message_count, last_message_at}.
            Ordonnée par dernier message DESC.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    session_id,
                    COUNT(*) AS message_count,
                    MAX(timestamp) AS last_message_at
                FROM messages
                GROUP BY session_id
                ORDER BY last_message_at DESC
                """,
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_session(self, session_id: str) -> None:
        """
        Supprime tous les messages d'une session.

        Args:
            session_id: Session à effacer. Si inexistante, opération silencieuse.
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()
