# API Reference — Smart Doc Assistant

Backend FastAPI disponible sur `http://localhost:8000`
Documentation Swagger interactive : `http://localhost:8000/docs`

## Endpoints

### `GET /api/health`
Vérification de l'état du service.

**Response 200**
```json
{
  "status": "ok",
  "llm_provider": "ollama",
  "chroma_collection": "smart_docs",
  "documents_count": 42
}
```

---

### `POST /api/chat`
Envoie une question à l'agent RAG LangGraph.

**Request**
```json
{
  "question": "Quelle est la limite de taux de l'API ?",
  "session_id": "abc123"
}
```

**Response 200**
```json
{
  "answer": "D'après la documentation v2.3, la limite est de 100 req/min.",
  "sources": [
    {
      "content": "La limite de taux est fixée à 100 req/min par défaut...",
      "source": "api-doc.pdf",
      "page": 12,
      "score": 0.87
    }
  ],
  "confidence": 0.87,
  "latency_ms": 1240,
  "session_id": "abc123"
}
```

---

### `GET /api/history/{session_id}`
Historique **persistant SQLite** d'une session (survie aux redémarrages).

**Query params** : `?limit=20` (optionnel — retourne les N messages les plus récents)

**Response 200**
```json
{
  "session_id": "abc123",
  "messages": [
    {
      "id": 1,
      "session_id": "abc123",
      "role": "user",
      "content": "Quelle est la limite de taux ?",
      "timestamp": "2026-01-15T10:30:00+00:00"
    },
    {
      "id": 2,
      "session_id": "abc123",
      "role": "assistant",
      "content": "D'après la documentation...",
      "timestamp": "2026-01-15T10:30:02+00:00"
    }
  ],
  "count": 2
}
```

---

### `DELETE /api/history/{session_id}`
Efface l'historique SQLite et la mémoire in-process d'une session.

**Response 200**
```json
{ "session_id": "abc123", "status": "cleared" }
```

---

### `GET /api/sessions`
Liste toutes les sessions avec métadonnées (depuis SQLite).

**Response 200**
```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "message_count": 10,
      "last_message_at": "2026-01-15T10:30:02+00:00"
    }
  ],
  "count": 1
}
```

---

### `POST /api/upload`
Upload d'un fichier (PDF, CSV, Markdown).

**Request** : `multipart/form-data` avec champ `file`

**Response 200**
```json
{
  "filename": "rapport.pdf",
  "chunks_created": 23,
  "status": "ingested"
}
```

---

### `POST /api/ingest-url`
Ingestion d'une page web via URL.

**Request**
```json
{ "url": "https://docs.example.com/api" }
```

**Response 200**
```json
{
  "url": "https://docs.example.com/api",
  "chunks_created": 12,
  "status": "ingested"
}
```

---

### `GET /api/documents`
Liste tous les documents ingérés.

**Response 200**
```json
{
  "documents": [
    {
      "source": "rapport.pdf",
      "type": "pdf",
      "chunk_count": 23
    }
  ],
  "total": 1
}
```

---

### `DELETE /api/documents/{source}`
Supprime un document et ses chunks de ChromaDB. `source` = nom de fichier ou URL encodée.

**Response 200**
```json
{ "deleted": "rapport.pdf", "status": "ok" }
```

**Response 404** : Document introuvable.
