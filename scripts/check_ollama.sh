#!/bin/bash
# check_ollama.sh - Vérifie que Ollama est installé et que les modèles requis sont présents
# Modèles requis : mistral (LLM), nomic-embed-text (embeddings)

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║    Smart Doc Assistant - Vérification Ollama  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Vérifier que ollama est installé ───────────────────────────────────────
if ! command -v ollama &> /dev/null; then
    echo "❌  Ollama n'est pas installé."
    echo ""
    echo "    Installation selon votre OS :"
    echo ""
    case "$(uname -s)" in
        Darwin)
            echo "    macOS - Télécharger et installer le .dmg :"
            echo "    https://ollama.ai/download/mac"
            echo ""
            echo "    Ou via Homebrew : brew install ollama"
            ;;
        Linux)
            echo "    Linux (Ubuntu / Debian / Fedora / Arch) :"
            echo "    curl -fsSL https://ollama.ai/install.sh | sh"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "    Windows - Télécharger l'installeur .exe :"
            echo "    https://ollama.ai/download/windows"
            echo ""
            echo "    Note : WSL2 recommandé pour de meilleures performances"
            ;;
        *)
            echo "    Installer depuis : https://ollama.ai"
            ;;
    esac
    echo ""
    echo "    Après installation, lancer : ollama serve"
    exit 1
fi
echo "✅  Ollama installé : $(ollama --version)"

# ── 2. Vérifier que le serveur Ollama tourne ──────────────────────────────────
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌  Le serveur Ollama ne répond pas sur localhost:11434"
    echo "    Lancer avec : ollama serve"
    exit 1
fi
echo "✅  Serveur Ollama actif sur localhost:11434"

# ── 3. Vérifier le modèle mistral ─────────────────────────────────────────────
if ollama list | grep -q "mistral"; then
    echo "✅  Modèle mistral présent"
else
    echo "⚠️   Modèle mistral absent - téléchargement en cours..."
    ollama pull mistral
    echo "✅  Modèle mistral téléchargé"
fi

# ── 4. Vérifier nomic-embed-text ──────────────────────────────────────────────
if ollama list | grep -q "nomic-embed-text"; then
    echo "✅  Modèle nomic-embed-text présent"
else
    echo "⚠️   Modèle nomic-embed-text absent - téléchargement en cours..."
    ollama pull nomic-embed-text
    echo "✅  Modèle nomic-embed-text téléchargé"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅  Tous les prérequis Ollama sont présents  ║"
echo "╚══════════════════════════════════════════════╝"
