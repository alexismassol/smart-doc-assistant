#!/bin/bash
# dev.sh — Lance backend FastAPI + frontend React en parallèle
# Backend sur port 8000, Frontend sur port 5173
# Usage : npm run dev

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════╗"
echo "║     Smart Doc Assistant — npm run dev         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "   Backend → http://localhost:8000"
echo "   Frontend → http://localhost:5173"
echo "   Swagger  → http://localhost:8000/docs"
echo ""
echo "Ctrl+C pour arrêter les deux serveurs"
echo ""

# ── Vérifications préliminaires ────────────────────────────────────────────────
if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
    echo "❌  Venv Python manquant. Lancer d'abord : npm run setup"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "❌  node_modules manquant. Lancer d'abord : npm run setup"
    exit 1
fi

# Trap pour tuer les deux processus au Ctrl+C
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "🛑  Arrêt des serveurs..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# ── Backend FastAPI ────────────────────────────────────────────────────────────
cd "$PROJECT_ROOT"
source backend/venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "🐍  Backend démarré (PID $BACKEND_PID)"

# ── Frontend React + Vite ─────────────────────────────────────────────────────
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "⚛️   Frontend démarré (PID $FRONTEND_PID)"

echo ""

# Attendre que l'un des deux se termine (ou Ctrl+C)
wait "$BACKEND_PID" "$FRONTEND_PID"
