"""Matcher agent: rank every opportunity for one company and store the result.

Three steps (retrieve, score, re-rank):
  1. Semantic similarity: a local embedding model (core/embed.py) compares the company profile with
     every opportunity; stored as Match.vector_score. Skipped if the model is not installed.
  2. agents/scoring.py scores every opportunity (deterministic, keyword topic fit, priorities,
     region, evidence, feedback). base = (1 - SEMANTIC_WEIGHT) * score + SEMANTIC_WEIGHT * similarity.
  3. A relevance judgement re-ranks: final = (1 - RERANK_WEIGHT) * score + RERANK_WEIGHT * judgement.
     Judgements and the written "why it fits / what is uncertain" live in data/explanations.json.
     Until a live LLM writes them they were written offline in a Claude Code session (`written_by`). Pairs without a judgement get 0: judged not relevant.

Run: cd tecnoverse && python -m agents.matcher --all
"""
import json
from datetime import datetime, timezone

from pydantic import BaseModel

from agents.scoring import rank_opportunities
from core.embed import similarities
from core.schemas import Feedback
from core.store import (DATA, load_companies, load_feedback, load_matches, load_opportunities,
                        load_profile, save_feedback, save_matches)

RERANK_WEIGHT = 0.5    # how much the relevance judgement counts against the score
SEMANTIC_WEIGHT = 0.3  # how much embedding similarity counts inside the score


class Explanation(BaseModel):
    why: str                 # why it fits this company, citing the profile
    uncertain: str           # what is uncertain or must be checked
    score: float = 0.0       # relevance judgement 0..1, used for re-ranking
    written_by: str = "Claude Code, offline"


def load_explanations() -> dict[tuple[str, str], Explanation]:
    """Judgements for funding, events and testbeds (data/explanations.json) and the trend monitor's
    per-company notes (data/trend_notes.json, written live by agents/trends.py)."""
    raw = {}
    for name in ("explanations.json", "trend_notes.json"):
        path = DATA / name
        if path.exists():
            raw.update(json.loads(path.read_text(encoding="utf-8")))
    return {tuple(k.split("|")): Explanation(**v) for k, v in raw.items()}


def match_company(company_id: str):
    """Re-rank all opportunities for one company. Returns the stored matches, best first."""
    matches = rank(load_profile(company_id), load_matches(company_id))
    save_matches(company_id, matches)
    return matches


def rank(profile, previous=()):
    """The ranking for one profile, without saving (also used by eval/quality.py)."""
    company_id = profile.company.id
    opportunities = load_opportunities()
    scored = rank_opportunities(profile.company, profile.items, opportunities,
                                load_feedback(company_id), list(previous))
    judged = load_explanations()
    sims = similarities(profile.items, opportunities)  # None without the local model: keyword score only
    for s in scored:
        m = s.match
        m.llm_score = judged[(company_id, m.opportunity_id)].score if (company_id, m.opportunity_id) in judged else 0.0
        # feedback is added after blending so a thumbs up/down keeps its full weight
        base = m.final_score - m.feedback_adj
        if sims and m.opportunity_id in sims:
            m.vector_score = round(sims[m.opportunity_id], 4)
            base = (1 - SEMANTIC_WEIGHT) * base + SEMANTIC_WEIGHT * max(0.0, m.vector_score)
        m.final_score = round((1 - RERANK_WEIGHT) * base + RERANK_WEIGHT * m.llm_score + m.feedback_adj, 4)
    matches = sorted((s.match for s in scored), key=lambda m: -m.final_score)
    for n, m in enumerate(matches, 1):
        m.rank = n
    return matches


def feedback_state(company_id: str) -> tuple[set[str], dict[str, str]]:
    """(saved opportunity ids, latest thumbs vote per opportunity) from the company's feedback."""
    saved: dict[str, bool] = {}
    vote: dict[str, str] = {}
    for f in sorted(load_feedback(company_id), key=lambda f: f.created_at):
        if f.kind in ("saved", "unsaved"):
            saved[f.opportunity_id] = f.kind == "saved"
        elif f.kind in ("up", "down"):
            vote[f.opportunity_id] = f.kind
    return {k for k, v in saved.items() if v}, vote


def give_feedback(company_id: str, opportunity_id: str, kind: str, user_id: str):
    """Record thumbs up/down (or save) and re-rank. Feedback stays in the company's own folder."""
    fb = load_feedback(company_id)
    fb.append(Feedback(id=f"{company_id}-{len(fb) + 1}", company_id=company_id, opportunity_id=opportunity_id,
                       user_id=user_id, kind=kind, created_at=datetime.now(timezone.utc)))
    save_feedback(company_id, fb)
    return match_company(company_id)


if __name__ == "__main__":
    import sys
    if "--all" in sys.argv:
        for c in load_companies():
            top = match_company(c.id)[:3]
            print(c.id, [round(m.final_score, 2) for m in top])
    else:
        print("usage: python -m agents.matcher --all")
