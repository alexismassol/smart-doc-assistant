# Documentation technique - Smart Doc Assistant

## Présentation

Smart Doc Assistant est un agent IA de type RAG (Retrieval Augmented Generation).
Il permet d'interroger une base de documents hétérogènes en langage naturel et d'obtenir des réponses précises avec citation des sources originales.

L'application est conçue pour les équipes techniques qui souhaitent capitaliser sur leurs bases de connaissance internes (documentation, rapports, wikis) sans exposer leurs données à des services cloud externes.

## Architecture technique

### Orchestration avec LangGraph

Le cœur de l'agent est un StateGraph LangGraph composé de 4 nœuds séquentiels :

1. **retrieve_node** : Interroge ChromaDB pour récupérer les top-k chunks les plus proches de la question (similarité cosinus, k=5 par défaut).
2. **rerank_node** : Filtre les chunks dont le score de pertinence est inférieur au seuil (0.4 par défaut) et retrie par pertinence décroissante.
3. **memory_node** : Injecte les 5 derniers échanges de la conversation dans le contexte pour maintenir la cohérence du dialogue.
4. **generate_node** : Génère la réponse finale via le LLM configuré, en s'appuyant uniquement sur les chunks récupérés.

### Pipeline d'ingestion

Le pipeline d'ingestion transforme les documents bruts en vecteurs stockés dans ChromaDB :

1. **Chargement** : PyMuPDF pour les PDF, pandas pour les CSV, lecture directe pour les fichiers Markdown et TXT, httpx + BeautifulSoup4 pour les URLs.
2. **Découpage** : RecursiveCharacterTextSplitter de LangChain - taille de chunk : 500 tokens, overlap : 50 tokens.
3. **Embedding** : nomic-embed-text via Ollama - modèle open-source, performant, 100% local.
4. **Stockage** : ChromaDB persistant dans `./data/chroma_db` avec métadonnées (source, page, type, timestamp).

### Stockage vectoriel avec ChromaDB

ChromaDB est utilisé comme vector store persistant. La collection `smart_docs` stocke les embeddings avec leurs métadonnées associées. La recherche de similarité est effectuée via l'algorithme HNSW (Hierarchical Navigable Small World) qui offre un excellent compromis entre vitesse et précision.

### Persistance de l'historique avec SQLite

Chaque échange (question + réponse) est persisté dans une base SQLite locale (`./data/history.db`). Cela permet de retrouver l'historique complet d'une session même après un redémarrage du serveur. En parallèle, un dictionnaire en mémoire maintient une fenêtre glissante de 5 échanges pour le contexte de l'agent LangGraph.

## Configuration

La configuration se fait via le fichier `.env` à la racine du projet.

### Provider LLM

Le provider LLM est entièrement configurable via la variable `LLM_PROVIDER` :
- `ollama` : Mistral 7B local via Ollama (mode développement, gratuit, offline)
- `mistral` : Mistral API `mistral-small-latest` (mode production, nécessite une clé API)
- `anthropic` : Claude Haiku via l'API Anthropic (mode démonstration multi-provider)

### Paramètres de retrieval

- `RETRIEVAL_TOP_K=5` : Nombre de chunks retournés par la recherche vectorielle
- `RETRIEVAL_SCORE_THRESHOLD=0.4` : Score minimum de pertinence (chunks en dessous ignorés)
- `MEMORY_WINDOW=5` : Nombre d'échanges conservés dans la fenêtre glissante de mémoire

### Paramètres de chunking

- `chunk_size=500` : Taille maximale d'un chunk en tokens
- `chunk_overlap=50` : Overlap entre chunks consécutifs pour éviter les coupures de contexte

## API REST

L'API est exposée par FastAPI sur le port 8000. La documentation Swagger interactive est disponible sur `/docs`.

### Endpoint principal : POST /api/chat

Envoie une question à l'agent et reçoit une réponse avec sources citées.

Corps de la requête :
- `question` (string, requis) : La question en langage naturel
- `session_id` (string, optionnel) : Identifiant de session, auto-généré si absent

Réponse :
- `answer` : Réponse générée par le LLM
- `sources` : Liste des chunks sources avec score de pertinence
- `confidence` : Score de confiance moyen des sources
- `latency_ms` : Latence de génération en millisecondes
- `session_id` : Identifiant de la session utilisée

### Endpoints d'ingestion

