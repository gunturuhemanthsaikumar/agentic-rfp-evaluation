from pathlib import Path
from pypdf import PdfReader

def extract_pdf_document(pdf_path: Path) -> dict:
    """Document tool: deterministic PDF extraction, page labelled for evidence traceability."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        pages.append({"page": idx, "text": text})
    full_text = "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in pages)
    return {"file_name": pdf_path.name, "pages": pages, "text": full_text}
