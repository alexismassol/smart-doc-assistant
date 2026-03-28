# 📚 Tutorial technique — Smart Doc Assistant

> Explication du code réel du projet, brique par brique. Comment chaque partie fonctionne, pourquoi on l'a codée comme ça, et où la trouver dans le repo.

---

## Sommaire

1. [Pipeline d'ingestion — `backend/ingest/`](#1-pipeline-dingestion)
2. [Base vectorielle ChromaDB — `backend/retrieval/`](#2-base-vectorielle-chromadb)
3. [Agent LangGraph — `backend/agent/`](#3-agent-langgraph)
4. [Backend FastAPI — `backend/api/`](#4-backend-fastapi)
5. [Streaming SSE — token par token](#5-streaming-sse)
6. [Configuration LLM — `backend/config.py`](#6-configuration-llm)
7. [Hooks React — `frontend/src/hooks/`](#7-hooks-react)
8. [Composants UI — `frontend/src/components/`](#8-composants-ui)

---

## 1. Pipeline d'ingestion

**Fichiers :** `backend/ingest/loader.py`, `chunker.py`, `embedder.py`

### Loader — lire les documents

Le loader unifie tous les formats en une liste de `Document` LangChain.

```python
# backend/ingest/loader.py

def load_document(file_path: str, file_type: str) -> list[Document]:
    if file_type == "pdf":
        # PyMuPDF extrait texte + n° de page automatiquement
        loader = PyMuPDFLoader(file_path)
        return loader.load()

    elif file_type == "csv":
        # Chaque ligne CSV → un Document LangChain
        loader = CSVLoader(file_path)
        return loader.load()

    elif file_type in ("md", "txt"):
        # Markdown/TXT : lecture directe, pas de lib spéciale
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path})]

def load_from_url(url: str) -> list[Document]:
    # httpx télécharge la page, BeautifulSoup4 extrait le texte HTML
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return [Document(page_content=text, metadata={"source": url, "type": "url"})]
```

Un `Document` LangChain c'est simplement :
```python
Document(
    page_content="La limite de taux est 100 req/min.",
    metadata={"source": "api.pdf", "page": 5, "type": "pdf"}
)
```

---

### Chunker — découper le texte

```python
# backend/ingest/chunker.py

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,    # ~100 mots par chunk
    chunk_overlap=50,  # chevauchement pour ne pas perdre les infos à cheval
    separators=["\n\n", "\n", ".", " ", ""],  # coupe sur les séparateurs naturels
)

def split_documents(documents: list[Document]) -> list[Document]:
    return splitter.split_documents(documents)
```

**Pourquoi `overlap=50` ?** Si une info importante est à cheval sur la fin du chunk 3 et le début du chunk 4, l'overlap garantit qu'elle apparaît dans les deux — on ne la rate pas à la recherche.

**Pourquoi `RecursiveCharacterTextSplitter` ?** Il essaie de couper d'abord sur `\n\n` (paragraphes), puis `\n` (lignes), puis `.` (phrases), puis espace — jamais au milieu d'un mot. Le texte reste lisible.

---

### Embedder — vectoriser et stocker

```python
# backend/ingest/embedder.py

def embed_and_store(chunks: list[Document], source_name: str) -> int:
    collection = get_collection()  # ChromaDB collection "smart_docs"

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [
        {
            "source": source_name,
            "page": chunk.metadata.get("page", 0),
            "type": chunk.metadata.get("type", "txt"),
            "timestamp": datetime.now().isoformat(),
        }
        for chunk in chunks
    ]

    # nomic-embed-text via Ollama → appel local, aucun cloud
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectors = embeddings.embed_documents(texts)

    # Stockage dans ChromaDB avec ID unique par chunk
    ids = [f"{source_name}_{i}" for i in range(len(chunks))]
    collection.add(documents=texts, embeddings=vectors, metadatas=metadatas, ids=ids)

    return len(chunks)
```

---

## 2. Base vectorielle ChromaDB

**Fichiers :** `backend/retrieval/vectorstore.py`, `retriever.py`

### Connexion ChromaDB

```python
# backend/retrieval/vectorstore.py

import chromadb

def get_collection():
    # Mode persistant — les données survivent au redémarrage
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(
        name=settings.chroma_collection,   # "smart_docs"
        metadata={"hnsw:space": "cosine"}  # Similarité cosine pour les embeddings
    )
```

Les données sont stockées dans `./data/chroma_db/` sur le disque. En relançant l'app, tous les documents sont déjà là.

---

### Retriever — recherche sémantique

```python
# backend/retrieval/retriever.py

def retrieve_with_confidence(question: str) -> tuple[list[dict], float]:
    collection = get_collection()

    # 1. Embed la question avec le même modèle que les documents
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    query_vector = embeddings.embed_query(question)

    # 2. ChromaDB retourne les top_k chunks les plus proches
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=settings.retrieval_top_k,  # top_k=5
        include=["documents", "metadatas", "distances"]
    )

    # 3. Convertir distances en scores (distance cosine → score pertinence)
    # ChromaDB retourne des distances, pas des similarités → 1 - distance
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        score = 1 - results["distances"][0][i]
        if score >= settings.retrieval_score_threshold:  # filtre score < 0.4
            chunks.append({
                "content": doc,
                "source": results["metadatas"][0][i]["source"],
                "page": results["metadatas"][0][i].get("page", 0),
                "score": score,
                "type": results["metadatas"][0][i].get("type", "txt"),
            })

    # Confidence = moyenne des scores des chunks retenus
    confidence = sum(c["score"] for c in chunks) / len(chunks) if chunks else 0.0
    return chunks, confidence
```

**Le score de confiance affiché dans l'UI** (`Confiance : 72%`) vient directement de cette moyenne.

---

## 3. Agent LangGraph

**Fichiers :** `backend/agent/state.py`, `nodes.py`, `graph.py`, `memory.py`

### L'état partagé

```python
# backend/agent/state.py

class AgentState(TypedDict):
    question: str      # Question de l'utilisateur
    context: list      # Chunks récupérés de ChromaDB
    answer: str        # Réponse générée par le LLM
    sources: list      # Sources formatées pour le frontend
    history: list      # Historique conversation (max 5 échanges)
    confidence: float  # Score de confiance moyen
    session_id: str    # UUID de session
```

LangGraph passe cet état de nœud en nœud. Chaque nœud retourne **uniquement les clés qu'il modifie** — les autres restent inchangées.

---

### Les 3 nœuds

```python
# backend/agent/nodes.py

def retrieve_node(state: AgentState) -> dict:
    """Nœud 1 — Chercher les documents pertinents dans ChromaDB"""
    results, confidence = retrieve_with_confidence(state["question"])
    return {"context": results, "confidence": confidence}
    # → passe le résultat au nœud suivant via l'état


def memory_node(state: AgentState) -> dict:
    """Nœud 2 — Limiter l'historique aux 5 derniers échanges"""
    windowed = apply_sliding_window(state["history"], window=settings.memory_window)
    return {"history": windowed}
    # → évite un contexte LLM trop long


def generate_node(state: AgentState) -> dict:
    """Nœud 3 — Générer la réponse avec le LLM"""
    from langchain_core.messages import SystemMessage, HumanMessage

    # Construction du contexte documentaire pour le prompt
    context_str = "\n\n".join([
        f"[Source: {r['source']}, score: {r['score']:.2f}]\n{r['content']}"
        for r in state["context"]
    ]) if state["context"] else "Aucun document pertinent trouvé."

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),  # "Tu réponds UNIQUEMENT sur les docs..."
        HumanMessage(content=f"Contexte:\n{context_str}\n\nQuestion: {state['question']}"),
    ]

    # Appel LLM — le provider dépend de .env (ollama / mistral / anthropic)
    llm = settings.get_llm()
    response = llm.invoke(messages)

    return {"answer": response.content, "sources": state["context"]}
```

---

### Le graph — assemblage des nœuds

```python
# backend/agent/graph.py

def build_graph():
    graph = StateGraph(AgentState)

    # Ajout des nœuds
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("memory", memory_node)
    graph.add_node("generate", generate_node)

    # Edges séquentiels : START → retrieve → memory → generate → END
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "memory")
    graph.add_edge("memory", "generate")
    graph.add_edge("generate", END)

    return graph.compile()

# Instance globale importée par les routes FastAPI
agent_graph = build_graph()
```

**Extension possible :** ajouter un edge conditionnel après `retrieve` :
```python
graph.add_conditional_edges(
    "retrieve",
    lambda state: "generate" if state["confidence"] < 0.3 else "memory",
    # Si confiance trop basse → passer directement à generate (qui dira "pas trouvé")
)
```

---

### Mémoire — fenêtre glissante

```python
# backend/agent/memory.py

def apply_sliding_window(history: list, window: int = 5) -> list:
    """Garde les N derniers échanges (1 échange = 1 question + 1 réponse = 2 messages)"""
    max_messages = window * 2
    return history[-max_messages:] if len(history) > max_messages else history

def format_history_for_prompt(history: list) -> str:
    """Formate l'historique pour l'injecter dans le prompt"""
    lines = []
    for msg in history:
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
```

---

## 4. Backend FastAPI

**Fichiers :** `backend/main.py`, `backend/api/routes_chat.py`, `routes_ingest.py`

### Démarrage — lifespan

```python
# backend/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage : vérifier ChromaDB
    try:
        collection = get_collection()
        count = collection.count()
        logger.info(f"ChromaDB connecté — {count} chunks dans '{settings.chroma_collection}'")
    except Exception as e:
        logger.warning(f"ChromaDB non disponible : {e}")
    yield
    logger.info("Smart Doc Assistant arrêté")

app = FastAPI(title="Smart Doc Assistant API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], ...)
```

---

### Route upload

```python
# backend/api/routes_ingest.py

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Sauvegarde temporaire du fichier
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Pipeline : load → chunk → embed → ChromaDB
    file_type = suffix.lstrip(".")
    documents = load_document(tmp_path, file_type)
    chunks = split_documents(documents)
    count = embed_and_store(chunks, source_name=file.filename)

    return {"status": "ok", "chunks": count, "source": file.filename}
```

---

### Route chat (non-streaming)

```python
# backend/api/routes_chat.py

@router.post("/api/chat")
async def chat(request: ChatRequest):
    initial_state = AgentState(
        question=request.question,
        context=[],
        answer="",
        sources=[],
        history=get_session_history(request.session_id),  # depuis SQLite
        confidence=0.0,
        session_id=request.session_id,
    )

    # Invocation du graph LangGraph
    result = agent_graph.invoke(initial_state)

    # Sauvegarder l'échange dans SQLite
    save_exchange(request.session_id, request.question, result["answer"])

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        latency_ms=int((time.time() - start_time) * 1000),
    )
```

---

## 5. Streaming SSE

**Fichiers :** `backend/api/routes_chat.py` (route `/api/chat/stream`), `frontend/src/hooks/useChat.js`

### Côté backend — StreamingResponse

```python
# backend/api/routes_chat.py

@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        start_time = time.time()

        # 1. Retrieval synchrone (rapide — juste une requête ChromaDB)
        results, confidence = retrieve_with_confidence(request.question)

        # 2. Construction du prompt
        messages = build_messages(request.question, results, history)

        # 3. Streaming LLM token par token avec astream()
        llm = settings.get_llm()
        async for chunk in llm.astream(messages):
            token = chunk.content
            if token:
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # 4. Sources envoyées après le dernier token
        latency = int((time.time() - start_time) * 1000)
        yield f"data: {json.dumps({'type': 'sources', 'sources': results, 'confidence': confidence, 'latency_ms': latency})}\n\n"

        # 5. Signal de fin
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

Les 3 types d'événements SSE :
- `token` — un morceau de texte à afficher immédiatement
- `sources` — chunks sources + confidence (envoyé une seule fois, à la fin)
- `done` — fermer le stream

---

### Côté frontend — ReadableStream

```javascript
// frontend/src/hooks/useChat.js

const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: question.trim(), session_id: sessionId }),
})

const reader = response.body.getReader()  // API Web standard, aucune dépendance
const decoder = new TextDecoder()
let buffer = ''

while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()  // Garder la ligne incomplète pour le prochain chunk

    for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const event = JSON.parse(line.slice(6))

        if (event.type === 'token') {
            if (!assistantAdded) {
                // Premier token → créer la bulle, cacher le TypingIndicator
                assistantAdded = true
                setIsLoading(false)
                setMessages(prev => [...prev, {
                    role: 'assistant', content: event.content,
                    sources: [], confidence: 0, isStreaming: true, id: assistantId,
                }])
            } else {
                // Tokens suivants → accumuler dans la bulle existante
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantId
                        ? { ...msg, content: msg.content + event.content }
                        : msg
                ))
            }
        } else if (event.type === 'sources') {
            // Mettre à jour sources + confidence + arrêter le curseur clignotant
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? { ...msg, sources: event.sources, confidence: event.confidence,
                        latency_ms: event.latency_ms, isStreaming: false }
                    : msg
            ))
        }
    }
}
```

**Séquence UX complète :**
1. Envoi → `isLoading = true` → `TypingIndicator` (`...`) affiché
2. Premier token → bulle créée, `isLoading = false` → `TypingIndicator` disparaît
3. Tokens suivants → accumulation dans la bulle, curseur `|` clignotant
4. Événement `sources` → sources affichées, `isStreaming = false`, curseur disparaît

---

## 6. Configuration LLM

**Fichier :** `backend/config.py`

```python
# backend/config.py — Pydantic Settings v2

