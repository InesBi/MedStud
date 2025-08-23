from __future__ import annotations
import io
import re
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
import spacy

# ---- Model loader: prefer domain NER if present; fallback to SciSpaCy core; final fallback is blank English with sentencizer
_PREFERRED_MODELS = [
    "en_ner_bc5cdr_md",  # diseases+chemicals (if you've installed it)
    "en_core_sci_md",    # general scientific model (entities often labeled "ENTITY")
]

def _load_nlp():
    for name in _PREFERRED_MODELS:
        try:
            return spacy.load(name)
        except Exception:
            continue
    # last resort: blank English with sentence splitter
    nlp = spacy.blank("en")
    if "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp

nlp = _load_nlp()

# Labels we *prefer* when available (bc5cdr, bionlp, etc.). If model doesn't emit these, we accept any entity.
PREFERRED_LABELS = {
    "DISEASE", "CHEMICAL", "ANATOMICAL_SYSTEM", "ORGAN", "ORGANISM",
    "SIGN_OR_SYMPTOM", "GENE_OR_GENE_PRODUCT", "PATHOLOGICAL_FUNCTION",
    "CELL", "CELL_LINE", "TISSUE", "PROCEDURE", "DISORDER"
}

def _to_bytes(pdf_file) -> bytes:
    """Streamlit's uploader gives a file-like. Ensure we read bytes from start."""
    if hasattr(pdf_file, "seek"):
        try:
            pdf_file.seek(0)
        except Exception:
            pass
    if hasattr(pdf_file, "read"):
        data = pdf_file.read()
        # if read() returned a str (rare), encode
        if isinstance(data, str):
            data = data.encode("utf-8", errors="ignore")
        return data
    if isinstance(pdf_file, (bytes, bytearray)):
        return bytes(pdf_file)
    raise TypeError("process_pdf expects a file-like object or PDF bytes")

def _extract_headings_by_font(page) -> List[str]:
    """Use PyMuPDF's 'dict' to find blocks whose max span size is above page median → likely headings."""
    try:
        d = page.get_text("dict")
    except Exception:
        return []
    sizes = []
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size")
                if isinstance(size, (int, float)):
                    sizes.append(float(size))
    if not sizes:
        return []
    sizes.sort()
    median = sizes[len(sizes)//2]

    heads: List[str] = []
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        # compute block max font size
        max_size = 0.0
        texts = []
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "")
                if t:
                    texts.append(t)
                s = span.get("size")
                if isinstance(s, (int, float)):
                    if s > max_size:
                        max_size = float(s)
        txt = "".join(texts).strip()
        # threshold: somewhat larger than median; also avoid very short/noisy lines
        if txt and len(txt) >= 3 and max_size >= median + 2:
            # collapse whitespace, strip bullets
            cleaned = re.sub(r"\s+", " ", txt)
            cleaned = re.sub(r"^[•\-\u2022]\s*", "", cleaned)
            if 3 <= len(cleaned) <= 140:
                heads.append(cleaned)
    return heads

def _unique_preserve_order(items: List[str], limit: int | None = None) -> List[str]:
    seen = set()
    out = []
    for x in items:
        x = x.strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
        if limit and len(out) >= limit:
            break
    return out

def process_pdf(pdf_file) -> Dict:
    """
    Parse a PDF, detect headings via font sizes, run NER, and return learning chunks.
    Returns:
        {
          "headings": [str, ...],
          "chunks": [str, ...],
          "meta": {"pages": int, "model": str, "note": str|None, "entities_found": int}
        }
    """
    pdf_bytes = _to_bytes(pdf_file)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # --- Gather text and headings per page
    all_text_parts: List[str] = []
    found_heads: List[str] = []
    for page in doc:
        found_heads.extend(_extract_headings_by_font(page))
        # full 'text' is usually fine; "blocks" would preserve layout but is noisier
        txt = page.get_text("text") or ""
        all_text_parts.append(txt)

    full_text = "\n".join(all_text_parts).strip()
    if len(full_text) < 40:
        # Likely a scanned PDF (no digital text)
        return {
            "headings": _unique_preserve_order(found_heads, limit=40),
            "chunks": [],
            "meta": {
                "pages": len(doc),
                "model": getattr(nlp, "meta", {}).get("name", "unknown"),
                "note": "No extractable text found. This PDF may be scanned. Consider OCR.",
                "entities_found": 0,
            },
        }

    # --- NLP pass
    parsed = nlp(full_text)

    # Decide label filter: if the model emits any of our preferred labels, use only those; otherwise accept all labels.
    labels_in_doc = {e.label_ for e in parsed.ents}
    use_preferred = bool(labels_in_doc & PREFERRED_LABELS)
    allowed = PREFERRED_LABELS if use_preferred else None

    chunks: List[str] = []
    ent_count = 0
    for sent in parsed.sents:
        ents_in_sent = [e for e in sent.ents if (allowed is None or e.label_ in allowed)]
        if ents_in_sent:
            ent_count += len(ents_in_sent)
            # Clean sentence and keep it as a "learning chunk"
            s = re.sub(r"\s+", " ", sent.text).strip()
            if 20 <= len(s) <= 400:  # keep mid-length chunks; tune as needed
                chunks.append(s)

    # Dedup and cap to avoid overwhelming the UI
    headings = _unique_preserve_order(found_heads, limit=60)
    chunks = _unique_preserve_order(chunks, limit=300)

    note = None
    if not chunks:
        note = ("No entity-bearing sentences found with current model. "
                "Try installing 'en_ner_bc5cdr_md' for DISEASE/CHEMICAL coverage, "
                "or loosen filters.")

    return {
        "headings": headings,
        "chunks": chunks,
        "meta": {
            "pages": len(doc),
            "model": getattr(nlp, "meta", {}).get("name", "unknown"),
            "note": note,
            "entities_found": ent_count,
        },
    }
