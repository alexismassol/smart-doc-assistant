# SPECS.md - Smart Doc Assistant

## Vision produit

**Smart Doc Assistant** est un agent IA conversationnel qui permet à un utilisateur d'interroger en langage naturel une base de documents hétérogènes (PDF, CSV, Markdown, pages web). Il retourne des réponses contextualisées accompagnées des sources exactes utilisées.

**Cas d'usage cible** : Une équipe DSI qui veut interroger sa documentation technique, ses logs, ses rapports internes sans moteur de recherche classique.

---

## Spécifications fonctionnelles

### SF-01 - Ingestion de documents

| ID | Fonctionnalité | Priorité |
|---|---|---|
| SF-01.1 | Upload de fichiers PDF via interface drag & drop | MUST |
| SF-01.2 | Upload de fichiers CSV (données tabulaires) | MUST |
| SF-01.3 | Upload de fichiers Markdown / TXT | MUST |
| SF-01.4 | Ingestion d'une URL (scraping de page web) | MUST |
| SF-01.5 | Feedback visuel de progression d'ingestion | SHOULD |
| SF-01.6 | Liste des documents ingérés avec statut | SHOULD |
| SF-01.7 | Suppression d'un document de la base | COULD |

**Règles métier :**
- Taille max fichier : 10 MB
- Un document déjà ingéré (même nom) est re-ingéré (écrase l'ancien)
- L'ingestion est asynchrone : l'utilisateur peut continuer à chatter pendant ce temps

---

### SF-02 - Conversation avec l'agent

| ID | Fonctionnalité | Priorité |
|---|---|---|
| SF-02.1 | Saisie d'une question en langage naturel | MUST |
| SF-02.2 | Réponse générée par le LLM basée sur les documents | MUST |
| SF-02.3 | Affichage des sources (chunks) utilisées pour la réponse | MUST |
| SF-02.4 | Historique de conversation dans la session | MUST |
| SF-02.5 | Réponse en streaming (caractère par caractère) | SHOULD |
| SF-02.6 | Indicateur "Je ne sais pas" si aucun doc pertinent | MUST |
| SF-02.7 | Bouton de reset de la conversation | SHOULD |
| SF-02.8 | Copie de la réponse en un clic | COULD |

**Règles métier :**
- Si aucun document n'est ingéré, l'agent répond : *"Aucun document chargé. Veuillez d'abord uploader des fichiers."*
- Si les documents ne contiennent pas de réponse, l'agent le dit explicitement - il n'invente pas
- Le contexte de conversation est conservé sur les 5 derniers échanges

---

### SF-03 - Interface utilisateur

| ID | Fonctionnalité | Priorité |
|---|---|---|
| SF-03.1 | Layout split : panneau upload à gauche, chat à droite | MUST |
| SF-03.2 | Dark mode par défaut | SHOULD |
| SF-03.3 | Responsive (desktop uniquement pour v1) | MUST |
| SF-03.4 | Affichage du LLM actif et du nombre de docs indexés | SHOULD |
| SF-03.5 | Score de pertinence visible sur chaque source | COULD |

---

## Spécifications techniques

### ST-01 - Pipeline d'ingestion (backend)

```
[Fichier / URL]
      ↓
  Loader (PyMuPDF / pandas / requests+BS4)
      ↓
  Chunker (RecursiveCharacterTextSplitter)
  → chunk_size = 500 tokens
  → chunk_overlap = 50 tokens
      ↓
  Embedder (nomic-embed-text via Ollama)
  → vecteur de dimension 768
      ↓
  ChromaDB (persistance locale)
  → collection: "smart_docs"
  → métadonnées: source, page, type, timestamp
```

**Choix techniques justifiés :**
- `chunk_size=500` : bon équilibre entre contexte et précision de retrieval
- `chunk_overlap=50` : évite de couper des phrases importantes en limite de chunk
- `nomic-embed-text` : modèle d'embedding open-source performant, tourne via Ollama

---

### ST-02 - Agent LangGraph

#### State (TypedDict)

```python
class AgentState(TypedDict):
    question: str           # question de l'utilisateur
    context: list[Document] # chunks récupérés par le retriever
    answer: str             # réponse générée
    sources: list[dict]     # métadonnées des sources (pour le frontend)
    history: list[dict]     # historique [{role, content}, ...]
    confidence: float       # score moyen de pertinence des chunks
```

#### Graph d'état

```
[START]
   ↓
[retrieve_node]     → similarity_search top-k=5 dans ChromaDB
   ↓
[rerank_node]       → filtre les chunks score < 0.4, trie par pertinence
   ↓
[memory_node]       → injecte les 5 derniers échanges dans le contexte
   ↓
[generate_node]     → appel LLM avec prompt structuré
   ↓
[END]               → retourne answer + sources
```

#### Prompt système (generate_node)

```
Tu es un assistant expert en analyse documentaire. 
Tu réponds UNIQUEMENT en te basant sur les documents fournis dans le contexte.
Si la réponse n'est pas dans les documents, réponds : 
"Je n'ai pas trouvé cette information dans les documents chargés."

Ne génère pas d'informations non présentes dans le contexte.
Cite toujours les sources que tu utilises.

Contexte documentaire :
{context}

Historique de conversation :
{history}
```

---

### ST-03 - API FastAPI

#### Endpoints

| Méthode | Route | Description | Body |
|---|---|---|---|
| POST | `/api/chat` | Envoie une question, reçoit réponse + sources | `{question, session_id}` |
| POST | `/api/upload` | Upload d'un fichier | `multipart/form-data` |
| POST | `/api/ingest-url` | Ingestion d'une URL | `{url}` |
| GET | `/api/documents` | Liste les docs ingérés | - |
| DELETE | `/api/documents/{id}` | Supprime un doc | - |
| GET | `/api/health` | Santé de l'API | - |

#### Réponse type `/api/chat`

```json
{
  "answer": "D'après le document technique v2.3, la limite est de 100 requêtes/minute.",
  "sources": [
    {
      "content": "La limite de taux est fixée à 100 req/min par défaut...",
      "source": "api-doc-v2.3.pdf",
      "page": 12,
      "score": 0.87
    }
  ],
  "confidence": 0.87,
  "latency_ms": 1240
}
```

---

### ST-04 - Frontend React

#### Composants

```
App.jsx
├── StatusBar          → LLM actif | docs indexés | latence
├── UploadPanel        → drag&drop + liste documents
│   └── DocumentItem   → nom, type, date, bouton suppr
└── ChatWindow         → zone principale
    ├── MessageList
    │   └── MessageBubble  → question ou réponse
    │       └── SourceCard → chunk source avec score
    └── InputBar       → champ texte + bouton envoi
```

#### Hooks custom

```javascript
// useChat.js
const { messages, sendMessage, isLoading, reset } = useChat()

// useUpload.js  
const { documents, uploadFile, ingestUrl, deleteDoc, isUploading } = useUpload()
```

---

### ST-05 - Configuration LLM (switchable)

```python
# config.py
class LLMConfig:
    provider: str  # "ollama" | "mistral" | "anthropic"
    
    def get_llm(self):
        if self.provider == "ollama":
            return ChatOllama(model="mistral", base_url=OLLAMA_URL)
        elif self.provider == "mistral":
            return ChatMistralAI(api_key=MISTRAL_KEY, model="mistral-small")
        elif self.provider == "anthropic":
            return ChatAnthropic(api_key=ANTHROPIC_KEY, model="claude-haiku-4-5")
```

---

## Contraintes non-fonctionnelles

| Contrainte | Valeur cible |
|---|---|
| Temps de réponse (génération) | < 5s en local avec Ollama |
| Temps d'ingestion PDF 10 pages | < 10s |
| Précision du retrieval (recall@5) | > 80% sur docs de test |
| Taille base vectorielle supportée | ~1000 documents (ChromaDB local) |
| Compatibilité OS | Linux, macOS, Windows (WSL) |

---

## Ce que ce projet démontre sur un CV

| Compétence | Où c'est visible |
|---|---|
| LangChain / LangGraph | `agent/graph.py`, `agent/nodes.py` |
| RAG (Retrieval Augmented Generation) | Pipeline complet ingest → retrieve → generate |
| Python avancé | Type hints, async FastAPI, dataclasses |
| APIs LLM (Mistral, Claude) | `config.py` switchable multi-provider |
| Bases vectorielles | ChromaDB avec persistance et métadonnées |
| Prompt engineering | Prompt système structuré dans `nodes.py` |
| React moderne | Hooks custom, composants fonctionnels |
| Architecture logicielle | Séparation claire des responsabilités |

---

## Hors scope (v1)

- Authentification utilisateur
- Multi-tenant (plusieurs utilisateurs)
- Fine-tuning de modèle
- Déploiement cloud (prévu v2)
- Base de données relationnelle (SQLite prévu v2 pour l'historique)