class Settings(BaseSettings):
    # Provider LLM : "ollama" | "mistral" | "anthropic"
    llm_provider: str = "ollama"

    # Ollama (local, gratuit)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Mistral API (cloud)
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    # Anthropic (cloud)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    # RAG
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.4
    memory_window: int = 5

    model_config = SettingsConfigDict(env_file=".env")

    def get_llm(self):
        """Factory LLM — retourne le bon client selon LLM_PROVIDER dans .env"""
        if self.llm_provider == "ollama":
            return ChatOllama(
                base_url=self.ollama_base_url,
                model=self.ollama_model,
            )
        elif self.llm_provider == "mistral":
            return ChatMistralAI(
                api_key=self.mistral_api_key,
                model=self.mistral_model,
            )
        elif self.llm_provider == "anthropic":
            return ChatAnthropic(
                api_key=self.anthropic_api_key,
                model=self.anthropic_model,
            )
        raise ValueError(f"Provider inconnu : {self.llm_provider}")

settings = Settings()  # Singleton — lu une seule fois au démarrage
```

Changer de LLM = modifier `.env` uniquement. Le reste du code appelle `settings.get_llm()` sans savoir quel provider est utilisé.

---

## 7. Hooks React

**Fichiers :** `frontend/src/hooks/useChat.js`, `useUpload.js`

### useChat — gestion de la conversation

```javascript
// frontend/src/hooks/useChat.js

