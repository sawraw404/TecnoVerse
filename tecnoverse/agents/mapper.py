"""Staff mapper: suggested connections between companies, for the staff view. Public items only.

Two steps, like the matcher:
  1. agents/scoring.py `rank_connections` finds every pair with keyword overlap in public items.
  2. Judged connections in data/connections.json: pairs where the public items show a real shared theme
     or a complementary fit, with the two items that are the basis. Until a live LLM writes them they
     were written offline in a Claude Code session (`written_by`). Pairs whose public items
     already show they work together are left out.

`live()` re-checks every judged pair against the current profiles: if a basis item was removed or made
private since, the connection is dropped, so the staff view never shows private data.

Check: cd tecnoverse && python -m agents.mapper
"""
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from core.schemas import Connection, ProfileItem
from core.store import DATA, load_companies, load_profile


class Judged(BaseModel):
    connection: Connection   # team schema: company_a < company_b, basis item ids, public data only
    theme: str               # short shared theme, groups connections on the staff page
    why: str
    uncertain: str
    written_by: str = "Claude Code, offline"


def load_connections() -> list[Judged]:
    path = DATA / "connections.json"
    return [Judged(**j) for j in json.loads(path.read_text(encoding="utf-8"))] if path.exists() else []


def usable(item: ProfileItem | None) -> bool:
    return item is not None and item.visibility == "public" and item.status not in ("missing", "user_removed")


def live(profiles: dict) -> list[Judged]:
    """Judged connections whose basis items are all still public and present, best first."""
    out = []
    for j in load_connections():
        a, b = profiles.get(j.connection.company_a), profiles.get(j.connection.company_b)
        if not (a and b):
            continue
        items_a, items_b = {i.id: i for i in a.items}, {i.id: i for i in b.items}
        if j.connection.basis and all(usable(items_a.get(x.item_a_id)) and usable(items_b.get(x.item_b_id))
                                      for x in j.connection.basis):
            out.append(j)
    return sorted(out, key=lambda j: -j.connection.score)


# --- Knowledge graph (staff only) -----------------------------------------------------------------
# Nodes: Blue Science Park, the park's focus areas, and every profiled company. Edges:
#   member        park member -> Blue Science Park
#   area          company -> its focus area (data/focus_areas.json); this is the "shared industry" link
#   collaboration stated on a company's own public page (a public item naming the other company)
#   suggestion    judged connection from live(), labelled as a suggestion
# Public items only, every fact and link with its source and date.

PARK = "bsp"


class Fact(BaseModel):
    field: str
    value: str
    url: str | None
    retrieved_at: datetime | None


class Node(BaseModel):
    id: str
    kind: Literal["park", "area", "company"]
    label: str
    area: str | None = None           # focus area key, for colour
    member: bool = False
    website: str | None = None
    facts: list[Fact] = []


class Edge(BaseModel):
    source: str
    target: str
    kind: Literal["member", "area", "collaboration", "suggestion"]
    label: str = ""
    why: str = ""
    uncertain: str = ""
    evidence: list[Fact] = []


class Graph(BaseModel):
    areas: dict[str, str]
    nodes: list[Node]
    edges: list[Edge]


def _fact(p, item: ProfileItem) -> Fact:
    page = next((pg for pg in p.pages if pg.id == item.source_page_id), None)
    return Fact(field=item.field, value=item.value, url=page.url if page else None,
                retrieved_at=page.retrieved_at if page else None)


def _names(company) -> list[str]:
    """How another company's public text may name this one: full name and the part before a dash."""
    base = company.name.split(" (")[0]
    return list({base, base.split(" – ")[0].strip()})


def knowledge_graph(profiles: dict) -> Graph:
    focus = json.loads((DATA / "focus_areas.json").read_text(encoding="utf-8"))
    profiles = {k: p for k, p in profiles.items() if p}
    used = {focus["companies"].get(k, "other") for k in profiles}
    nodes = [Node(id=PARK, kind="park", label="Blue Science Park")]
    nodes += [Node(id=f"area:{a}", kind="area", label=label, area=a) for a, label in focus["areas"].items() if a in used]
    edges: list[Edge] = []
    for cid, p in profiles.items():
        public = [i for i in p.items if usable(i) and i.value]
        area = focus["companies"].get(cid, "other")
        facts = [_fact(p, i) for f, n in (("industry", 1), ("offering", 3), ("innovation", 2))
                 for i in [x for x in public if x.field == f][:n]]
        nodes.append(Node(id=cid, kind="company", label=p.company.name, area=area, member=p.company.is_member,
                          website=p.company.website, facts=facts))
        edges.append(Edge(source=cid, target=f"area:{area}", kind="area", label=focus["areas"][area]))
        if p.company.is_member:
            edges.append(Edge(source=cid, target=PARK, kind="member", label="Blue Science Park member"))

    # stated collaborations: a public item of one company names another company in the graph
    seen = set()
    for cid, p in profiles.items():
        for i in (x for x in p.items if usable(x) and x.value):
            text = f"{i.value} {i.quote or ''}"
            for oid, o in profiles.items():
                pair = tuple(sorted((cid, oid)))
                if oid == cid or pair in seen:
                    continue
                if any(re.search(rf"\b{re.escape(n)}\b", text, re.I) for n in _names(o.company)):
                    seen.add(pair)
                    edges.append(Edge(source=cid, target=oid, kind="collaboration",
                                      label="Stated on a public page", evidence=[_fact(p, i)]))

    for j in live(profiles):
        c = j.connection
        pa, pb = profiles[c.company_a], profiles[c.company_b]
        ia, ib = {i.id: i for i in pa.items}, {i.id: i for i in pb.items}
        edges.append(Edge(source=c.company_a, target=c.company_b, kind="suggestion", label=c.label, why=j.why,
                          uncertain=j.uncertain,
                          evidence=[f for b in c.basis for f in (_fact(pa, ia[b.item_a_id]), _fact(pb, ib[b.item_b_id]))]))
    return Graph(areas={a: focus["areas"][a] for a in focus["areas"] if a in used}, nodes=nodes, edges=edges)


if __name__ == "__main__":
    profiles = {c.id: load_profile(c.id) for c in load_companies()}
    g = knowledge_graph(profiles)
    kinds = {k: sum(e.kind == k for e in g.edges) for k in ("member", "area", "collaboration", "suggestion")}
    assert kinds["member"] == sum(p.company.is_member for p in profiles.values()) and kinds["area"] == len(profiles)
    assert kinds["collaboration"] >= 1 and kinds["suggestion"] == len(live(profiles)), kinds
    ids = {n.id for n in g.nodes}
    assert all(e.source in ids and e.target in ids for e in g.edges)
    judged = load_connections()
    for j in judged:
        c = j.connection
        assert c.company_a < c.company_b and c.uses_public_data_only, c
        assert c.company_a in profiles and c.company_b in profiles, c
    assert len(live(profiles)) == len(judged), "a basis item is missing or not public"
    # a basis item made private drops the connection
    first = judged[0].connection
    item = next(i for i in profiles[first.company_a].items if i.id == first.basis[0].item_a_id)
    item.visibility = "private"
    assert len(live(profiles)) == len(judged) - 1
    print("ok", len(judged))
