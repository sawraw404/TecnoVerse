"""Scoring matrix: ranks opportunities for a company (Match) and suggests company pairs (Connection).

Matrix 1, company -> opportunity          Matrix 2, company <-> company (public items only)
  topic fit        0.50                      topic fit        0.60
  stated priority  0.20                      Blekinge region  0.30
  Blekinge region  0.20                      evidence quality 0.10
  evidence quality 0.10                      ties: members first
  + feedback (+0.10 up / -0.20 down)
  ties: sooner deadline first

Every criterion is 0..1. Ties are scores within TIE_MARGIN of the top of their group.
Inputs come from agents/scoring_adapters.py, so a new profiler output only changes the adapter.

The README schema is not changed. Match/Connection are built from the existing fields, and the
per-criterion breakdown is returned next to them (ScoredMatch / ScoredConnection) until the team
agrees where to store it. Field mapping for Match:
  vector_score   = topic fit (keyword overlap now, embedding cosine later)
  llm_score      = 0.0 (no LLM rerank yet)
  priority_boost = weighted priority contribution
  feedback_adj   = feedback adjustment
"""
from dataclasses import dataclass
from datetime import date

from agents.scoring_adapters import (
    Region, ScoringOpp, ScoringProfile, Topic, adapt_opportunity, adapt_profile,
)
from core.schemas import (
    Basis, Company, Connection, Feedback, Match, Opportunity, ProfileItem, Reason,
)

# --- Tunable weights ----------------------------------------------------------------------------

OPP_WEIGHTS = {"topic": 0.50, "priority": 0.20, "region": 0.20, "evidence": 0.10}
COMPANY_WEIGHTS = {"topic": 0.60, "region": 0.30, "evidence": 0.10}
FEEDBACK_ADJ = {"up": 0.10, "down": -0.20}
REGION_SCORES = {
    "same_municipality": 1.0,
    "online": 0.8,
    "blekinge": 0.6,       # both in Blekinge, different or unstated municipality
    "unknown": 0.5,        # neutral, flagged as uncertain
    "national": 0.5,       # funding call with no location: location doesn't apply
    "outside": 0.2,
}
TIE_MARGIN = 0.02
MAX_REASONS = 3

STATUS_LABEL = {
    "user_confirmed": "confirmed",
    "fact": "stated on the company's site",
    "inferred": "inferred, not confirmed",
}
DATE_LABEL = {"funding": "Deadline", "event": "Starts", "testbed": "Key date", "news": "Published"}

# --- Results ------------------------------------------------------------------------------------


@dataclass
class ScoredMatch:
    match: Match
    breakdown: dict[str, float]  # topic, priority, region, evidence (0..1), feedback, final
    title: str


@dataclass
class ScoredConnection:
    connection: Connection
    breakdown: dict[str, float]  # topic, region, evidence (0..1), final
    names: tuple[str, str]
    uncertainties: list[str]


# --- Building blocks ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Hit:
    topic: Topic
    coverage: float           # share of the topic's keywords found on the other side
    shared: frozenset[str]

    @property
    def strength(self) -> float:
        return self.topic.weight * self.coverage


def _hits(topics: list[Topic], other: frozenset[str]) -> list[_Hit]:
    out = []
    for t in topics:
        shared = t.tokens & other
        if shared:
            out.append(_Hit(t, len(shared) / len(t.tokens), shared))
    return sorted(out, key=lambda h: -h.strength)


def _topic_fit(hits: list[_Hit]) -> float:
    """Noisy-OR: one strong match already scores high, more matches add with diminishing returns."""
    miss = 1.0
    for h in hits:
        miss *= 1 - h.strength
    return 1 - miss


def _evidence(hits: list[_Hit]) -> float:
    """Share of the match strength that rests on facts or user-confirmed items."""
    total = sum(h.strength for h in hits)
    return sum(h.strength for h in hits if h.topic.is_evidence) / total if total else 0.0


def _place(a: Region, b: Region) -> tuple[float, str, bool]:
    """(score, explanation, uncertain) for two places, Blekinge scope."""
    if b.status == "national":
        return REGION_SCORES["national"], "National call: location does not apply", False
    if b.status == "online":
        return REGION_SCORES["online"], "Can be joined online", False
    if b.status == "outside" or a.status == "outside":
        return REGION_SCORES["outside"], "Outside Blekinge", False
    if a.status == "unknown" or b.status == "unknown":
        return REGION_SCORES["unknown"], "Location unknown", True
    if a.municipality and a.municipality == b.municipality:
        return REGION_SCORES["same_municipality"], f"Both in {a.municipality}", False
    if a.municipality and b.municipality:
        return REGION_SCORES["blekinge"], f"Both in Blekinge ({a.municipality} and {b.municipality})", False
    return REGION_SCORES["blekinge"], "Elsewhere in Blekinge", False


