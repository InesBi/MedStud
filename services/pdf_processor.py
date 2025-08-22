import fitz  # PyMuPDF
import spacy
import scispacy
import en_core_sci_md

nlp = en_core_sci_md.load()

def process_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    parsed = nlp(text)
    headings = set()
    chunks = []
    for sent in parsed.sents:
        ents = [e.text for e in sent.ents if e.label_ in ["DISEASE", "CHEMICAL", "ANATOMICAL_SITE"]]
        if ents:
            chunks.append(sent.text)
            if sent.start_char < 100:
                headings.update(ents)
    return {"headings": list(headings), "chunks": chunks}
