#!/bin/bash
# start-backend.sh - Lance uniquement le backend FastAPI
# Utilisé par : npm run start:backend / npm run start (via concurrently)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
source backend/venv/bin/activate

# Afficher l'adresse IP locale pour accès depuis téléphone/tablette
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$LOCAL_IP" ]; then
  echo "📱 Accès réseau local : http://$LOCAL_IP:5173"
fi

exec uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
