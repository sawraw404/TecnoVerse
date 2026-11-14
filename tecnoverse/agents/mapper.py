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


if __name__ == "__main__":
    profiles = {c.id: load_profile(c.id) for c in load_companies()}
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
