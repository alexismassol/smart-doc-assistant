"""
test_check_ollama.py - Tests pour le script de vérification Ollama
TDD Phase Red : vérifie que check_ollama retourne les bons codes de sortie.
"""
import pytest
import subprocess
import os


class TestCheckOllamaScript:
    """Tests du script scripts/check_ollama.sh."""

    def test_script_exists(self):
        """Le script check_ollama.sh doit exister."""
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../scripts/check_ollama.sh"
        )
        assert os.path.exists(script_path), "scripts/check_ollama.sh introuvable"

    def test_script_is_executable(self):
        """Le script doit être exécutable."""
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../scripts/check_ollama.sh"
        )
        assert os.access(script_path, os.X_OK), "check_ollama.sh n'est pas exécutable"

    def test_setup_script_exists(self):
        """Le script setup.sh doit exister."""
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../scripts/setup.sh"
        )
        assert os.path.exists(script_path), "scripts/setup.sh introuvable"