export function useChat() {
    const [messages, setMessages] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [sessionId] = useState(() => crypto.randomUUID())  // UUID stable par session
    const [lastLatency, setLastLatency] = useState(null)

    const sendMessage = useCallback(async (question) => {
        if (!question?.trim() || isLoading) return

        // 1. Ajouter le message utilisateur immédiatement (réactivité)
        setMessages(prev => [...prev, { role: 'user', content: question, id: Date.now() }])
        setIsLoading(true)

        // 2. Appel SSE streaming (voir section 5)
        // ...

    }, [isLoading, sessionId])

    const reset = useCallback(() => {
        setMessages([])
        setLastLatency(null)
    }, [])

    return { messages, isLoading, sendMessage, reset, lastLatency, sessionId }
}
```

**Pourquoi `useCallback` ?** Évite de recréer la fonction `sendMessage` à chaque render. Sans ça, si `sendMessage` est passé en prop à un composant enfant, il provoquerait un re-render inutile à chaque keystroke.

**Pourquoi `sessionId` sans setter ?** `useState(() => crypto.randomUUID())` — l'initializer est appelé une seule fois. L'UUID reste stable pendant toute la session, même si le composant re-render.

---

### useUpload — gestion des fichiers

```javascript
// frontend/src/hooks/useUpload.js

