
from pathlib import Path
import fitz

def extract_pdf_text(path_or_bytes):
    if isinstance(path_or_bytes, (str, Path)):
        doc = fitz.open(str(path_or_bytes))
    else:
        doc = fitz.open(stream=path_or_bytes, filetype="pdf")

    pages = []
    try:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(f"[Page {i}]\n{text}")
    finally:
        doc.close()

    text = "\n\n".join(pages)
    # Basic cleanup while retaining page markers for evidence traceability.
    lines = [re.sub(r"[ \t]+", " ", line).strip()
             for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

import re
