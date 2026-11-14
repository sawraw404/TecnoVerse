"""Scoring matrix tests. No network, no LLM. Run from the repo root: pytest"""
from datetime import date, datetime, timezone

import pytest

from agents.scoring import (
    COMPANY_WEIGHTS, OPP_WEIGHTS, REGION_SCORES, rank_connections, rank_opportunities, score_opportunity,
)
from agents.scoring_adapters import adapt_opportunity, adapt_profile, locate, tokens
from agents.scoring_samples import CLOUD, ITEMS, MARINE, OPPORTUNITIES, SENSOR, item, opp
from core.schemas import Feedback

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def ranked_ids(company, items=None, opportunities=OPPORTUNITIES, **kw):
    return [s.match.opportunity_id
            for s in rank_opportunities(company, items or ITEMS[company.id], opportunities, **kw)]


def breakdown(company, items, opportunity):
    return score_opportunity(adapt_profile(company, items), adapt_opportunity(opportunity)).breakdown


def vote(kind, opp_id, company=SENSOR, minute=0):
    return Feedback(id=f"fb-{kind}-{minute}", company_id=company.id, opportunity_id=opp_id,
                    user_id=f"rep-{company.id}", kind=kind, created_at=NOW.replace(minute=minute))


# --- Weights ------------------------------------------------------------------------------------

def test_weights_sum_to_one():
    assert sum(OPP_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(COMPANY_WEIGHTS.values()) == pytest.approx(1.0)


# --- Personalisation ----------------------------------------------------------------------------

def test_different_companies_get_different_rankings():
    sensor, cloud, marine = ranked_ids(SENSOR), ranked_ids(CLOUD), ranked_ids(MARINE)
    assert sensor[0] in {"t-sensor-lab", "f-maintenance-call"}
    assert cloud[0] == "e-cloud-day"
    assert marine[0] == "f-energy-call"


def test_scores_are_between_zero_and_one():
    for company in (SENSOR, CLOUD, MARINE):
        for s in rank_opportunities(company, ITEMS[company.id], OPPORTUNITIES):
            for key in ("topic", "priority", "region", "evidence", "final"):
                assert 0.0 <= s.breakdown[key] <= 1.0, (company.id, key)


def test_ranks_are_consecutive_and_sorted():
    result = rank_opportunities(CLOUD, ITEMS[CLOUD.id], OPPORTUNITIES)
    assert [s.match.rank for s in result] == list(range(1, len(OPPORTUNITIES) + 1))
    finals = [s.breakdown["final"] for s in result]
    for higher, lower in zip(finals, finals[1:]):
        assert higher >= lower - 0.02  # only ties may swap order


# --- Stated priority (demo step 2: "testing is a priority") -------------------------------------

def test_priority_moves_testbeds_up_and_records_prev_rank():
    company = MARINE  # the sensor lab starts near the bottom for MarineCo
    before = rank_opportunities(company, ITEMS[company.id], OPPORTUNITIES)
    prioritised = company.model_copy(update={"priority_types": ["testbed"], "profile_version": 2})
    after = rank_opportunities(prioritised, ITEMS[company.id], OPPORTUNITIES,
                               previous=[s.match for s in before])
    rank = lambda res: next(s.match for s in res if s.match.opportunity_id == "t-sensor-lab")
    assert rank(after).rank < rank(before).rank
    assert rank(after).prev_rank == rank(before).rank
    assert rank(after).priority_boost == pytest.approx(OPP_WEIGHTS["priority"])
    assert rank(after).profile_version == 2
    assert any("priority" in r.text for r in rank(after).reasons)


def test_inferred_interest_is_never_a_priority():
    items = ITEMS[SENSOR.id] + [item(SENSOR.id, "possible_interest", "Testbeds", status="inferred")]
    assert breakdown(SENSOR, items, OPPORTUNITIES[0])["priority"] == 0.0


# --- Status weights -----------------------------------------------------------------------------

@pytest.mark.parametrize("weaker,stronger", [("inferred", "fact"), ("fact", "user_confirmed")])
def test_stronger_status_scores_higher(weaker, stronger):
    lab = OPPORTUNITIES[0]
    weak = breakdown(SENSOR, [item(SENSOR.id, "offering", "Vibration sensors", status=weaker)], lab)
    strong = breakdown(SENSOR, [item(SENSOR.id, "offering", "Vibration sensors", status=stronger)], lab)
    assert strong["topic"] > weak["topic"]


def test_removed_and_missing_items_are_ignored():
    items = [item(SENSOR.id, "offering", "Vibration sensors", status="user_removed"),
             item(SENSOR.id, "technology", "", status="missing")]
    assert adapt_profile(SENSOR, items).topics == []
    assert breakdown(SENSOR, items, OPPORTUNITIES[0])["topic"] == 0.0


def test_inferred_only_match_is_flagged():
    items = [item(SENSOR.id, "offering", "Vibration sensors", status="inferred")]
    s = rank_opportunities(SENSOR, items, [OPPORTUNITIES[0]])[0]
    assert s.breakdown["evidence"] == 0.0
    assert any("inferred" in u for u in s.match.uncertainties)


# --- Region (Blekinge only) ---------------------------------------------------------------------

@pytest.mark.parametrize("text,status,municipality", [
    ("Karlskrona", "municipality", "Karlskrona"),
    ("Sölvesborg", "municipality", "Sölvesborg"),
    ("solvesborg", "municipality", "Sölvesborg"),
    ("Region Blekinge", "blekinge", None),
    ("Online webinar", "online", None),
    ("Stockholm", "outside", None),
    ("", "unknown", None),
])
def test_locate(text, status, municipality):
    r = locate(text)
    assert (r.status, r.municipality) == (status, municipality)


@pytest.mark.parametrize("location,fmt,expected", [
    ("Karlskrona", "in_person", "same_municipality"),
    ("Ronneby", "in_person", "blekinge"),
    (None, "online", "online"),
    ("Stockholm", "hybrid", "online"),      # hybrid: the online option beats travelling
    ("Stockholm", "in_person", "outside"),
    (None, None, "unknown"),
])
def test_region_scores_for_sensor_company_in_karlskrona(location, fmt, expected):
    o = opp("x", "event", "Sensor meetup", "sensors", location=location, format=fmt)
    assert breakdown(SENSOR, ITEMS[SENSOR.id], o)["region"] == REGION_SCORES[expected]


def test_funding_without_location_is_national_not_uncertain():
    s = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [OPPORTUNITIES[3]])[0]
    assert s.breakdown["region"] == REGION_SCORES["national"]
    assert not any("Location unknown" in u for u in s.match.uncertainties)


