# doctor.py
# Health check for the Medical Study Companion environment.
# Runs checks for: Python/pip paths, spaCy + SciSpaCy + model, PyMuPDF, Streamlit, and Ollama (optional).

from __future__ import annotations
import argparse
import importlib
import json
import os
import platform
import sys
import textwrap
import time
from typing import Optional

# -----------------------------
# tiny coloring helper (no extra deps)
# -----------------------------
class C:
    G = "\033[92m"  # green
    Y = "\033[93m"  # yellow
    R = "\033[91m"  # red
    B = "\033[94m"  # blue
    D = "\033[0m"   # reset

def line(msg: str = ""):
    print(msg)

def ok(msg: str):
    print(f"{C.G}✅ {msg}{C.D}")

def warn(msg: str):
    print(f"{C.Y}⚠️  {msg}{C.D}")

def bad(msg: str):
    print(f"{C.R}❌ {msg}{C.D}")

def info(msg: str):
    print(f"{C.B}ℹ️  {msg}{C.D}")

# -----------------------------
# utils
# -----------------------------
def import_optional(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

def check_python_paths():
    line("=== Python / Pip ===")
    ok(f"Python: {sys.version.split()[0]} ({sys.executable})")
    # figure out pip linked to current interpreter
    try:
        import pip  # type: ignore
        pip_exe = os.popen(f'"{sys.executable}" -m pip --version').read().strip()
        ok(f"Pip: {pip_exe}")
        # show which 'pip' is on PATH to catch mismatches
        which_pip = os.popen("which pip").read().strip()
        info(f"`which pip` -> {which_pip or 'N/A'}")
        if which_pip and not which_pip.startswith(os.path.dirname(sys.executable)):
            warn("Your PATH's pip is NOT the env's pip. Always use `python -m pip ...` in this env.")
    except Exception as e:
        bad(f"Pip check failed: {e}")
        return False
    return True

def check_spacy_scispacy(model_name: str = "en_core_sci_md") -> bool:
    line("\n=== spaCy / SciSpaCy ===")
    ok_spacy = ok_scispacy = ok_model = True

    spacy = import_optional("spacy")
    if not spacy:
        bad("spaCy is NOT installed. Try:  python -m pip install spacy==3.7.5")
        ok_spacy = False
    else:
        ok(f"spaCy installed: v{spacy.__version__}")

    scispacy = import_optional("scispacy")
    if not scispacy:
        bad("SciSpaCy is NOT installed. Try:  python -m pip install scispacy==0.5.4")
        ok_scispacy = False
    else:
        ok("SciSpaCy installed: v0.5.4 (expected)")

    if spacy:
        try:
            nlp = spacy.load(model_name)
            ok(f"Model loaded: {model_name} (pipes: {', '.join(nlp.pipe_names) or 'none'})")
        except Exception as e:
            ok_model = False
            bad(f"Failed to load model '{model_name}': {e}")
            info(textwrap.dedent(f"""\
                install via:
                  python -m pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/{model_name}-0.5.4.tar.gz
                """))
    return ok_spacy and ok_scispacy and ok_model

def check_pymupdf() -> bool:
    line("\n=== PyMuPDF (fitz) ===")
    fitz = import_optional("fitz")
    if not fitz:
        bad("PyMuPDF (fitz) NOT installed. Try:  python -m pip install pymupdf==1.24.9")
        return False
    try:
        ver = getattr(fitz, "__version__", "unknown")
        ok(f"PyMuPDF import OK (version: {ver})")
        # sanity open
        doc = fitz.open()  # empty doc
        ok("Basic open/create doc OK")
        return True
    except Exception as e:
        bad(f"PyMuPDF runtime check failed: {e}")
        return False

def check_streamlit() -> bool:
    line("\n=== Streamlit ===")
    st = import_optional("streamlit")
    if not st:
        bad("Streamlit NOT installed. Try:  python -m pip install streamlit")
        return False
    ok(f"Streamlit import OK (version: {getattr(st, '__version__', 'unknown')})")
    return True

def check_nmslib_optional() -> bool:
    # optional: present because scispacy depends on it, but not required for basic NER usage
    nmslib = import_optional("nmslib")
    if nmslib:
        ok("nmslib import OK (binary present)")
        return True
    else:
        warn("nmslib NOT installed (ok if you are not using UMLS linker). If needed:  conda install -c conda-forge nmslib==2.1.1")
        return True  # not critical

def check_ollama(timeout: float = 2.0) -> bool:
    line("\n=== Ollama (optional) ===")
    req = import_optional("requests")
    if not req:
        warn("requests not installed; skipping Ollama HTTP check. (Install with: python -m pip install requests)")
        return True
    url = "http://localhost:11434/api/tags"
    try:
        resp = req.get(url, timeout=timeout)
        if resp.ok:
            tags = []
            try:
                tags = [m.get("name") for m in resp.json().get("models", [])]
            except Exception:
                pass
            ok(f"Ollama reachable at {url} (models: {', '.join(tags) or 'unknown'})")
            return True
        else:
            warn(f"Ollama responded with status {resp.status_code}. Is the daemon running? Try: `ollama serve` then `ollama pull mistral`")
            return False
    except Exception as e:
        warn(f"Ollama not reachable: {e}. If you plan to use local LLMs, start it with `ollama serve`.")
        return True  # optional, don't fail whole check

def summary(failures: list[str]):
    line("\n=== Summary ===")
    if failures:
        for f in failures:
            bad(f)
        print()
        bad("Environment check FAILED (see items above).")
        sys.exit(1)
    else:
        ok("All critical checks passed. You're good to go! 🚀")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Environment healthcheck for Medical Study Companion")
    parser.add_argument("--model", default="en_core_sci_md", help="spaCy/SciSpaCy model to load")
    parser.add_argument("--no-ollama", action="store_true", help="skip Ollama connectivity check")
    args = parser.parse_args()

    line(f"Doctor 🩺 for Medical Study Companion   (Python {sys.version.split()[0]} on {platform.platform()})")
    failures: list[str] = []

    if not check_python_paths():
        failures.append("Pip environment not healthy / mismatched PATH.")

    if not check_spacy_scispacy(args.model):
        failures.append("spaCy / SciSpaCy / model check failed.")

    if not check_pymupdf():
        failures.append("PyMuPDF (fitz) check failed.")

    if not check_streamlit():
        failures.append("Streamlit missing.")

    check_nmslib_optional()

    if not args.no_ollama:
        # don't mark as failure; it's optional to run locally
        check_ollama()

    summary(failures)

if __name__ == "__main__":
    main()
