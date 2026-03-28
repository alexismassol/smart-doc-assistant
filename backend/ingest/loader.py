"""
loader.py — Document loaders pour le pipeline d'ingestion
Uses: LangChain (UnstructuredMarkdownLoader, CSVLoader, PyMuPDFLoader),
      httpx (HTTP async), BeautifulSoup4 (HTML parsing)
Formats supportés : PDF, CSV, Markdown, URL
"""
import os
from typing import List

import httpx
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader, CSVLoader
from langchain_core.documents import Document


def load_pdf(file_path: str) -> List[Document]:
    """
    Charge un fichier PDF et retourne une liste de Documents LangChain.
    Utilise PyMuPDFLoader (rapide, extrait texte + métadonnées page).

    Args:
        file_path: Chemin absolu ou relatif vers le fichier PDF.

    Returns:
        Liste de Documents, un par page, avec métadonnées source/page/type.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF introuvable : {file_path}")

    # LangChain PyMuPDFLoader — parsing rapide avec métadonnées de page
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    # Enrichissement des métadonnées
    for doc in docs:
        doc.metadata["source"] = os.path.basename(file_path)
        doc.metadata["type"] = "pdf"

    return docs


def load_csv(file_path: str) -> List[Document]:
    """
    Charge un fichier CSV et retourne une liste de Documents LangChain.
    Chaque ligne devient un Document avec le contenu de la ligne.

    Args:
        file_path: Chemin vers le fichier CSV.

    Returns:
        Liste de Documents avec métadonnées source/type/row.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        ValueError: Si le fichier CSV est vide.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV introuvable : {file_path}")

    # LangChain CSVLoader — chaque ligne → un Document
    loader = CSVLoader(file_path=file_path)
    docs = loader.load()

    if not docs:
        raise ValueError(f"Le fichier CSV est vide : {file_path}")

    # Enrichissement des métadonnées
    for i, doc in enumerate(docs):
        doc.metadata["source"] = os.path.basename(file_path)
        doc.metadata["type"] = "csv"
        doc.metadata["row"] = i

    return docs


def load_markdown(file_path: str) -> List[Document]:
    """
    Charge un fichier Markdown (.md ou .txt) et retourne un Document LangChain.

    Args:
        file_path: Chemin vers le fichier Markdown.

    Returns:
        Liste contenant un unique Document avec le contenu complet.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc = Document(
        page_content=content,
        metadata={
            "source": os.path.basename(file_path),
            "type": "markdown",
            "page": 0,
        },
    )
    return [doc]


def load_url(url: str, timeout: int = 15) -> List[Document]:
    """
    Charge le contenu textuel d'une URL via httpx + BeautifulSoup4.
    Extrait uniquement le texte visible (balises <p>, <h1-h6>, <li>).

    Args:
        url: URL de la page à ingérer.
        timeout: Timeout en secondes (défaut 15).

    Returns:
        Liste de Documents avec le contenu texte de la page.

    Raises:
        ValueError: Si la requête HTTP échoue.
    """
    try:
        # httpx — client HTTP moderne, async-compatible
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Impossible de charger l'URL {url} : {e}")

    # BeautifulSoup4 — extraction du texte visible uniquement
    soup = BeautifulSoup(response.text, "lxml")

    # Supprime les scripts et styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    if not text.strip():
        raise ValueError(f"Aucun contenu textuel trouvé à l'URL : {url}")

    doc = Document(
        page_content=text,
        metadata={
            "source": url,
            "type": "url",
            "page": 0,
        },
    )
    return [doc]


def load_document(file_path: str) -> List[Document]:
    """
    Point d'entrée unifié — détecte le format et dispatch vers le bon loader.

    Args:
        file_path: Chemin vers le fichier (PDF, CSV, MD, TXT).

    Returns:
        Liste de Documents LangChain.

    Raises:
        ValueError: Si le format n'est pas supporté.
    """
    ext = os.path.splitext(file_path)[1].lower()
    loaders = {
        ".pdf": load_pdf,
        ".csv": load_csv,
        ".md": load_markdown,
        ".txt": load_markdown,
    }
    if ext not in loaders:
        raise ValueError(f"Format non supporté : {ext}. Formats acceptés : {list(loaders.keys())}")

    return loaders[ext](file_path)
