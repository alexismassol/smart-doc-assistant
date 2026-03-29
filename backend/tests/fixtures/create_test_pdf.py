"""
create_test_pdf.py - Génère un PDF de test minimal pour les tests unitaires
Usage: python create_test_pdf.py
"""
import os


def create_minimal_pdf(output_path: str) -> None:
    """Crée un PDF minimal valide avec du texte."""
    # PDF minimal valide (structure PDF 1.4 basique)
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
<< /Length 80 >>
stream
BT
/F1 12 Tf
50 750 Td
(Smart Doc Assistant - Document de test PDF.) Tj
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
0000000407 00000 n

trailer
<< /Size 6 /Root 1 0 R >>
startxref
480
%%EOF"""
    with open(output_path, "wb") as f:
        f.write(pdf_content)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    out = os.path.join(os.path.dirname(__file__), "sample.pdf")
    create_minimal_pdf(out)
    print(f"PDF créé : {out}")
