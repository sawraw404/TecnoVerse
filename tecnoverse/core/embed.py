"""Local text embeddings for matching (user decision, 14 Nov: a local model, no API).

Model: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers, 384 dimensions). Multilingual
because the opportunities are mostly Swedish and the profiles English. Runs on the CPU; the first
call downloads the model once (~470 MB) into the Hugging Face cache.

Opportunity vectors are computed once and stored on `Opportunity.embedding` in data/opportunities.json.
A company's vector is computed from its profile items when matching runs. If sentence-transformers is
not installed, everything returns None and matching falls back to keyword overlap only.

Run: cd tecnoverse && python -m core.embed     -> embeds every opportunity and saves them
"""
import threading
from functools import lru_cache

import numpy as np

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PROFILE_FIELDS = ("industry", "offering", "technology", "expertise", "application_area", "market",
                  "innovation", "priority", "project")


_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load():
    try:
        from sentence_transformers import SentenceTransformer
    except (ImportError, OSError):  # OSError: torch DLL blocked, e.g. by Windows Smart App Control
        return None
    return SentenceTransformer(MODEL)


def _model():
    """The model, loaded once per process (about 20 s on a laptop CPU). The lock makes requests that
    arrive while it is loading wait for that one load instead of starting their own."""
    with _lock:
        return _load()


def warm_up() -> None:
    """Start loading the model in the background, so the first save or ranking does not wait for it."""
    threading.Thread(target=_model, daemon=True, name="embed-warm-up").start()


def embed(texts: list[str]) -> np.ndarray | None:
    """Unit-length vectors, one row per text, or None when the model is not available."""
    m = _model()
    if m is None or not texts:
        return None
    return m.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)


def opportunity_text(o) -> str:
    return " ".join([o.title, o.summary, " ".join(o.tags), " ".join(o.requirements[:2])]).strip()


def profile_text(items) -> str:
    """What the company does, from usable items; confirmed items are repeated so they weigh more."""
    parts = []
    for i in items:
        if i.field in PROFILE_FIELDS and i.value and i.status in ("fact", "inferred", "user_confirmed"):
            parts += [i.value] * (2 if i.status == "user_confirmed" else 1)
    return ". ".join(parts)


def similarities(profile_items, opportunities) -> dict[str, float] | None:
    """Cosine similarity between the company profile and every opportunity that has a stored vector."""
    with_vec = [o for o in opportunities if o.embedding]
    q = embed([profile_text(profile_items)])
    if q is None or not with_vec:
        return None
    mat = np.array([o.embedding for o in with_vec], dtype=np.float32)
    sims = mat @ q[0]
    return {o.id: float(s) for o, s in zip(with_vec, sims)}


def embed_opportunities() -> int:
    from core.store import load_opportunities, save_opportunities
    opps = load_opportunities()
    vecs = embed([opportunity_text(o) for o in opps])
    if vecs is None:
        print("sentence-transformers is not installed: pip install sentence-transformers")
        return 0
    for o, v in zip(opps, vecs):
        o.embedding = [round(float(x), 5) for x in v]
    save_opportunities(opps)
    return len(opps)


if __name__ == "__main__":
    v = embed(["Underwater sensors for detecting divers", "Undervattenssensorer som upptäcker dykare",
               "A pasta recipe with tomatoes"])
    if v is not None:
        same, other = float(v[0] @ v[1]), float(v[0] @ v[2])
        assert same > other + 0.2, (same, other)  # Swedish and English say the same thing
        print(f"ok: same meaning {same:.2f}, unrelated {other:.2f}")
    print("embedded", embed_opportunities(), "opportunities")