export function useUpload() {
    const [documents, setDocuments] = useState([])
    const [isUploading, setIsUploading] = useState(false)

    const uploadFile = useCallback(async (file) => {
        setIsUploading(true)
        const formData = new FormData()
        formData.append('file', file)  // multipart/form-data

        const response = await fetch('/api/upload', { method: 'POST', body: formData })
        const data = await response.json()  // { status, chunks, source }

        await refreshDocuments()  // Recharge la liste après upload
        setIsUploading(false)
        return data
    }, [])

    const deleteDocument = useCallback(async (source) => {
        await fetch(`/api/documents/${encodeURIComponent(source)}`, { method: 'DELETE' })
        await refreshDocuments()
    }, [])

    const refreshDocuments = useCallback(async () => {
        const res = await fetch('/api/documents')
        const data = await res.json()
        setDocuments(data.documents)
    }, [])

    return { documents, isUploading, uploadFile, deleteDocument, refreshDocuments }
}
```

---

## 8. Composants UI

**Fichiers :** `frontend/src/components/`

### MessageBubble — bulles de conversation

```jsx
// frontend/src/components/MessageBubble.jsx

export default function MessageBubble({ message }) {
    const isUser = message.role === 'user'
    const [copied, setCopied] = useState(false)

    const handleCopy = () => {
        navigator.clipboard.writeText(message.content).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)  // Reset après 2s
        })
    }

    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div className="relative group px-4 py-3 rounded-2xl ...">
                {message.content}

                {/* Curseur clignotant pendant le streaming */}
                {message.isStreaming && (
                    <span className="inline-block w-0.5 h-4 bg-accent animate-pulse" />
                )}

                {/* Bouton copier — visible au hover, uniquement quand réponse terminée */}
                {!isUser && !message.isStreaming && (
                    <button
                        onClick={handleCopy}
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                        {copied ? <CheckIcon /> : <CopyIcon />}
                    </button>
                )}
            </div>

            {/* Sources */}
            {message.sources?.length > 0 && (
                <div>
                    {message.sources.map((src, i) => <SourceCard key={i} source={src} />)}
                </div>
            )}
        </div>
    )
}
```

**`group` + `group-hover:opacity-100`** — pattern Tailwind pour afficher un bouton au survol du parent. Le bouton est `opacity-0` par défaut et devient visible quand la souris survole la bulle.

---

### UploadPanel — collapsible sur mobile

```jsx
// frontend/src/components/UploadPanel.jsx

