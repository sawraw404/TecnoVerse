"""Quality check: profile accuracy, relevance and traceability, as the brief asks. No network, no LLM.

Run: cd tecnoverse && python -m eval.quality     -> prints the numbers and writes eval/quality_report.md
Needs the local page text (data/cache/*/pages.json, gitignored) to re-verify quotes.

The hand spot-check of sampled facts lives in eval/spotcheck.json (item id -> verdict); `--sample`
prints the seeded sample to review.
"""
import json
import random
import re
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

from agents.mapper import load_connections, live
from agents.matcher import load_explanations, rank
from agents.profiler import _norm, _site, find_contact
from core.store import load_companies, load_opportunities, load_profile

HERE = Path(__file__).parent
SHOWN = lambda i: i.value and i.status not in ("missing", "user_removed")
FUNDING_WORDS = re.compile(r"\b(eligible|eligibility for you|you qualify|qualifies)\b", re.I)


def traceability(profiles, opps):
    items = [(p, i) for p in profiles.values() for i in p.items if SHOWN(i)]
    pages = {(p.company.id, pg.id): pg for p in profiles.values() for pg in p.pages}
    unsourced = [f"{p.company.id}/{i.field}: {i.value[:60]}" for p, i in items
                 if not (pg := pages.get((p.company.id, i.source_page_id))) or not pg.url or not pg.retrieved_at]
    undated = [f"{o.type}: {o.title[:60]}" for o in opps.values()
               if o.type != "testbed" and not (o.deadline or o.start_date or o.published_at)]
    no_link = [o.title for o in opps.values() if not o.url.startswith("http")]
    expl = load_explanations()
    dangling = [f"{c}|{o}" for c, o in expl if c not in profiles or o not in opps]
    dated = sum(1 for o in opps.values() if o.type != "testbed" and (o.deadline or o.start_date or o.published_at))
    return {"items": len(items), "unsourced": unsourced, "opps": len(opps), "undated": undated, "dated": dated,
            "no_link": no_link, "explanations": len(expl), "dangling": dangling}


def accuracy(profiles):
    facts, failed = 0, []
    for p in profiles.values():
        pages = {pg.id: pg for pg in p.pages}
        for i in p.items:
            if i.status != "fact" or not i.value:
                continue
            facts += 1
            page = pages.get(i.source_page_id)
            if i.field == "contact":
                ok = page and find_contact(i.value, [page])
            else:
                ok = page and page.text and i.quote and _norm(i.quote) in _norm(page.text)
            if not ok:
                failed.append(f"{p.company.id}/{i.field}: {i.value[:60]}")
    off_site = [f"{p.company.id}: {i.value}" for p in profiles.values() for i in p.items
                if i.field == "contact" and SHOWN(i) and _site(next((pg.url for pg in p.pages if pg.id == i.source_page_id), ""))
                != _site(p.company.website)]
    missing_contact = [p.company.id for p in profiles.values() if not any(i.field == "contact" and SHOWN(i) for i in p.items)]
    spot = json.loads((HERE / "spotcheck.json").read_text(encoding="utf-8")) if (HERE / "spotcheck.json").exists() else {}
    return {"facts": facts, "quote_failed": failed, "spot": spot, "off_site": off_site, "missing_contact": missing_contact}


def sample(profiles, n=25):
    facts = [(p, i) for p in profiles.values() for i in p.items if i.status == "fact" and i.value]
    return random.Random(14).sample(facts, n)


def relevance(profiles, opps):
    out = {}
    # 1. demo edit: "testing is a priority" moves testbeds up for the sensor company
    p = profiles["embeddedart"].model_copy(deep=True)
    p.company.priority_types = []
    before = rank(p)
    p.company.priority_types = ["testbed"]
    after = rank(p)
    tb = lambda ms: sum(m.rank for m in ms if opps[m.opportunity_id].type == "testbed") / \
        max(1, sum(opps[m.opportunity_id].type == "testbed" for m in ms))
    out["testbed_rank"] = (round(tb(before), 1), round(tb(after), 1))
    # 2. different companies get different rankings: overlap of top 5 judged matches
    tops = {cid: {m.opportunity_id for m in [m for m in rank(prof) if m.llm_score > 0][:5]}
            for cid, prof in profiles.items()}
    pairs = [(a, b) for a, b in combinations(tops, 2) if tops[a] and tops[b]]
    out["top5_overlap"] = round(sum(len(tops[a] & tops[b]) / len(tops[a] | tops[b]) for a, b in pairs)
                                / max(1, len(pairs)), 2)
    out["no_judged_match"] = sorted(c for c, t in tops.items() if not t)
    # 3. wording: funding is never "eligible"
    texts = [e.why + " " + e.uncertain for e in load_explanations().values()] + \
            [j.why + " " + j.uncertain for j in load_connections()]
    out["funding_wording"] = [t[:80] for t in texts if FUNDING_WORDS.search(t)]
    out["connections_live"] = (len(live(profiles)), len(load_connections()))
    return out


