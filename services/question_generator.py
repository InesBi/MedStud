# services/question_generator.py
from __future__ import annotations
import json, re, time, hashlib, random
from typing import List, Dict, Any
import requests

# ---- TUNE HERE ---------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b-instruct"  # fast + good-enough
TIMEOUT_S = 18                          # per request timeout
BATCH_SIZE = 5                          # how many chunks per LLM call
MAX_QUESTIONS = 20                      # safety cap
NUM_PREDICT = 220                       # keep outputs short
NUM_CTX = 1024                          # smaller ctx speeds up decoding
TEMPERATURE = 0.2                       # more deterministic
# -----------------------------------------------------------------------------

def _hash_key(text: str, model: str, n_q: int, mode: str) -> str:
    h = hashlib.sha1()
    h.update(text.encode("utf-8", errors="ignore"))
    h.update(f"|{model}|{n_q}|{mode}".encode())
    return h.hexdigest()[:16]

_cache: Dict[str, List[Dict[str, Any]]] = {}

def _pick_top_chunks(chunks: List[str], want: int) -> List[str]:
    """Heuristic: prefer mid-length factual sentences; dedup; shuffle lightly."""
    uniq = []
    seen = set()
    for c in chunks:
        s = " ".join(c.split())
        if 40 <= len(s) <= 300 and s not in seen:
            uniq.append(s); seen.add(s)
    # light shuffle for variety, but stable-ish
    random.seed(42)
    random.shuffle(uniq)
    return uniq[:max(1, want)]

def _prompt_for_batch(batch: List[str], want_each: int = 1) -> str:
    examples = [
        "Which receptor does drug X primarily target?",
        "What is the most likely diagnosis given the findings?",
        "Which pathophysiologic mechanism explains the sign?"
    ]
    return f"""You are a medical exam item writer.

Given the following study snippets, generate {want_each} multiple-choice question per snippet.
Focus on key facts; avoid trivia. Vary stems; keep options plausible. One correct answer only.

Return ONLY valid JSON in this exact schema:
{{
  "questions": [
    {{
      "stem": "string",
      "options": ["A", "B", "C", "D"],
      "answer_index": 0,
      "explanation": "brief rationale",
      "source_idx": 0
    }}
  ]
}}

Snippets (index them by order 0..{len(batch)-1}):
{json.dumps(batch, ensure_ascii=False, indent=2)}
"""
def _post_ollama(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT,
        },
        "format": "json"  # many models honor this; we still robust-parse below
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json().get("response", "")

def _extract_json(s: str) -> Dict[str, Any]:
    # Try direct JSON first
    try:
        return json.loads(s)
    except Exception:
        pass
    # Fallback: find the last {...} block
    m = re.findall(r"\{(?:[^{}]|(?R))*\}", s, flags=re.S)
    for block in (m[::-1] if m else []):
        try:
            return json.loads(block)
        except Exception:
            continue
    return {}

def _normalize_items(obj: Dict[str, Any], batch_len: int) -> List[Dict[str, Any]]:
    out = []
    qs = obj.get("questions") if isinstance(obj, dict) else None
    if not isinstance(qs, list):
        return out
    for q in qs:
        stem = (q.get("stem") or "").strip()
        opts = q.get("options") or []
        if not stem or not isinstance(opts, list) or len(opts) < 2:
            continue
        ai = q.get("answer_index", 0)
        try:
            ai = int(ai)
        except Exception:
            ai = 0
        if ai < 0 or ai >= len(opts):
            ai = 0
        src = q.get("source_idx", 0)
        try:
            src = max(0, min(int(src), max(0, batch_len-1)))
        except Exception:
            src = 0
        out.append({
            "type": "mcq",
            "prompt": stem,
            "options": opts[:4],
            "answer": opts[ai] if ai < len(opts) else opts[0],
            "explanation": (q.get("explanation") or "").strip(),
            "source_idx": src
        })
    return out

