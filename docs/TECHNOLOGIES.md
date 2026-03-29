# Tutoriel technique - Smart Doc Assistant

> Ce document explique chaque technologie utilisée dans le projet : ce qu'elle fait, pourquoi on l'a choisie, et quelles sont les alternatives. Idéal pour comprendre l'architecture avant de contribuer, ou pour un recruteur qui veut creuser la stack.

---

## Table des matières

1. [Vue d'ensemble - qu'est-ce que le RAG ?](#1-vue-densemble--quest-ce-que-le-rag-)
2. [LangChain - le couteau suisse LLM](#2-langchain--le-couteau-suisse-llm)
3. [LangGraph - orchestration par graphe d'état](#3-langgraph--orchestration-par-graphe-détat)
4. [Ollama - LLM local gratuit](#4-ollama--llm-local-gratuit)
5. [Mistral AI - LLM API open-source](#5-mistral-ai--llm-api-open-source)
6. [nomic-embed-text - les embeddings](#6-nomic-embed-text--les-embeddings)
7. [ChromaDB - la base vectorielle](#7-chromadb--la-base-vectorielle)
8. [FastAPI - le backend Python](#8-fastapi--le-backend-python)
9. [Pydantic Settings - la configuration typée](#9-pydantic-settings--la-configuration-typée)
10. [React 18 + Vite - le frontend](#10-react-18--vite--le-frontend)
11. [TailwindCSS - le styling](#11-tailwindcss--le-styling)
12. [PyMuPDF - parsing de PDF](#12-pymupdf--parsing-de-pdf)
13. [Récapitulatif - tableau des alternatives](#13-récapitulatif--tableau-des-alternatives)

---

## 1. Vue d'ensemble - qu'est-ce que le RAG ?

**RAG = Retrieval-Augmented Generation**

Un LLM (comme Mistral ou ChatGPT) est entraîné une fois et ne connaît pas tes documents privés. Le RAG résout ça en deux phases :

```
Phase 1 - Ingestion (une fois par document)
┌─────────────────────────────────────────────────────────┐
│  Tes documents (PDF, CSV, MD, URL)                      │
│       ↓                                                 │
│  Découpage en petits morceaux (chunks de 500 tokens)    │
│       ↓                                                 │
│  Transformation en vecteurs numériques (embeddings)     │
│       ↓                                                 │
│  Stockage dans ChromaDB (base vectorielle)              │
└─────────────────────────────────────────────────────────┘

Phase 2 - Question (à chaque message utilisateur)
┌─────────────────────────────────────────────────────────┐
│  Question : "Quelle est la limite de l'API ?"           │
│       ↓                                                 │
│  La question est transformée en vecteur                 │
│       ↓                                                 │
│  ChromaDB trouve les 5 chunks les plus proches          │
│       ↓                                                 │
│  Le LLM reçoit : question + chunks + historique         │
│       ↓                                                 │
│  Réponse générée UNIQUEMENT à partir des documents      │
└─────────────────────────────────────────────────────────┘
```

**Pourquoi RAG plutôt que fine-tuning ?**

| Approche | Avantage | Inconvénient |
|---|---|---|
| **RAG** (ce projet) | Rapide, pas cher, documents mis à jour en temps réel | Dépend de la qualité du retrieval |
| **Fine-tuning** | Modèle "sait" vraiment le contenu | Coûteux (GPU + temps), statique |
| **Context window** | Simple à implémenter | Limité à ~32k tokens, pas scalable |

---

## 2. LangChain - le couteau suisse LLM

**Site** : [langchain.com](https://www.langchain.com)
**Version utilisée** : 0.3+

### Ce que c'est

LangChain est un framework Python (et JS) qui standardise toutes les briques d'une application LLM. Sans LangChain, il faudrait écrire soi-même les loaders PDF, les text splitters, les interfaces avec chaque LLM, etc.

### Ce qu'on utilise dans ce projet

| Composant LangChain | Où | Rôle |
|---|---|---|
| `PyMuPDFLoader` | `ingest/loader.py` | Charge et parse les PDF |
| `CSVLoader` | `ingest/loader.py` | Charge les fichiers CSV |
| `RecursiveCharacterTextSplitter` | `ingest/chunker.py` | Découpe le texte en chunks |
| `OllamaEmbeddings` | `ingest/embedder.py` | Génère les embeddings via Ollama |
| `ChatOllama` / `ChatMistralAI` | `config.py` | Interface LLM switchable |
| `Document` | Partout | Type standard pour un chunk de texte |

### Alternatives

| Alternative | Différence |
|---|---|
| **LlamaIndex** | Plus orienté RAG "clé en main", moins flexible |
| **Haystack** | Plus orienté production enterprise |
| **Code maison** | Contrôle total, mais beaucoup plus de travail |

---

## 3. LangGraph - orchestration par graphe d'état

**Site** : [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
**Version utilisée** : 0.2+

### Ce que c'est

LangGraph est une extension de LangChain qui permet de créer des agents sous forme de **graphe d'état**. Au lieu d'une chaîne linéaire (`A → B → C`), on définit des nœuds et des arêtes - avec des conditions.

### Pourquoi pas juste une fonction Python ?

```python
# ❌ Sans LangGraph - code difficile à maintenir, pas de state management
def process(question):
    chunks = retrieve(question)
    chunks = rerank(chunks)
    history = get_history()
    return generate(question, chunks, history)

# ✅ Avec LangGraph - state typé, observable, testable
graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("rerank", rerank_node)
graph.add_node("memory", memory_node)
graph.add_node("generate", generate_node)
graph.add_edge("retrieve", "rerank")
# ... edges conditionnels possibles
```

### Notre graphe

```
[START]
   ↓
[retrieve_node]  → similarity_search top-5 dans ChromaDB
   ↓
[rerank_node]    → filtre les chunks score < 0.4
   ↓
[memory_node]    → injecte les 5 derniers échanges
   ↓
[generate_node]  → appel LLM + prompt structuré
   ↓
[END]            → retourne answer + sources + confidence
```

### Alternatives

| Alternative | Différence |
|---|---|
| **LangChain LCEL** | Moins expressif pour les conditions complexes |
| **CrewAI** | Multi-agents, plus haut niveau, moins de contrôle |
| **AutoGen (Microsoft)** | Multi-agents conversationnels |
| **Code maison** | Simple à démarrer, difficile à maintenir |

---

## 4. Ollama - LLM local gratuit

**Site** : [ollama.ai](https://ollama.ai)

### Ce que c'est

Ollama est un outil qui permet de télécharger et faire tourner des LLMs open-source **localement sur ton machine**, sans internet, sans API key, sans coût.

```bash
ollama pull mistral       # Télécharge Mistral 7B (~4.4 GB)
ollama pull phi3:mini     # Télécharge Phi-3 Mini (~2.2 GB) - plus léger
ollama pull nomic-embed-text  # Télécharge le modèle d'embeddings

ollama run mistral "Bonjour !"   # Lancer une conversation
ollama serve                      # Démarrer le serveur API (port 11434)
pkill ollama                      # Arrêter le serveur
```

### Modèles disponibles dans ce projet

| Modèle | Taille | Vitesse sur Intel | Usage |
|---|---|---|---|
| `mistral` | 4.4 GB | ~5-15s/réponse | LLM principal (prod locale) |
| `phi3:mini` | 2.2 GB | ~2-5s/réponse | Dev rapide, moins de RAM |
| `nomic-embed-text` | 274 MB | très rapide | Embeddings (obligatoire) |

### Commandes utiles

```bash
ollama serve          # Démarrer le serveur Ollama
ollama list           # Lister les modèles téléchargés
ollama ps             # Voir les modèles en cours d'exécution
pkill ollama          # Arrêter le serveur
ollama rm mistral     # Supprimer un modèle
```

### Alternatives

| Alternative | Différence |
|---|---|
| **LM Studio** | Interface graphique, plus user-friendly |
| **llama.cpp** | Plus bas niveau, plus performant, moins pratique |
| **Mistral API** | Payant, pas besoin de GPU/CPU local |

---

## 5. Mistral AI - LLM API open-source

**Site** : [mistral.ai](https://mistral.ai)

### Ce que c'est

Mistral AI est une startup française qui propose des LLMs open-source performants. Le modèle `mistral-small-latest` est utilisé en mode API (cloud) pour le déploiement production.

### Pourquoi Mistral plutôt que OpenAI ?

- **Open-source** : les poids sont publics (contrairement à GPT-4)
- **Moins cher** : API moins coûteuse que OpenAI
- **Européen** : conformité RGPD facilitée
- **Performant** : Mistral 7B surpasse GPT-3.5 sur de nombreux benchmarks

### Configuration dans ce projet

```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=votre_clé
MISTRAL_MODEL=mistral-small-latest
```

### Alternatives

| Alternative | Différence |
|---|---|
| **OpenAI GPT-4** | Plus puissant, plus cher, closed-source |
| **Claude (Anthropic)** | Très bon en raisonnement, intégré en alternatif dans ce projet |
| **Cohere** | Orienté enterprise et RAG |
| **Gemini (Google)** | Bon multimodal |

---

## 6. nomic-embed-text - les embeddings

**Modèle** : `nomic-embed-text` via Ollama

### Ce que c'est

Un modèle d'**embedding** transforme du texte en vecteur numérique de dimension fixe. Deux textes sémantiquement proches auront des vecteurs proches dans l'espace vectoriel.

```
"FastAPI est un framework web Python"  →  [0.23, -0.87, 0.41, 0.12, ...]  (768 dim)
"Flask est aussi un framework Python"  →  [0.21, -0.85, 0.39, 0.14, ...]  (proche !)
"Le chat mange du poisson"             →  [-0.54, 0.33, -0.71, 0.88, ...]  (loin !)
```

### Rôle dans le pipeline RAG

```
Document : "La limite de taux est 100 req/min"
       ↓ nomic-embed-text
Vecteur : [0.12, -0.34, 0.78, ...]
       ↓ stocké dans ChromaDB

Question : "Quelle est la limite de l'API ?"
       ↓ nomic-embed-text
Vecteur : [0.11, -0.32, 0.75, ...]   ← proche du vecteur du document !
       ↓ ChromaDB compare par similarité cosinus
Résultat : le chunk du document est retourné ✅
```

**Sans embeddings, le RAG ne peut pas fonctionner.** C'est le cœur de la recherche sémantique.

### Alternatives

| Alternative | Dimension | Notes |
|---|---|---|
| **nomic-embed-text** (ce projet) | 768 | Open-source, local via Ollama |
| **text-embedding-3-small** (OpenAI) | 1536 | Très performant, payant |
| **all-MiniLM-L6-v2** (HuggingFace) | 384 | Léger, gratuit, moins précis |
| **mxbai-embed-large** (Ollama) | 1024 | Plus précis que nomic, plus lourd |

---

## 7. ChromaDB - la base vectorielle

**Site** : [trychroma.com](https://www.trychroma.com)
**Version** : 0.5+

### Ce que c'est

ChromaDB est une **base de données vectorielle** open-source. Elle stocke des vecteurs et permet de retrouver les K plus proches voisins d'un vecteur requête (similarity search).

### Comment on l'utilise

```python
# Stocker un chunk
collection.add(
    documents=["La limite de taux est 100 req/min"],
    embeddings=[[0.12, -0.34, 0.78, ...]],
    metadatas=[{"source": "api.pdf", "page": 5}],
    ids=["chunk_001"]
)

# Retrouver les 5 chunks les plus proches d'une question
results = collection.query(
    query_embeddings=[[0.11, -0.32, 0.75, ...]],
    n_results=5
)
```

### Pourquoi ChromaDB ?

- **Sans serveur** : tourne en mode embarqué, pas besoin de Docker séparé
- **Persistant** : les données survivent au redémarrage (`./data/chroma_db/`)
- **Simple** : API Python claire, parfait pour un projet portfolio
- **Open-source** : gratuit, pas de limit de tier

### Alternatives

| Alternative | Notes |
|---|---|
| **Pinecone** | Managed cloud, très scalable, payant |
| **Weaviate** | Self-hosted, plus complet, plus complexe |
| **Qdrant** | Rust, très performant, self-hosted |
| **pgvector** | Extension PostgreSQL, bonne option si déjà sur Postgres |
| **FAISS** (Meta) | Très rapide, mais pas de persistance native |

---

## 8. FastAPI - le backend Python

**Site** : [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
**Version** : 0.110+

### Ce que c'est

FastAPI est un framework web Python **asynchrone** basé sur Pydantic et Starlette. Il génère automatiquement la documentation Swagger et valide les entrées/sorties via des types Python.

### Ce qu'on apprécie

```python
# Type hints → validation automatique + doc Swagger
@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    ...
```

- **Async natif** : gère la concurrence sans bloquer
- **Swagger auto** : `http://localhost:8000/docs` - généré sans effort
- **Pydantic intégré** : validation des requêtes/réponses

### Alternatives

| Alternative | Différence |
|---|---|
| **Flask** | Plus simple, synchrone, moins de features |
| **Django REST** | Plus lourd, batteries included, ORM intégré |
| **Litestar** | Concurrent direct de FastAPI, moins populaire |
| **Express (Node.js)** | Autre langage, très populaire mais pas de type hints natifs |

---

## 9. Pydantic Settings - la configuration typée

**Version** : v2

### Ce que c'est

Pydantic Settings charge les variables d'environnement (depuis `.env` ou l'environnement système) et les valide avec des types Python.

```python
class Settings(BaseSettings):
    llm_provider: Literal["ollama", "mistral", "anthropic"] = "ollama"
    retrieval_top_k: int = 5          # automatiquement converti depuis string
    retrieval_score_threshold: float = 0.4

settings = Settings()  # Charge .env au démarrage, valide tout
```

Si `LLM_PROVIDER=openai` dans le `.env` → **erreur au démarrage**, pas en production. C'est le principe de **fail fast**.

---

## 10. React 18 + Vite - le frontend

**React version** : 18 | **Bundler** : Vite

### Pourquoi React 18 ?

- **Hooks** : `useState`, `useEffect`, hooks custom (`useChat`, `useUpload`) - logique métier découplée du rendering
- **Standard industrie** : ce que les recruteurs attendent de voir en 2024-2025
- **Composants fonctionnels** : plus lisibles, testables

### Pourquoi Vite plutôt que Create React App ?

- **10x plus rapide** en dev (HMR instantané)
- CRA est déprécié depuis 2023
- Configuration proxy `/api → localhost:8000` intégrée

### Alternatives

| Alternative | Différence |
|---|---|
| **Next.js** | SSR/SSG, routing intégré, overkill pour ce projet |
| **Vue 3** | Courbe d'apprentissage plus douce, moins populaire en France |
| **Svelte** | Très léger, moins d'emplois |
| **Angular** | Enterprise, verbeux, TypeScript natif |

---

## 11. TailwindCSS - le styling

**Version** : 3

### Ce que c'est

Tailwind est un framework CSS **utility-first** : au lieu d'écrire du CSS, on compose des classes utilitaires directement dans le HTML/JSX.

```jsx
// ❌ CSS classique
<div className="card">  // + 20 lignes dans un .css

// ✅ Tailwind
<div className="bg-gray-800 rounded-lg p-4 shadow-md hover:shadow-lg transition-shadow">
```

### Alternatives

| Alternative | Différence |
|---|---|
| **CSS Modules** | Scoped CSS, plus verbeux |
| **Styled Components** | CSS-in-JS, runtime overhead |
| **shadcn/ui** | Composants prêts à l'emploi basés sur Tailwind |
| **MUI / Chakra** | Design system complet, moins de liberté |

---

## 12. PyMuPDF - parsing de PDF

**Package Python** : `fitz` (nom d'import de PyMuPDF)
**Version** : 1.24+

### Ce que c'est

PyMuPDF est la librairie de parsing PDF la plus rapide disponible en Python. Elle extrait le texte, les métadonnées (numéro de page, auteur, titre) et les images.

### Alternatives

| Alternative | Différence |
|---|---|
| **pdfplumber** | Plus précis sur les tableaux, plus lent |
| **PyPDF2** | Plus ancien, moins maintenu |
| **pdfminer.six** | Très précis mais lent |
| **unstructured** | Gère plus de formats, lourd |

---

## 13. Récapitulatif - tableau des alternatives

| Composant | Choix dans ce projet | Alternative principale | Pourquoi notre choix |
|---|---|---|---|
| LLM local | Ollama + Mistral 7B | LM Studio | CLI + API REST, scriptable |
| LLM API | Mistral API | OpenAI GPT-4 | Open-source, moins cher, européen |
| LLM alternatif | Claude Haiku | Gemini | Démo multi-provider Anthropic |
| Embeddings | nomic-embed-text | text-embedding-3-small | Gratuit, local, open-source |
| Vector store | ChromaDB | Pinecone | Sans serveur, open-source, simple |
| Agent | LangGraph | CrewAI | Graph d'état typé, plus de contrôle |
| Framework LLM | LangChain | LlamaIndex | Écosystème plus large |
| Backend | FastAPI | Flask | Async, Swagger auto, Pydantic natif |
| Frontend | React 18 | Next.js | SPA suffisant, pas de SSR nécessaire |
| Styling | TailwindCSS | CSS Modules | Productivité, cohérence |
| PDF | PyMuPDF | pdfplumber | Rapidité + métadonnées |
| Config | Pydantic Settings v2 | python-decouple | Validation typée, intégré FastAPI |

---

*Ce document fait partie du projet Smart Doc Assistant - portfolio technique IA par Alexis MASSOL.*
