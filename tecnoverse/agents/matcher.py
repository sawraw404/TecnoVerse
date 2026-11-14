"""Matcher agent: rank every opportunity for one company and store the result.

Two steps, as in the plan (retrieve, then re-rank):
  1. agents/scoring.py scores every opportunity (deterministic, keyword topic fit, priorities,
     region, evidence, feedback). Re-ranking after an edit or a thumbs up/down is instant.
  2. A relevance judgement re-ranks: final = (1 - RERANK_WEIGHT) * score + RERANK_WEIGHT * judgement.
     Judgements and the written "why it fits / what is uncertain" live in data/explanations.json.
     Until a live LLM writes them they were written offline in a Claude Code session and are
     labelled SIMULATED. Pairs without a judgement get 0: judged not relevant.

Run: cd tecnoverse && python -m agents.matcher --all
"""
import json
from datetime import datetime, timezone

from pydantic import BaseModel

from agents.scoring import rank_opportunities
from core.schemas import Feedback
from core.store import (DATA, load_companies, load_feedback, load_matches, load_opportunities,
                        load_profile, save_feedback, save_matches)

RERANK_WEIGHT = 0.5  # how much the relevance judgement counts against the keyword score


class Explanation(BaseModel):
    why: str                 # why it fits this company, citing the profile
    uncertain: str           # what is uncertain or must be checked
    score: float = 0.0       # relevance judgement 0..1, used for re-ranking
    written_by: str = "Claude Code, offline (SIMULATED)"


def load_explanations() -> dict[tuple[str, str], Explanation]:
    path = DATA / "explanations.json"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {tuple(k.split("|")): Explanation(**v) for k, v in raw.items()}


def match_company(company_id: str):
    """Re-rank all opportunities for one company. Returns the stored matches, best first."""
    matches = rank(load_profile(company_id), load_matches(company_id))
    save_matches(company_id, matches)
    return matches


def rank(profile, previous=()):
    """The ranking for one profile, without saving (also used by eval/quality.py)."""
    company_id = profile.company.id
    scored = rank_opportunities(profile.company, profile.items, load_opportunities(),
                                load_feedback(company_id), list(previous))
    judged = load_explanations()
    for s in scored:
        m = s.match
        m.llm_score = judged[(company_id, m.opportunity_id)].score if (company_id, m.opportunity_id) in judged else 0.0
        # feedback is added after blending so a thumbs up/down keeps its full weight
        base = m.final_score - m.feedback_adj
        m.final_score = round((1 - RERANK_WEIGHT) * base + RERANK_WEIGHT * m.llm_score + m.feedback_adj, 4)
    matches = sorted((s.match for s in scored), key=lambda m: -m.final_score)
    for n, m in enumerate(matches, 1):
        m.rank = n
    return matches


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
