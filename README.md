# Smart Doc Assistant

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6B35)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-1C3C3C)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3-38BDF8?logo=tailwindcss&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5+-8B5CF6)
![SQLite](https://img.shields.io/badge/SQLite-history-003B57?logo=sqlite&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local-black)
![Mistral](https://img.shields.io/badge/Mistral-AI-FF7000)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/Tests-pytest%20%2B%20Vitest%20%2B%20Playwright-green)
![TDD](https://img.shields.io/badge/TDD-Red%20→%20Green%20→%20Refactor-brightgreen)
![License](https://img.shields.io/badge/License-Proprietary-red)

> **Agent RAG conversationnel** — Interrogez vos documents en langage naturel.
> Propulsé par **LangGraph · Mistral · ChromaDB · FastAPI · React 18**

---

## Présentation

**Smart Doc Assistant** est un agent IA de type **RAG (Retrieval Augmented Generation)** qui permet d'interroger une base de documents hétérogènes en langage naturel, avec citation des sources.

L'architecture repose sur :
- **LangGraph** pour l'orchestration de l'agent (graph d'état)
- **LangChain** pour les loaders de documents et le pipeline RAG
- **ChromaDB** comme base vectorielle locale et persistante
- **Ollama + Mistral 7B** en local (gratuit, offline) ou **Mistral API** en production

---

## Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| **Ingestion multi-format** | PDF, CSV, Markdown, pages web (URL) |
| **Retrieval sémantique** | ChromaDB + nomic-embed-text, reranking par score |
| **Mémoire de conversation** | Contexte des 5 derniers échanges (LangGraph memory node) |
| **Sources citées** | Chaque réponse affiche les chunks utilisés + score de pertinence |
| **Multi-provider LLM** | Ollama (local) · Mistral API · Claude Haiku — switcher via `.env` |
| **Interface React** | Upload drag & drop + chat streaming token-by-token (SSE) + dark theme |
| **Streaming SSE** | Réponses en temps réel via Server-Sent Events (`/api/chat/stream`) |

---

## Architecture

```
┌─── React 18 + Vite + TailwindCSS ───────────────────────────┐
│  UploadPanel (drag&drop)        ChatWindow + SourceCards    │
└──────┬──────────────────────────────────┬───────────────────┘
       │ POST /api/upload                 │ POST /api/chat
       ▼                                  ▼
┌─── FastAPI + Uvicorn ───────────────────────────────────────┐
│                                                             │
│  Ingest Pipeline (LangChain)    LangGraph Agent             │
│  ├ PyMuPDF      (PDF)           ├ retrieve_node             │
│  ├ pandas       (CSV)           ├ rerank_node               │
│  ├ direct       (Markdown)      ├ memory_node (window=5)    │
│  └ httpx + BS4  (URL)           └ generate_node             │
│        ↓                                ↓                   │
│  RecursiveCharacterTextSplitter    Pydantic Settings        │
│  chunk=500 / overlap=50            config.py                │
│        ↓                                ↓                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │   ChromaDB  —  collection: smart_docs               │    │
│  │   nomic-embed-text (Ollama) — dim 768               │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │   LLM (switchable via .env)                         │    │
│  │   ollama    → Mistral 7B (local, gratuit)           │    │
│  │   mistral   → Mistral API mistral-small-latest      │    │
│  │   anthropic → Claude Haiku                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Démarrage rapide

### Prérequis

- [Python 3.11+](https://python.org)
- [Node.js 18+](https://nodejs.org)
- [Ollama](https://ollama.ai) (pour le mode local gratuit)

### Installation

```bash
git clone https://github.com/votre-username/smart-doc-assistant.git
cd smart-doc-assistant

# Installation complète automatique
npm run setup
```

Le script `setup.sh` installe automatiquement :
- Le virtualenv Python + toutes les dépendances backend
- Les packages npm du frontend React
- Les modèles Ollama (`mistral` + `nomic-embed-text`)

### Démarrage — mode développement

```bash
# Lance backend (FastAPI :8000) + frontend (React :5173) simultanément
npm run start

# Ou avec logs colorés par service (BACK / FRONT)
npm run dev
```

Ouvrir [http://localhost:5173](http://localhost:5173)

> **`npm run start`** utilise `concurrently` pour lancer les deux serveurs en parallèle avec des labels colorés.\
> **`npm run dev`** utilise le script `scripts/dev.sh` (même résultat, sans `concurrently`).

### Démarrage — mode Docker

```bash
# Build et lancement complet (interactif)
npm run docker:start

# Ou en arrière-plan
npm run docker:start:detach

# Première fois : télécharger les modèles Ollama
docker exec smart-doc-ollama ollama pull mistral
docker exec smart-doc-ollama ollama pull nomic-embed-text

# Arrêter
npm run docker:stop
```

Ouvrir [http://localhost](http://localhost) (port 80, Nginx sert le build React)

---

## Configuration LLM

Modifier `LLM_PROVIDER` dans `.env` :

```env
# Mode local gratuit (défaut)
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral

# Mistral API (production)
LLM_PROVIDER=mistral
MISTRAL_API_KEY=votre_clé_ici

# Claude Haiku (Anthropic)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=votre_clé_ici
```

---

## Scripts disponibles

### Démarrage / Arrêt

| Commande | Description |
|---|---|
| `npm run setup` | Installation complète (venv + npm + ollama pull + playwright) |
| `npm run start` | Lance backend + frontend (concurrently, logs colorés) |
| `npm run start:backend` | Backend FastAPI seul (port 8000) |
| `npm run start:frontend` | Frontend React seul (port 5173) |
| `npm run stop` | Arrête backend + frontend |
| `npm run stop:backend` | Arrête uniquement le backend |
| `npm run stop:frontend` | Arrête uniquement le frontend |
| `npm run dev` | Même chose que `start` via `scripts/dev.sh` |
| `npm run check` | Vérifie Ollama + modèles présents |

### Docker

| Commande | Description |
|---|---|
| `npm run docker:start` | Build + lance (interactif, Ctrl+C pour arrêter) |
| `npm run docker:start:detach` | Build + lance en arrière-plan |
| `npm run docker:stop` | Arrête les conteneurs |
| `npm run docker:clean` | Arrête + supprime les images |
| `npm run docker:logs` | Voir les logs en direct |
| `npm run docker:ps` | État des conteneurs |

### Tests

| Commande | Description |
|---|---|
| `npm run test:unit` | Tests unitaires Python (pytest) |
| `npm run test:integration` | Tests d'intégration Python |
| `npm run test:all` | Tous les tests Python + couverture HTML |
| `npm run test:coverage` | Rapport de couverture (terminal) |
| `npm run test:frontend` | Tests unitaires React (Vitest, 82 tests) |
| `npm run test:frontend:coverage` | Couverture frontend |
| `npm run test:e2e` | Tests E2E Playwright (nécessite serveurs démarrés) |
| `npm run test:ingest` | Teste le pipeline d'ingestion |
| `npm run test:retrieval` | Teste le retrieval sémantique |
| `npm run test:agent` | Session CLI interactive avec l'agent |

### Gestion d'Ollama

```bash
ollama serve          # Démarrer le serveur Ollama (port 11434)
ollama list           # Lister les modèles téléchargés
ollama ps             # Voir les modèles actifs en mémoire
pkill ollama          # Arrêter le serveur Ollama
```

---

## API Reference

Documentation interactive disponible sur [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger auto-généré par FastAPI).

### `POST /api/chat`

```json
// Request
{ "question": "Quelle est la limite de taux de l'API ?", "session_id": "abc123" }

// Response
{
  "answer": "D'après la documentation v2.3, la limite est de 100 req/min.",
  "sources": [
    { "content": "...", "source": "api-doc.pdf", "page": 12, "score": 0.87 }
  ],
  "confidence": 0.87,
  "latency_ms": 1240
}
```

Voir [`docs/API.md`](docs/API.md) pour la référence complète.

---

## Stack complète

| Couche | Technologie | Rôle |
|---|---|---|
| Orchestration agent | **LangGraph 0.2** | Graph d'état, nodes, edges conditionnels |
| Framework LLM | **LangChain 0.3** | Loaders, splitters, chains |
| LLM local | **Ollama + Mistral 7B** | Inférence locale gratuite |
| LLM prod | **Mistral API** | `mistral-small-latest` |
| Embeddings | **nomic-embed-text** | Via Ollama, open-source |
| Base vectorielle | **ChromaDB** | Persistance locale |
| Historique | **SQLite** | Conversations persistantes (stdlib Python) |
| Backend | **FastAPI + Uvicorn** | REST API async |
| Frontend | **React 18 + Vite** | Interface SPA |
| CSS | **TailwindCSS 3** | Utility-first styling |
| Tests frontend | **Vitest + RTL** | 109 tests unitaires composants/hooks |
| Conteneurisation | **Docker Compose** | 3 services : backend + frontend + ollama |
| PDF | **PyMuPDF** | Parsing texte + métadonnées |
| Web scraping | **httpx + BeautifulSoup4** | Ingestion URLs |
| Config | **Pydantic Settings v2** | `.env` typé et validé |

---

## Documentation

- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — Explication de chaque technologie, pourquoi on l'utilise, alternatives
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Architecture détaillée avec schéma
- [`docs/SPECS.md`](docs/SPECS.md) — Spécifications fonctionnelles et techniques
- [`docs/API.md`](docs/API.md) — Référence API complète

---

## Licence

© 2026 Alexis MASSOL — Tous droits réservés.

Ce projet est un **portfolio de démonstration**. Vous pouvez le consulter, le forker et l'étudier à des fins personnelles et éducatives. Toute utilisation commerciale ou redistribution est interdite sans autorisation écrite. Voir [LICENSE](LICENSE) pour les conditions complètes.

---

*Projet portfolio — Alexis MASSOL | Senior Software Engineer · Embedded Systems & Cloud Platforms*
*Stack : LangGraph · LangChain · Mistral · ChromaDB · FastAPI · React 18*