def test_company_market_geography_is_unknown_not_outside():
    assert adapt_profile(MARINE, ITEMS[MARINE.id]).region.status == "unknown"


# --- Feedback -----------------------------------------------------------------------------------

def test_feedback_moves_scores_and_latest_vote_wins():
    lab = OPPORTUNITIES[0]
    base = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab])[0].breakdown["final"]
    up = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab], feedback=[vote("up", lab.id)])[0]
    changed = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab],
                                 feedback=[vote("up", lab.id, minute=1), vote("down", lab.id, minute=2)])[0]
    assert up.breakdown["final"] == pytest.approx(min(1.0, base + 0.10))
    assert changed.breakdown["final"] == pytest.approx(base - 0.20)
    assert changed.match.feedback_adj == -0.20


def test_down_vote_drops_rank():
    before = ranked_ids(SENSOR)
    top = before[0]
    after = ranked_ids(SENSOR, feedback=[vote("down", top)])
    assert after.index(top) > before.index(top)


def test_other_companies_feedback_is_ignored():
    lab = OPPORTUNITIES[0]
    base = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab])[0].breakdown["final"]
    other = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab], feedback=[vote("down", lab.id, company=CLOUD)])
    assert other[0].breakdown["final"] == base


# --- Ties ---------------------------------------------------------------------------------------

