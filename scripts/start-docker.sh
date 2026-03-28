#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# start-docker.sh — Lancement Docker de Smart Doc Assistant
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage : ./scripts/start-docker.sh [OPTIONS]
#
# OPTIONS :
#   -d, --detach    : Lance en arrière-plan (détaché)
#   --build-only    : Build seulement, ne lance pas
#   --no-build      : Lance sans rebuild (plus rapide si images déjà buildées)
#   --backend       : Lance uniquement le backend + ollama
#   --frontend      : Lance uniquement le frontend
#
# MODE PAR DÉFAUT : Interactif (logs visibles, Ctrl+C pour arrêter)
#
# APRÈS PREMIER LANCEMENT : Télécharger les modèles Ollama :
#   docker exec smart-doc-ollama ollama pull nomic-embed-text
#   docker exec smart-doc-ollama ollama pull mistral
#
# SERVICES :
#   backend  → http://localhost:8000  (FastAPI + Uvicorn)
#   frontend → http://localhost       (React + Nginx)
#   ollama   → http://localhost:11434 (LLM local)
#   swagger  → http://localhost:8000/docs
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Détection IP locale (Wi-Fi) ────────────────────────────────────────────────
LOCAL_IP=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' \
  || hostname -I 2>/dev/null | awk '{print $1}' \
  || echo "")

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       Smart Doc Assistant — Docker                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📋 Endpoints :"
echo "   Frontend → http://localhost"
echo "   Backend  → http://localhost:8000"
echo "   Swagger  → http://localhost:8000/docs"
echo "   Ollama   → http://localhost:11434"
[ -n "$LOCAL_IP" ] && echo "   📱 LAN    → http://$LOCAL_IP  (téléphone / tablette)"
echo ""

cd "$ROOT_DIR/docker"

# ── Parse des options ─────────────────────────────────────────────────────────
DETACH=false
BUILD_ONLY=false
NO_BUILD=false
COMPOSE_SERVICES=""

for arg in "$@"; do
  case $arg in
    -d|--detach)    DETACH=true ;;
    --build-only)   BUILD_ONLY=true ;;
    --no-build)     NO_BUILD=true ;;
    --backend)      COMPOSE_SERVICES="backend ollama" ;;
    --frontend)     COMPOSE_SERVICES="frontend" ;;
  esac
done

# ── Vérifier que Docker est lancé ─────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker n'est pas démarré. Lance Docker Desktop et réessaie."
  exit 1
fi

# ── Build only ────────────────────────────────────────────────────────────────
if [ "$BUILD_ONLY" = true ]; then
  echo "🔨 Build des images Docker..."
  if [ -n "$COMPOSE_SERVICES" ]; then
    docker compose build $COMPOSE_SERVICES
  else
    docker compose build
  fi
  echo "✅ Build terminé"
  exit 0
fi

# ── Build + lancement ─────────────────────────────────────────────────────────
BUILD_FLAG="--build"
[ "$NO_BUILD" = true ] && BUILD_FLAG=""

if [ "$DETACH" = true ]; then
  echo "🔨 Build + lancement en arrière-plan..."
  if [ -n "$COMPOSE_SERVICES" ]; then
    docker compose up $BUILD_FLAG -d $COMPOSE_SERVICES
  else
    docker compose up $BUILD_FLAG -d
  fi
  echo ""
  echo "✅ Conteneurs démarrés en arrière-plan"
  echo ""
  echo "Commandes utiles :"
  echo "  npm run docker:logs    → Voir les logs en direct"
  echo "  npm run docker:ps      → État des conteneurs"
  echo "  npm run docker:stop    → Arrêter"
  echo ""
  # Vérification Ollama — modèles présents ?
  echo "⏳ Vérification Ollama..."
  sleep 3
  if docker exec smart-doc-ollama ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "✅ Ollama — modèles présents"
  else
    echo "⚠️  Premier lancement : modèles Ollama à télécharger :"
    echo "   docker exec smart-doc-ollama ollama pull nomic-embed-text"
    echo "   docker exec smart-doc-ollama ollama pull mistral"
  fi
  echo ""
else
  echo "🔨 Build + lancement des conteneurs... (Ctrl+C pour arrêter)"
  echo ""
  if [ -n "$COMPOSE_SERVICES" ]; then
    docker compose up $BUILD_FLAG $COMPOSE_SERVICES
  else
    docker compose up $BUILD_FLAG
  fi
fi