def _template_fallback(sent: str, distract_pool: List[str]) -> Dict[str, Any]:
    """Very fast local fallback with no LLM: fill-in-the-blank from a keyword."""
    # pick a keyword-ish token (simple heuristic: longest word > 5 chars)
    tokens = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", sent)]
    target = sorted(tokens, key=len, reverse=True)[:1]
    if not target:
        # fallback to T/F
        return {
            "type": "truefalse",
            "prompt": f"True or False: {sent}",
            "options": ["True", "False"],
            "answer": "True",
            "explanation": "Statement taken verbatim from source.",
            "source_idx": 0
        }
    answer = target[0]
    stem = sent.replace(answer, "____", 1)
    # distractors from pool: pick different-looking words
    pool = [w for w in distract_pool if w.lower() != answer.lower() and 4 <= len(w) <= 18]
    random.seed(len(sent))
    random.shuffle(pool)
    distractors = []
    for w in pool:
        if w.lower() != answer.lower() and w not in distractors:
            distractors.append(w)
        if len(distractors) >= 3:
            break
    options = [answer] + distractors
    random.shuffle(options)
    return {
        "type": "mcq",
        "prompt": f"Fill in the blank: {stem}",
        "options": options,
        "answer": answer,
        "explanation": "Key-term recall from the snippet.",
        "source_idx": 0
    }

def _fast_keywords(snippets: List[str], limit: int = 80) -> List[str]:
    words = []
    for s in snippets:
        for w in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", s):
            words.append(w)
            if len(words) >= limit:
                return words
    return words

def generate_questions(pdf_data: Dict[str, Any],
                       n_questions: int = 10,
                       model: str = DEFAULT_MODEL,
                       mode: str = "fast") -> List[Dict[str, Any]]:
    """
    mode: "fast" (few big batches), "quality" (more tokens), "template" (no LLM)
    """
    n_questions = max(1, min(int(n_questions), MAX_QUESTIONS))
    chunks = (pdf_data or {}).get("chunks") or []
    if not chunks:
        return []

    # tune knobs by mode
    global NUM_PREDICT, NUM_CTX
    if mode == "quality":
        ctx, pred = 2048, 350
    elif mode == "template":
        ctx, pred = 0, 0
    else:  # fast
        ctx, pred = 1024, 220
    NUM_CTX, NUM_PREDICT = ctx or NUM_CTX, pred or NUM_PREDICT

    top = _pick_top_chunks(chunks, want=min(4 * n_questions, 40))
    cache_key = _hash_key("\n".join(top), model, n_questions, mode)
    if cache_key in _cache:
        return _cache[cache_key][:n_questions]

    # pure template mode (no LLM calls)
    if mode == "template":
        pool = _fast_keywords(top, limit=120)
        qs = [_template_fallback(s, pool) for s in top[:n_questions]]
        _cache[cache_key] = qs
        return qs

    # batch call the LLM
    questions: List[Dict[str, Any]] = []
    want_each = 1  # one question per snippet; adjust if you want 2 each
    batches = [top[i:i+BATCH_SIZE] for i in range(0, len(top), BATCH_SIZE)]
    for b in batches:
        if len(questions) >= n_questions:
            break
        prompt = _prompt_for_batch(b, want_each=want_each)
        try:
            raw = _post_ollama(model, prompt)
            obj = _extract_json(raw)
            items = _normalize_items(obj, batch_len=len(b))
            if not items:
                # tight fallback: craft 1-2 items locally
                pool = _fast_keywords(b, limit=60)
                items = [_template_fallback(b[0], pool)]
        except Exception:
            pool = _fast_keywords(b, limit=60)
            items = [_template_fallback(b[0], pool)]
        questions.extend(items)

    # trim & dedup stems
    seen = set()
    clean = []
    for q in questions:
        stem = q.get("prompt", "").strip()
        if not stem or stem in seen:
            continue
        seen.add(stem)
        clean.append(q)
        if len(clean) >= n_questions:
            break

    _cache[cache_key] = clean
    return clean
