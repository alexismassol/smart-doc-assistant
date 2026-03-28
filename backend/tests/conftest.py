"""
conftest.py — Fixtures partagées pour tous les tests backend
Uses: pytest, ChromaDB in-memory, unittest.mock
"""
import pytest
import os
import sys

# Ajoute la racine du backend au PYTHONPATH pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


@pytest.fixture(scope="session")
def test_env_vars():
    """Variables d'environnement de test (ne touche pas à .env)."""
    return {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "mistral",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "EMBEDDING_PROVIDER": "ollama",
        "CHROMA_PERSIST_DIR": "/tmp/test_chroma_db",
        "CHROMA_COLLECTION": "test_smart_docs",
        "BACKEND_PORT": "8001",
        "CORS_ORIGINS": "http://localhost:5173",
        "RETRIEVAL_TOP_K": "5",
        "RETRIEVAL_SCORE_THRESHOLD": "0.4",
        "MEMORY_WINDOW": "5",
    }


@pytest.fixture(scope="function")
def sample_text():
    """Texte de test pour les tests d'ingestion."""
    return """
    LangChain est un framework Python pour construire des applications LLM.
    Il fournit des loaders, des text splitters, et des chains.
    ChromaDB est une base vectorielle open-source légère.
    Elle supporte la recherche par similarité cosinus.
    FastAPI est un framework web Python moderne et rapide.
    Il génère automatiquement une documentation Swagger.
    """


@pytest.fixture(scope="function")
def sample_documents():
    """Documents LangChain de test."""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="LangChain est un framework pour LLM.",
            metadata={"source": "test.pdf", "page": 1, "type": "pdf"}
        ),
        Document(
            page_content="ChromaDB stocke des vecteurs d'embedding.",
            metadata={"source": "test.pdf", "page": 2, "type": "pdf"}
        ),
        Document(
            page_content="FastAPI crée des APIs REST asynchrones.",
            metadata={"source": "test.md", "page": 0, "type": "markdown"}
        ),
    ]


@pytest.fixture(scope="session", autouse=True)
def create_test_pdf():
    """Crée le PDF de test si absent."""
    pdf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "sample_docs", "example.pdf"
    )
    if not os.path.exists(pdf_path):
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 75 >>
stream
BT
/F1 12 Tf
50 750 Td
(Smart Doc Assistant test document.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000402 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
475
%%EOF"""
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
