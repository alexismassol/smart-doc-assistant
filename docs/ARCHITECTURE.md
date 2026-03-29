# Architecture - Smart Doc Assistant

## Vue d'ensemble

```
┌─── Interface utilisateur ─────────────────────────────────────────────────────┐
│                                                                               │
│   React 18 + Vite + TailwindCSS                                               │
│                                                                               │
│   ┌──────────────────┐     ┌──────────────────────────────────────────────┐   │
│   │   UploadPanel    │     │              ChatWindow                      │   │
│   │   (drag & drop)  │     │   MessageBubble  ←  SourceCard (score)       │   │
│   └──────┬───────────┘     └────────────────────────┬─────────────────────┘   │
│          │ POST /api/upload                          │ POST /api/chat         │
└──────────┼───────────────────────────────────────────┼────────────────────────┘
           │                                           │
           ▼                                           ▼
┌─── Backend API ───────────────────────────────────────────────────────────────┐
│                                                                               │
│   FastAPI + Uvicorn  (port 8000)                                              │
│   Pydantic Settings v2  ←  .env                                               │
│                                                                               │
│   ┌─────────────────────────────┐   ┌──────────────────────────────────────┐  │
│   │   Ingest Pipeline           │   │   LangGraph Agent                    │  │
│   │   (LangChain)               │   │                                      │  │
│   │                             │   │   [START]                            │  │
│   │   PyMuPDF      → PDF        │   │      ↓                               │  │
│   │   pandas       → CSV        │   │   [retrieve_node]  top-k=5           │  │
│   │   direct       → Markdown   │   │      ↓                               │  │
│   │   httpx + BS4  → URL        │   │   [rerank_node]    score ≥ 0.4       │  │
│   │        ↓                    │   │      ↓                               │  │
│   │   RecursiveCharacterText    │   │   [memory_node]    window=5          │  │
│   │   Splitter (LangChain)      │   │      ↓                               │  │
│   │   chunk=500 / overlap=50    │   │   [generate_node]  LLM + prompt      │  │
│   └──────────────┬──────────────┘   │      ↓                               │  │
│                  │                  │   [END]  → answer + sources          │  │
│                  ▼                  └────────────────────────────┬─────────┘  │
│   ┌──────────────────────────────────────────────────────────────▼──────────┐ │
│   │                       ChromaDB                                          │ │
│   │   collection: smart_docs  |  nomic-embed-text (Ollama) dim=768          │ │
│   │   métadonnées: source, page, type, timestamp                            │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
│                                           ↓                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐ │
│   │   LLM (switchable via LLM_PROVIDER dans .env)                           │ │
│   │   ollama     → Mistral 7B    (local, gratuit - dev)                     │ │
│   │   mistral    → mistral-small-latest  (API - prod)                       │ │
│   │   anthropic  → claude-haiku-4-5  (alternatif - démo multi-provider)     │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Flux de données

### Ingestion d'un document
```
Fichier / URL → Loader → Chunks (500 tokens, overlap 50) → Embeddings (nomic-embed-text) → ChromaDB
```

### Question utilisateur
```
Question → retrieve_node (top-5) → rerank_node (filtre ≥ 0.4) → memory_node (inject 5 échanges) → generate_node (LLM) → réponse + sources
```

## Technologies et justifications

| Technologie | Rôle | Justification |
|---|---|---|
| **LangGraph** | Orchestration agent | Graph d'état typé, standard industrie IA 2024 |
| **LangChain** | Loaders + splitters | Écosystème riche, compatibilité multi-format |
| **ChromaDB** | Vector store | Léger, persistant, sans serveur, open-source |
| **nomic-embed-text** | Embeddings | Open-source, performant, local via Ollama |
| **FastAPI** | Backend REST | Async natif, Swagger auto, validation Pydantic |
| **Pydantic Settings v2** | Config | Validation typée du .env au boot |
| **React 18 + Vite** | Frontend | HMR rapide, standard entreprise |
| **TailwindCSS** | Styling | Utility-first, design system cohérent |