def test_opportunity_tie_goes_to_sooner_deadline():
    later = opp("later", "funding", "Sensor call A", "sensor", deadline=date(2027, 6, 1))
    sooner = opp("sooner", "funding", "Sensor call B", "sensor", deadline=date(2027, 1, 1))
    assert ranked_ids(SENSOR, opportunities=[later, sooner]) == ["sooner", "later"]


def test_connection_tie_goes_to_members():
    member = CLOUD.model_copy(update={"id": "z-member", "name": "Z member"})
    non_member = CLOUD.model_copy(update={"id": "a-nonmember", "name": "A non-member", "is_member": False})
    items = lambda c: [item(c.id, "offering", "Vibration sensors"), item(c.id, "geography", "Karlskrona")]
    result = rank_connections([(SENSOR, items(SENSOR)), (member, items(member)), (non_member, items(non_member))])
    first_two = [{s.connection.company_a, s.connection.company_b} for s in result[:2]]
    assert first_two[0] == {SENSOR.id, member.id}  # same score, both members
    assert non_member.id in first_two[1]


# --- Wording and labels -------------------------------------------------------------------------

def test_funding_is_possible_match_never_eligible():
    for s in rank_opportunities(SENSOR, ITEMS[SENSOR.id], OPPORTUNITIES):
        text = " ".join([s.match.next_step, *s.match.uncertainties, *(r.text for r in s.match.reasons)]).lower()
        assert s.match.match_label == "possible_match"
        assert "eligible" not in text and "you qualify" not in text
        if s.match.opportunity_id.startswith("f-"):
            assert any("possible match" in u.lower() for u in s.match.uncertainties)


def test_simulated_opportunities_are_labelled():
    for s in rank_opportunities(SENSOR, ITEMS[SENSOR.id], OPPORTUNITIES):
        assert "SIMULATED data" in s.match.uncertainties


def test_topic_reasons_point_to_profile_items():
    s = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [OPPORTUNITIES[0]])[0]
    item_ids = {i.id for i in ITEMS[SENSOR.id]}
    topic_reasons = [r for r in s.match.reasons if r.text.startswith("Matches")]
    assert topic_reasons and all(r.profile_item_id in item_ids for r in topic_reasons)


def test_next_step_has_date_and_contact():
    lab_with_date = OPPORTUNITIES[0].model_copy(update={"deadline": date(2027, 1, 31)})
    step = rank_opportunities(SENSOR, ITEMS[SENSOR.id], [lab_with_date])[0].match.next_step
    assert "2027-01-31" in step and "lab@example.com" in step


# --- Connections (staff view) -------------------------------------------------------------------

def test_connections_use_public_items_only():
    private = [item(SENSOR.id, "offering", "Cloud hosting and data storage", visibility="private")]
    result = rank_connections([(SENSOR, private), (CLOUD, ITEMS[CLOUD.id])])
    assert result == []  # the only overlap is private, so no suggestion


def test_connection_basis_and_label():
    result = rank_connections([(c, ITEMS[c.id]) for c in (SENSOR, CLOUD, MARINE)])
    assert result, "SensorCo and CloudCo share 'sensor'"
    for s in result:
        c = s.connection
        assert c.company_a < c.company_b
        assert c.basis and c.uses_public_data_only
        assert c.label.startswith("Suggestion")
        assert c.type == "shared_theme"


def test_location_alone_is_no_connection():
    a = [item(SENSOR.id, "offering", "Vibration sensors"), item(SENSOR.id, "geography", "Karlskrona")]
    b = [item(CLOUD.id, "offering", "Cloud hosting"), item(CLOUD.id, "geography", "Karlskrona")]
    assert rank_connections([(SENSOR, a), (CLOUD, b)]) == []


# --- Adapter ------------------------------------------------------------------------------------

def test_tokens_fold_plurals_and_drop_stopwords():
    assert tokens("Sensors for the industry") == {"sensor", "industry"}


def test_adapter_accepts_profile_object():
    from types import SimpleNamespace
    from agents.scoring_adapters import adapt_profile_obj
    p = adapt_profile_obj(SimpleNamespace(company=SENSOR, items=ITEMS[SENSOR.id]))
    assert p.region.municipality == "Karlskrona" and p.topics