def _region_for_opp(company: Region, opp: ScoringOpp) -> tuple[float, str, bool]:
    score, text, uncertain = _place(company, opp.region)
    if opp.online_option and REGION_SCORES["online"] > score:
        return REGION_SCORES["online"], "Can be joined online", False
    return score, text, uncertain


def _latest_vote(feedback: list[Feedback], company_id: str, opp_id: str) -> str | None:
    votes = [f for f in feedback
             if f.company_id == company_id and f.opportunity_id == opp_id and f.kind in FEEDBACK_ADJ]
    return max(votes, key=lambda f: f.created_at).kind if votes else None


def _rank(items: list, score, tiebreak) -> list:
    """Sort by score; items within TIE_MARGIN of their group's top are ordered by `tiebreak`."""
    ordered = sorted(items, key=lambda x: -score(x))
    out, group = [], []
    for x in ordered:
        if group and score(group[0]) - score(x) > TIE_MARGIN:
            out += sorted(group, key=tiebreak)
            group = []
        group.append(x)
    return out + sorted(group, key=tiebreak)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- Matrix 1: company -> opportunity -----------------------------------------------------------


@dataclass
class _OppScore:
    opp: ScoringOpp
    breakdown: dict[str, float]
    reasons: list[Reason]
    uncertainties: list[str]
    next_step: str


def _next_step(o: ScoringOpp) -> str:
    parts = []
    if o.deadline:
        parts.append(f"{DATE_LABEL.get(o.type, 'Date')}: {o.deadline.isoformat()}.")
    if o.type == "funding":
        parts.append("Check the requirements at the source before applying.")
    parts.append(f"Contact: {o.contact}." if o.contact else f"Details: {o.url}")
    return " ".join(parts)


def score_opportunity(p: ScoringProfile, o: ScoringOpp, feedback: list[Feedback] = ()) -> _OppScore:
    hits = _hits(p.topics, o.tokens)
    topic, evidence = _topic_fit(hits), _evidence(hits)
    priority = 1.0 if o.type in p.priority_types else 0.0
    region, region_text, region_uncertain = _region_for_opp(p.region, o)
    vote = _latest_vote(list(feedback), p.company_id, o.opportunity_id)
    fb = FEEDBACK_ADJ.get(vote, 0.0)

    w = OPP_WEIGHTS
    final = _clamp(w["topic"] * topic + w["priority"] * priority + w["region"] * region
                   + w["evidence"] * evidence + fb)

    reasons = [
        Reason(text=f'Matches {h.topic.field.replace("_", " ")} "{h.topic.text}" '
                    f'({STATUS_LABEL[h.topic.status]}), shared keywords: {", ".join(sorted(h.shared))}',
               profile_item_id=h.topic.item_id)
        for h in hits[:MAX_REASONS]
    ]
    if priority:
        reasons.append(Reason(text=f"You marked {o.type} opportunities as a priority"))
    if region >= REGION_SCORES["blekinge"]:
        from_profile = region_text.startswith(("Both in", "Elsewhere"))  # online needs no profile item
        reasons.append(Reason(text=region_text, profile_item_id=p.region.item_id if from_profile else None))
    if vote:
        reasons.append(Reason(text="You rated this " + ("up" if vote == "up" else "down")))

    uncertainties = []
    if not hits:
        uncertainties.append("No overlap with the company's profile topics")
    elif evidence == 0:
        uncertainties.append("Based only on inferred interests, not confirmed by the company")
    if region_uncertain:
        uncertainties.append(region_text)
    elif region < REGION_SCORES["unknown"]:
        uncertainties.append(region_text)
    if o.type == "funding":
        uncertainties.append("Possible match only: eligibility has not been assessed")
    if o.simulated:
        uncertainties.append("SIMULATED data")

    breakdown = {"topic": topic, "priority": priority, "region": region, "evidence": evidence,
                 "feedback": fb, "final": final}
    return _OppScore(o, {k: round(v, 4) for k, v in breakdown.items()}, reasons, uncertainties, _next_step(o))


