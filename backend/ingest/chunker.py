"""
chunker.py - Découpage de documents en chunks pour le pipeline RAG
Uses: LangChain RecursiveCharacterTextSplitter
Paramètres : chunk_size=500 tokens, chunk_overlap=50
"""
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Document]:
    """
    Découpe une liste de Documents en chunks de taille fixe avec overlap.

    Utilise LangChain RecursiveCharacterTextSplitter qui tente de couper
    sur les séparateurs naturels (paragraphes, phrases, mots) avant de couper
    arbitrairement - meilleur résultat pour le retrieval.

    Args:
        documents: Liste de Documents LangChain à découper.
        chunk_size: Taille maximale d'un chunk en caractères (défaut 500).
        chunk_overlap: Chevauchement entre chunks consécutifs (défaut 50).

    Returns:
        Liste de Documents découpés avec métadonnées enrichies (chunk_index).
    """
    if not documents:
        return []

    # LangChain RecursiveCharacterTextSplitter
    # Séparateurs : paragraphes → phrases → mots → caractères
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    # Ajout de l'index de chunk dans les métadonnées
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    return chunks
