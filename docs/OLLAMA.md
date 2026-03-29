# Ollama - Guide complet

Ollama fait tourner les LLMs **100% en local**, sans API key, sans connexion internet pour l'inférence.

---

## Installation

```bash
# macOS
brew install ollama
# ou télécharger le .dmg : https://ollama.ai/download/mac

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Télécharger l'installeur : https://ollama.ai/download/windows
```

---

## Démarrer le serveur

```bash
ollama serve          # démarre le serveur sur localhost:11434
ollama list           # liste les modèles téléchargés
ollama ps             # modèles actuellement chargés en mémoire
pkill ollama          # arrêter le serveur
```

---

## Modèles compatibles Smart Doc Assistant

| Modèle | Taille | Vitesse CPU | Qualité | Commande |
|---|---|---|---|---|
| `mistral` | 4.4 GB | ~30-60s/rép | ⭐⭐⭐⭐⭐ | `ollama pull mistral` |
| `phi3:mini` | 2.2 GB | ~10-20s/rép | ⭐⭐⭐⭐ | `ollama pull phi3:mini` |
| `llama3.2:3b` | 1.9 GB | ~8-15s/rép | ⭐⭐⭐ | `ollama pull llama3.2:3b` |

> **Embeddings** : `nomic-embed-text` est requis quel que soit le LLM choisi.
> ```bash
> ollama pull nomic-embed-text
> ```

### Changer de modèle

Dans `.env` :
```env
OLLAMA_MODEL=phi3:mini   # ou mistral, llama3.2:3b
```
Puis redémarrer : `npm run stop && npm run start`

---

## Confidentialité

- **Inférence** : 100% locale, aucune donnée envoyée à un serveur externe
- **Ingestion URL** : le backend fetch la page web une seule fois (httpx), puis le texte est vectorisé localement - aucune donnée n'est envoyée à Ollama
- **Documents** : stockés dans `data/chroma_db/` sur votre machine uniquement

---

## Tester Ollama en ligne de commande

### Test rapide sans document

```bash
# Démarrer une conversation interactive
ollama run mistral

# Ou envoyer un message one-shot
ollama run mistral "Explique le RAG en 2 phrases"
ollama run phi3:mini "Résume ce concept : retrieval augmented generation"
```

### Tester l'API directement (curl)

```bash
# Health check
curl http://localhost:11434/api/tags

# Générer une réponse (streaming)
curl http://localhost:11434/api/generate \
  -d '{
    "model": "mistral",
    "prompt": "Qu'\''est-ce que le RAG ?",
    "stream": false
  }'
```

### Tester via l'API Smart Doc Assistant

```bash
# Sans document - vérifie que l'agent répond correctement
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Comment fonctionne le pipeline RAG ?", "session_id": "test"}'

# Vérifier le provider actif
curl http://localhost:8000/api/health
# → {"status":"ok","llm_provider":"ollama","documents_count":0}
```

### Tester avec un document

```bash
# 1. Uploader un fichier Markdown
curl -X POST http://localhost:8000/api/upload \
  -F "file=@data/sample_docs/example.md"
# → {"message":"...","chunks":12,"source":"example.md"}

# 2. Poser une question sur le document
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Résume les points clés", "session_id": "test"}'
# → {"answer":"...","sources":[...],"confidence":0.87}
```

---

## VPS / Serveur distant

Pour utiliser Ollama sur un serveur OVH, AWS, Hetzner, etc. :

```bash
# Sur le serveur - exposer Ollama sur le réseau
OLLAMA_HOST=0.0.0.0 ollama serve

# Ou en service systemd (persistant)
sudo systemctl enable ollama
sudo systemctl start ollama

# Dans .env du projet (backend)
OLLAMA_BASE_URL=http://votre-ip:11434

# Ouvrir le port firewall (exemple UFW)
sudo ufw allow 11434
```

> **Note GPU** : sur un VPS avec GPU NVIDIA, Ollama utilise CUDA automatiquement - les réponses passent de 30-60s à 1-3s.
