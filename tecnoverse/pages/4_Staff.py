from collections import defaultdict

import streamlit as st

from agents.mapper import live
from agents.scoring import rank_connections
from core.store import load_profile

if st.session_state["user"].role != "staff":
    st.error("Staff only.")
    st.stop()

profiles = {c.id: load_profile(c.id) for c in st.session_state["companies"]}
judged = live(profiles)

st.title("Staff view")
st.caption(f"{len(profiles)} companies. Built from public profile items only. Connections are suggestions: "
           "no company has expressed interest. Judgements marked SIMULATED were written offline, not by a live model.")


def name(cid: str) -> str:
    c = profiles[cid].company
    return c.name + (" :violet-badge[member]" if c.is_member else "")


def evidence(cid: str, item_id: str) -> str:
    """The basis item with its source link and retrieval date."""
    p = profiles[cid]
    item = next(i for i in p.items if i.id == item_id)
    page = next((pg for pg in p.pages if pg.id == item.source_page_id), None)
    source = f"[source]({page.url}) · retrieved {page.retrieved_at:%Y-%m-%d}" if page else "no source page"
    simulated = " :orange-badge[SIMULATED extraction]" if "Claude Code" in p.extracted_by else ""
    return f"**{p.company.name}** ({item.field}): \"{item.value}\" · {source}{simulated}"


st.subheader("Shared themes")
themes = defaultdict(set)
for j in judged:
    themes[j.theme] |= {j.connection.company_a, j.connection.company_b}
for theme, ids in sorted(themes.items(), key=lambda t: -len(t[1])):
    st.markdown(f"- **{theme}** ({len(ids)}): " + ", ".join(sorted(profiles[i].company.name for i in ids)))

st.subheader("Suggested connections")
members_only = st.toggle("Park members only", value=True)
shown = [j for j in judged if not members_only
         or (profiles[j.connection.company_a].company.is_member and profiles[j.connection.company_b].company.is_member)]
for j in shown:
    c = j.connection
    with st.container(border=True):
        st.markdown(f"**{name(c.company_a)} ↔ {name(c.company_b)}** · {j.theme} · "
                    f"{c.type.replace('_', ' ')} · :blue-badge[{c.label}] :gray-badge[SIMULATED]")
        st.markdown(f"**Why:** {j.why}  \n**Uncertain:** {j.uncertain}")
        st.markdown("**Basis (public items):**")
        for b in c.basis:
            st.markdown(f"- {evidence(c.company_a, b.item_a_id)}\n- {evidence(c.company_b, b.item_b_id)}")

pairs = {(j.connection.company_a, j.connection.company_b) for j in judged}
rest = [s for s in rank_connections([(p.company, p.items) for p in profiles.values()])
        if (s.connection.company_a, s.connection.company_b) not in pairs][:20]
with st.expander(f"Other pairs ({len(rest)} shown): keyword overlap only, not judged relevant"):
    for s in rest:
        st.markdown(f"- {s.names[0]} ↔ {s.names[1]} · score {s.breakdown['final']:.2f} · "
                    + (s.connection.basis[0].text if s.connection.basis else ""))
