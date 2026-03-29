"""
test_loader.py - Tests unitaires pour ingest/loader.py
TDD Phase Red : définit le contrat de loader.py avant son implémentation.
Uses: pytest, unittest.mock, LangChain Document
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestLoadMarkdown:
    """Tests pour le chargement de fichiers Markdown."""

    def test_load_markdown_returns_documents(self, tmp_path):
        """load_markdown() doit retourner une liste de Documents LangChain."""
        from backend.ingest.loader import load_markdown
        md_file = tmp_path / "test.md"
        md_file.write_text("# Titre\n\nContenu du document markdown.")
        docs = load_markdown(str(md_file))
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_load_markdown_has_content(self, tmp_path):
        """Le contenu du fichier doit être dans page_content."""
        from backend.ingest.loader import load_markdown
        md_file = tmp_path / "test.md"
        md_file.write_text("Contenu important du markdown.")
        docs = load_markdown(str(md_file))
        assert "Contenu important" in docs[0].page_content

    def test_load_markdown_has_source_metadata(self, tmp_path):
        """Les métadonnées doivent contenir source et type."""
        from backend.ingest.loader import load_markdown
        md_file = tmp_path / "test.md"
        md_file.write_text("Contenu.")
        docs = load_markdown(str(md_file))
        assert "source" in docs[0].metadata
        assert docs[0].metadata.get("type") == "markdown"

    def test_load_markdown_file_not_found_raises(self):
        """Un fichier inexistant doit lever FileNotFoundError."""
        from backend.ingest.loader import load_markdown
        with pytest.raises(FileNotFoundError):
            load_markdown("/chemin/inexistant/fichier.md")


class TestLoadCSV:
    """Tests pour le chargement de fichiers CSV."""

    def test_load_csv_returns_documents(self, tmp_path):
        """load_csv() doit retourner une liste de Documents."""
        from backend.ingest.loader import load_csv
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("nom,valeur\nLangChain,0.3\nChromaDB,0.5\n")
        docs = load_csv(str(csv_file))
        assert isinstance(docs, list)
        assert len(docs) > 0

    def test_load_csv_has_type_metadata(self, tmp_path):
        """Les métadonnées doivent contenir type=csv."""
        from backend.ingest.loader import load_csv
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col\nvaleur\n")
        docs = load_csv(str(csv_file))
        assert docs[0].metadata.get("type") == "csv"

    def test_load_csv_empty_raises(self, tmp_path):
        """Un CSV vide (sans lignes) doit lever ValueError."""
        from backend.ingest.loader import load_csv
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        with pytest.raises(ValueError):
            load_csv(str(csv_file))


class TestLoadPDF:
    """Tests pour le chargement de fichiers PDF."""

    def test_load_pdf_returns_documents(self):
        """load_pdf() doit retourner une liste de Documents avec un vrai PDF de test."""
        from backend.ingest.loader import load_pdf
        sample_pdf = os.path.join(
            os.path.dirname(__file__), "../../..", "data/sample_docs/example.pdf"
        )
        if not os.path.exists(sample_pdf):
            pytest.skip("example.pdf non disponible - sera testé en intégration")
        docs = load_pdf(sample_pdf)
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_load_pdf_has_page_metadata(self):
        """Chaque Document PDF doit avoir un numéro de page dans les métadonnées."""
        from backend.ingest.loader import load_pdf
        sample_pdf = os.path.join(
            os.path.dirname(__file__), "../../..", "data/sample_docs/example.pdf"
        )
        if not os.path.exists(sample_pdf):
            pytest.skip("example.pdf non disponible")
        docs = load_pdf(sample_pdf)
        for doc in docs:
            assert "page" in doc.metadata
            assert "source" in doc.metadata
            assert doc.metadata.get("type") == "pdf"

    def test_load_pdf_file_not_found_raises(self):
        """Un PDF inexistant doit lever FileNotFoundError."""
        from backend.ingest.loader import load_pdf
        with pytest.raises(FileNotFoundError):
            load_pdf("/inexistant.pdf")


class TestLoadURL:
    """Tests pour l'ingestion d'URLs (web scraping)."""

    def test_load_url_returns_documents(self):
        """load_url() doit retourner des Documents depuis une URL mockée."""
        from backend.ingest.loader import load_url
        mock_html = "<html><body><p>Contenu de la page web.</p></body></html>"
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            docs = load_url("http://example.com/doc")
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert "Contenu de la page web" in docs[0].page_content

    def test_load_url_has_source_metadata(self):
        """Les Documents URL doivent avoir source=url et type=url."""
        from backend.ingest.loader import load_url
        mock_html = "<html><body><p>Texte.</p></body></html>"
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            docs = load_url("http://example.com/page")
        assert docs[0].metadata.get("source") == "http://example.com/page"
        assert docs[0].metadata.get("type") == "url"

    def test_load_url_http_error_raises(self):
        """Une erreur HTTP doit lever une ValueError."""
        from backend.ingest.loader import load_url
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            with pytest.raises(ValueError, match="Impossible de charger l'URL"):
                load_url("http://inexistant.example.com")