def report(t, a, r) -> str:
    spot = a["spot"]
    ok = sum(v["ok"] for v in spot.values())
    lines = [
        f"# Quality check\n\nRun {datetime.now():%Y-%m-%d %H:%M} on {len(load_companies())} companies, "
        f"{t['opps']} opportunities. Automated checks: `python -m eval.quality`. "
        "No network or LLM is used.\n",
        "## Traceability",
        f"- Profile items shown with a source page, link and retrieval date: "
        f"**{t['items'] - len(t['unsourced'])}/{t['items']}**",
        f"- Opportunities with a link: **{t['opps'] - len(t['no_link'])}/{t['opps']}**; funding, events and trends with a "
        f"deadline, start or published date: **{t['dated']}/{t['dated'] + len(t['undated'])}** "
        f"(testbeds are standing offers without a date)",
        f"- Match explanations that point to an existing company and opportunity: "
        f"**{t['explanations'] - len(t['dangling'])}/{t['explanations']}**",
        "\n## Profile accuracy",
        f"- Facts whose quote is found again in the stored page text (contacts: the address or number): "
        f"**{a['facts'] - len(a['quote_failed'])}/{a['facts']}**",
        f"- Hand spot-check of {len(spot)} randomly sampled facts (seed 14), value compared with its quote and "
        f"page: **{ok}/{len(spot)} correct**. Reviewed by Claude Code, not by a person.",
    ]
    lines += [f"  - {k}: {v['note']}" for k, v in spot.items() if not v["ok"]]
    lines += [
        f"- Contacts taken from the company's own site (rule: its published contact route, nothing from third "
        f"parties): **{len(a['off_site'])} from another site**",
        f"- Companies with no contact route: **{len(a['missing_contact'])}** {', '.join(a['missing_contact'])}",
    ]
    lines += [
        "\n## Relevance",
        f"- Demo edit, EmbeddedArt ticks \"testing is a priority\": average testbed rank "
        f"**{r['testbed_rank'][0]} → {r['testbed_rank'][1]}**",
        f"- Different companies get different rankings: average overlap of two companies' top-5 judged matches "
        f"is **{r['top5_overlap']:.0%}**",
        f"- Companies with no judged match (dashboard shows only keyword overlap): "
        f"**{len(r['no_judged_match'])}** {', '.join(r['no_judged_match'])}",
        f"- Explanations or connections that say \"eligible\" or \"you qualify\": **{len(r['funding_wording'])}**",
        f"- Judged connections still backed by public items: **{r['connections_live'][0]}/{r['connections_live'][1]}**",
        "\nRelevance judgements were written offline by Claude Code, so the ranking numbers check "
        "that the system behaves as designed, not that a company would agree. That needs member feedback "
        "(the thumbs on the dashboard).",
    ]
    fails = [("Items without a source", t["unsourced"]), ("Undated funding, events or trends", t["undated"]),
             ("Facts whose quote was not found", a["quote_failed"]), ("Dangling explanations", t["dangling"]),
             ("Contacts from another site", a["off_site"])]
    for title, xs in fails:
        if xs:
            lines += [f"\n### {title} ({len(xs)})"] + [f"- {x}" for x in xs[:30]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    profiles = {c.id: load_profile(c.id) for c in load_companies()}
    opps = {o.id: o for o in load_opportunities()}
    if "--sample" in sys.argv:
        for p, i in sample(profiles):
            pg = next((x for x in p.pages if x.id == i.source_page_id), None)
            print(f"{i.id} | {p.company.id} [{i.field}] {i.value}\n   quote: {i.quote}\n   page: {pg.url if pg else None}")
        sys.exit()
    text = report(traceability(profiles, opps), accuracy(profiles), relevance(profiles, opps))
    (HERE / "quality_report.md").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