def rank_for_profile(p: ScoringProfile, opps: list[ScoringOpp], feedback: list[Feedback] = (),
                     previous: list[Match] = ()) -> list[ScoredMatch]:
    """Adapter-level entry point: rank already adapted opportunities for one profile."""
    scored = [score_opportunity(p, o, feedback) for o in opps]
    ranked = _rank(scored, score=lambda s: s.breakdown["final"],
                   tiebreak=lambda s: (s.opp.deadline or date.max, s.opp.title.lower()))
    prev = {m.opportunity_id: m.rank for m in previous if m.company_id == p.company_id}
    out = []
    for rank, s in enumerate(ranked, 1):
        b = s.breakdown
        match = Match(
            company_id=p.company_id, opportunity_id=s.opp.opportunity_id, profile_version=p.profile_version,
            vector_score=b["topic"], llm_score=0.0,
            priority_boost=round(OPP_WEIGHTS["priority"] * b["priority"], 4), feedback_adj=b["feedback"],
            final_score=b["final"], rank=rank, prev_rank=prev.get(s.opp.opportunity_id),
            reasons=s.reasons, uncertainties=s.uncertainties, next_step=s.next_step,
        )
        out.append(ScoredMatch(match, b, s.opp.title))
    return out


def rank_opportunities(company: Company, items: list[ProfileItem], opportunities: list[Opportunity],
                       feedback: list[Feedback] = (), previous: list[Match] = ()) -> list[ScoredMatch]:
    """Schema-level entry point: rank opportunities for one company."""
    return rank_for_profile(adapt_profile(company, items),
                            [adapt_opportunity(o) for o in opportunities], feedback, previous)


# --- Matrix 2: company <-> company --------------------------------------------------------------


def _best_partner(hit: _Hit, others: list[Topic]) -> Topic | None:
    return max(others, key=lambda t: len(t.tokens & hit.shared), default=None)


def score_pair(a: ScoringProfile, b: ScoringProfile) -> ScoredConnection | None:
    """Public items only. Returns None when there is no shared theme: location alone is no basis."""
    if b.company_id < a.company_id:
        a, b = b, a
    a_topics, b_topics = a.public_topics, b.public_topics
    a_tokens = frozenset().union(*(t.tokens for t in a_topics))
    b_tokens = frozenset().union(*(t.tokens for t in b_topics))
    hits_ab, hits_ba = _hits(a_topics, b_tokens), _hits(b_topics, a_tokens)
    if not hits_ab:
        return None

    topic = (_topic_fit(hits_ab) + _topic_fit(hits_ba)) / 2
    evidence = _evidence(hits_ab + hits_ba)
    region, region_text, region_uncertain = _place(a.public_region, b.public_region)

    w = COMPANY_WEIGHTS
    final = _clamp(w["topic"] * topic + w["region"] * region + w["evidence"] * evidence)

    basis, seen = [], set()
    for h in hits_ab:
        partner = _best_partner(h, [t for t in b_topics if t.tokens & h.shared])
        if partner is None or (h.topic.item_id, partner.item_id) in seen:
            continue
        seen.add((h.topic.item_id, partner.item_id))
        basis.append(Basis(
            text=f'{a.name}: "{h.topic.text}" / {b.name}: "{partner.text}" '
                 f'(shared: {", ".join(sorted(h.shared & partner.tokens))})',
            item_a_id=h.topic.item_id, item_b_id=partner.item_id))
        if len(basis) == MAX_REASONS:
            break
    if region >= REGION_SCORES["blekinge"] and a.public_region.item_id and b.public_region.item_id:
        basis.append(Basis(text=region_text, item_a_id=a.public_region.item_id,
                           item_b_id=b.public_region.item_id))

    uncertainties = []
    if evidence == 0:
        uncertainties.append("Based only on inferred items")
    if region_uncertain:
        uncertainties.append(region_text)

    connection = Connection(company_a=a.company_id, company_b=b.company_id, basis=basis,
                            type="shared_theme",  # keyword overlap can only show shared themes
                            score=round(final, 4), uses_public_data_only=True)
    breakdown = {"topic": topic, "region": region, "evidence": evidence, "final": final}
    return ScoredConnection(connection, {k: round(v, 4) for k, v in breakdown.items()},
                            (a.name, b.name), uncertainties)


def rank_profiles(profiles: list[ScoringProfile]) -> list[ScoredConnection]:
    """Adapter-level entry point: every pair with a shared theme, best first. Ties: members first."""
    members = {p.company_id: p.is_member for p in profiles}
    pairs = [s for i, a in enumerate(profiles) for b in profiles[i + 1:] if (s := score_pair(a, b))]
    return _rank(pairs, score=lambda s: s.breakdown["final"],
                 tiebreak=lambda s: (-(members[s.connection.company_a] + members[s.connection.company_b]),
                                     s.names))


def rank_connections(companies: list[tuple[Company, list[ProfileItem]]]) -> list[ScoredConnection]:
    """Schema-level entry point: suggested connections across members, for the staff view."""
    return rank_profiles([adapt_profile(c, items) for c, items in companies])


def connections_for(company_id: str, connections: list[ScoredConnection]) -> list[ScoredConnection]:
    return [c for c in connections if company_id in (c.connection.company_a, c.connection.company_b)]