export default function UploadPanel({ ... }) {
    const [mobileOpen, setMobileOpen] = useState(false)

    return (
        // Sur mobile : hauteur auto + collapsible
        // Sur desktop md+ : toujours visible, flex-1 (prend toute la hauteur)
        <aside className={`
            w-full md:w-80 flex-none flex flex-col
            border-b md:border-b-0 md:border-r border-border
            overflow-hidden transition-all duration-200
            ${mobileOpen ? 'flex-1' : 'h-auto'} md:flex-1 md:h-auto
        `}>
            {/* Header cliquable uniquement sur mobile */}
            <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer md:cursor-default"
                onClick={() => setMobileOpen(o => !o)}
            >
                <span>DOCUMENTS ({documents.length})</span>
                {/* Chevron visible uniquement sur mobile */}
                <ChevronIcon open={mobileOpen} className="md:hidden" />
            </div>

            {/* Contenu : caché sur mobile si fermé */}
            <div className={`${mobileOpen ? 'block' : 'hidden'} md:block flex-1 overflow-y-auto`}>
                {/* Drop zone + liste documents */}
            </div>
        </aside>
    )
}
```

---

### StatusBar — métriques en temps réel

```jsx
// frontend/src/components/StatusBar.jsx

export default function StatusBar({ llmProvider, documentsCount, latency }) {
    // Mapping provider → label affiché
    const providerLabel = {
        ollama: '⚡ Ollama local',
        mistral: '🌐 Mistral API',
        anthropic: '🤖 Claude',
    }[llmProvider] || '— Connexion...'

    return (
        <div className="flex items-center justify-between px-6 py-2.5 border-b">
            <span className="hidden md:inline font-semibold">Smart Doc Assistant</span>

            <div className="flex items-center gap-5">
                <Metric icon={<DotIcon color={llmProvider ? '#10b981' : '#525252'} />}
                        label={providerLabel} />
                <Metric icon={<DocIcon />}
                        label={`${documentsCount ?? 0} document${documentsCount !== 1 ? 's' : ''}`} />
                {latency != null && (
                    <Metric icon={<ClockIcon />} label={`${latency} ms`} />
                )}
            </div>
        </div>
    )
}
```

`llmProvider` vient d'un appel `GET /api/health` dans `App.jsx` — il reflète ce qui est configuré dans `.env` côté backend.

---

*Smart Doc Assistant — Portfolio Alexis MASSOL*
*LangGraph · LangChain · Mistral · ChromaDB · FastAPI · React 18 · Ollama*
