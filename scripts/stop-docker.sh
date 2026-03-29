#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# stop-docker.sh - Arrêt Docker de Smart Doc Assistant
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage : ./scripts/stop-docker.sh [OPTIONS]
#
# OPTIONS :
#   -c, --clean     : Arrête + supprime les images Docker buildées
#   --volumes       : Arrête + supprime les volumes (⚠️ efface ChromaDB + SQLite)
#   --all           : Arrête + supprime images + volumes + prune cache
#
# MODE PAR DÉFAUT : Arrêt simple (docker compose down)
#   → Préserve les images et les volumes (données ChromaDB + history.db)
#
# VOLUMES :
#   smart-doc-assistant-data         → ChromaDB + SQLite history (précieux !)
#   smart-doc-assistant-ollama-models → Modèles Ollama (lourd à re-télécharger)
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "🛑 Smart Doc Assistant - Arrêt Docker"
echo "════════════════════════════════════"
echo ""

cd "$ROOT_DIR/docker"

# Vérifier si Docker est disponible
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker n'est pas démarré."
  exit 1
fi

# Vérifier si des conteneurs sont en cours
RUNNING=$(docker compose ps -q 2>/dev/null | wc -l | tr -d ' ')

if [ "$RUNNING" -gt 0 ]; then
  echo "🔄 Arrêt des conteneurs..."

  case "${1:-}" in
    -c|--clean)
      echo "   + Suppression des images (--clean)"
      docker compose down --rmi local
      ;;
    --volumes)
      echo "   ⚠️  Suppression des volumes (--volumes) - ChromaDB + SQLite effacés !"
      docker compose down --volumes
      ;;
    --all)
      echo "   ⚠️  Suppression complète : images + volumes + cache (--all)"
      docker compose down --rmi all --volumes
      docker system prune -f
      ;;
    *)
      docker compose down
      ;;
  esac

  echo ""
  echo "✅ Conteneurs arrêtés"
else
  echo "ℹ️  Aucun conteneur en cours"
fi

echo ""
echo "🔧 État Docker :"
docker compose ps 2>/dev/null || true
echo ""
echo "Commandes utiles :"
echo "  npm run docker:start         → Redémarrer (avec rebuild)"
echo "  npm run docker:start -- --no-build  → Redémarrer sans rebuild"
echo "  docker volume ls             → Voir les volumes persistants"
echo "  docker system prune -f       → Nettoyer le cache Docker"
echo ""
