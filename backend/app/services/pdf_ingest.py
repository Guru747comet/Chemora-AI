"""PDF text extraction and cautious, rule-based hints."""
import re
import fitz


class PDFProcessingError(ValueError):
    pass


def extract_pdf(data: bytes) -> dict:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PDFProcessingError("The uploaded file could not be opened as a PDF.") from exc

    pages = []
    all_text = []
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": page_number, "text": text})
            all_text.append(text)
    doc.close()
    full_text = "\n\n".join(all_text).strip()
    if not full_text:
        raise PDFProcessingError(
            "No selectable text was found. This may be a scanned PDF; OCR is not configured in this starter version."
        )
    return {
        "page_count": len(pages),
        "pages": pages,
        "text": full_text,
        "summary": make_rule_based_hints(full_text, pages),
    }


def make_rule_based_hints(text: str, pages: list[dict]) -> dict:
    """Return review hints; not a scientific entity-recognition model."""
    normalized = re.sub(r"\s+", " ", text)
    lower = normalized.lower()
    disease_vocab = [
        "cancer", "diabetes", "alzheimer", "parkinson", "malaria", "tuberculosis",
        "asthma", "arthritis", "anaemia", "anemia", "influenza", "fever", "hypertension",
    ]
    possible_disease_terms = sorted({term for term in disease_vocab if term in lower})

    # This intentionally returns candidate symbols only as review hints.
    gene_symbols = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", text)))
    common_words = {
        "PDF", "DNA", "RNA", "ATP", "ADP", "USA", "UK", "WHO", "API", "AI", "ML",
        "THE", "AND", "FOR", "WITH", "FROM", "FIG", "TABLE", "RESULTS", "METHODS",
        "INTRODUCTION", "CONCLUSION", "ABSTRACT", "REFERENCES", "PDB", "SMILES", "ADMET",
    }
    gene_symbols = [symbol for symbol in gene_symbols if symbol not in common_words][:30]

    top_page = pages[0]["text"][:700] if pages else ""
    return {
        "extraction_mode": "rule-based text scan; user review required",
        "possible_disease_terms": possible_disease_terms,
        "possible_gene_or_protein_symbols": gene_symbols,
        "first_page_excerpt": top_page,
        "warning": "These are keyword hints, not validated disease or target identifications. Confirm each field against the source document.",
    }
