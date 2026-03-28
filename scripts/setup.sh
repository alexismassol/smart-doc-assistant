#!/bin/bash
# setup.sh — Installation complète du projet Smart Doc Assistant
# Installe : venv Python, dépendances backend, npm frontend, modèles Ollama

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════╗"
echo "║    Smart Doc Assistant — Setup complet        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Copier .env.example → .env si absent ───────────────────────────────────
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✅  .env créé depuis .env.example"
else
    echo "ℹ️   .env déjà présent (non écrasé)"
fi

# ── 2. Venv Python + dépendances backend ──────────────────────────────────────
echo ""
echo "📦  Installation des dépendances Python..."
cd "$PROJECT_ROOT/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅  Virtualenv créé dans backend/venv/"
fi

source venv/bin/activate
echo "    Mise à jour de pip..."
pip install --upgrade pip -q

# chromadb requiert onnxruntime qui n'existe pas encore pour Python 3.14.
# On l'installe sans ses deps déclarées (il fonctionne sans onnxruntime en runtime),
# puis on installe le reste normalement.
echo "    Pré-installation de chromadb (contournement Python 3.14)..."
pip install --no-deps chromadb==1.5.5 -q

echo "    Installation des autres packages Python..."
# On filtre chromadb du requirements pour éviter la re-résolution
grep -v '^chromadb' requirements.txt | pip install -r /dev/stdin
echo "✅  Dépendances Python installées"

# ── 3. Dépendances npm frontend ───────────────────────────────────────────────
echo ""
echo "📦  Installation des dépendances Node.js (frontend)..."
cd "$PROJECT_ROOT/frontend"
npm install
echo "✅  Dépendances frontend installées"

# ── 3b. Dépendances Playwright E2E ────────────────────────────────────────────
echo ""
echo "🎭  Installation de Playwright E2E..."
cd "$PROJECT_ROOT/e2e"
npm install
npx playwright install chromium --with-deps 2>/dev/null || true
echo "✅  Playwright installé"

# ── 4. Vérification Ollama ────────────────────────────────────────────────────
echo ""
bash "$SCRIPT_DIR/check_ollama.sh"

# ── 5. Créer les dossiers de données ──────────────────────────────────────────
mkdir -p "$PROJECT_ROOT/data/chroma_db"
mkdir -p "$PROJECT_ROOT/data/sample_docs"
echo "✅  Dossiers data/ créés"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅  Setup terminé ! Lancer : npm start        ║"
echo "╚══════════════════════════════════════════════╝"