- `POST /api/upload` : Upload d'un fichier (PDF, CSV, MD, TXT) en multipart/form-data
- `POST /api/ingest-url` : Ingestion d'une page web via son URL
- `GET /api/documents` : Liste des documents indexés avec leur nombre de chunks
- `DELETE /api/documents/{source}` : Supprime un document et ses chunks de ChromaDB

### Endpoints d'historique

- `GET /api/history/{session_id}` : Historique complet d'une session (paramètre `?limit=N` disponible)
- `DELETE /api/history/{session_id}` : Efface l'historique d'une session
- `GET /api/sessions` : Liste toutes les sessions avec leur nombre de messages et date du dernier message

## Limites et contraintes

La taille maximale d'un fichier uploadé est de 10 MB. Les formats supportés sont : PDF, CSV, Markdown (.md), texte brut (.txt).

Le contexte de conversation est conservé sur les 5 derniers échanges (configurable via MEMORY_WINDOW). Pour des questions nécessitant un contexte plus long, augmenter cette valeur.

Le score de pertinence minimum pour un chunk est de 0.4. En dessous de ce seuil, le chunk est écarté. Si aucun chunk ne dépasse ce seuil, l'agent indique qu'il n'a pas trouvé d'information pertinente dans la base documentaire.

En mode Ollama local, la latence dépend des capacités de la machine. Sur un MacBook M2, une réponse Mistral 7B prend entre 3 et 8 secondes. En mode Mistral API, la latence est typiquement de 400 à 800 ms.

## Installation et démarrage

### Prérequis

- Python 3.11+
- Node.js 18+
- Ollama installé et démarré (`ollama serve`)
- Modèles téléchargés : `ollama pull mistral` et `ollama pull nomic-embed-text`

### Démarrage rapide

Cloner le projet, copier `.env.example` vers `.env`, puis lancer `npm run setup` suivi de `npm start`. L'interface est accessible sur http://localhost:5173 et l'API sur http://localhost:8000/docs.

### Démarrage avec Docker

La commande `docker compose -f docker/docker-compose.yml up --build` démarre les 3 services : backend FastAPI sur le port 8000, frontend React via Nginx sur le port 80, Ollama sur le port 11434.

Les données (ChromaDB et historique SQLite) sont persistées dans un volume Docker nommé `smart-data`, qui survit aux redémarrages et rebuilds.

## Tests

### Backend Python

Les tests backend sont organisés en deux niveaux. Les tests unitaires dans `tests/unit/` couvrent chaque fonction de manière isolée avec des mocks LLM et ChromaDB. Les tests d'intégration dans `tests/integration/` couvrent les endpoints FastAPI via TestClient et le pipeline complet ingest/retrieval/agent. La couverture cible est de 80%.

### Frontend React

Les tests frontend utilisent Vitest et React Testing Library. Ils couvrent les 6 composants principaux (ChatWindow, MessageBubble, UploadPanel, SourceCard, StatusBar) et les 2 hooks (useChat, useUpload). La couverture cible est de 70%.

### Tests E2E

Les tests end-to-end utilisent Playwright. Ils vérifient le parcours utilisateur complet : upload d'un document, envoi d'une question, affichage de la réponse avec sources citées.

## Stack technique complète

| Couche | Technologie | Version |
|--------|------------|---------|
| Orchestration agent | LangGraph | 0.2+ |
| Framework LLM | LangChain | 0.3+ |
| LLM local | Ollama + Mistral 7B | latest |
| LLM production | Mistral API | mistral-small-latest |
| LLM alternatif | Claude Haiku | claude-haiku-4-5 |
| Embeddings | nomic-embed-text | latest |
| Vector store | ChromaDB | 0.5+ |
| Backend API | FastAPI + Uvicorn | 0.110+ |
| Frontend | React 18 + Vite + TailwindCSS | React 18 |
| Persistance historique | SQLite (stdlib Python) | - |
| Parsing PDF | PyMuPDF (fitz) | 1.24+ |
| Scraping web | BeautifulSoup4 + httpx | latest |
| Config | Pydantic Settings v2 | v2 |
| Tests backend | pytest + pytest-cov | latest |
| Tests frontend | Vitest + React Testing Library | 2.x |
| Tests E2E | Playwright | 1.48+ |
| Conteneurisation | Docker + Docker Compose | - |
