import streamlit as st

from agents.matcher import give_feedback, load_explanations, match_company
from core.store import load_matches, load_opportunities

PER_TYPE = 5
TABS = [("funding", "Funding"), ("event", "Events"), ("testbed", "Testbeds")]
DATE_LABEL = {"funding": "Deadline", "event": "Starts", "testbed": "Date"}

company = st.session_state["company"]
user = st.session_state["user"]
opps = {o.id: o for o in load_opportunities()}

st.title("Dashboard")
if not opps:
    st.info("No opportunities collected yet. Run the monitors: `python -m agents.monitors --run`.")
    st.stop()

if company is None:  # staff or external visitor: everything, no personal ranking
    st.caption("All collected opportunities. Log in as a company to see them ranked for that company.")
    for kind, label in TABS:
        st.subheader(label)
        for o in sorted((o for o in opps.values() if o.type == kind), key=lambda o: str(o.deadline or o.start_date)):
            st.markdown(f"- [{o.title}]({o.url}) · {DATE_LABEL[kind]} {o.deadline or o.start_date or 'not stated'}")
    st.stop()

matches = load_matches(company.id) or match_company(company.id)
explained = load_explanations()
st.caption(f"Ranked for {company.name}. Funding is always a possible match: eligibility is never assessed here.")


def email(o) -> str:
    return (f"Subject: {o.title}\n\nHello,\n\nWe are {company.name} ({company.website}). We saw "
            f"\"{o.title}\" and believe it may fit our work. Could you tell us more about how to take part "
            f"and whether our profile could be relevant?\n\nBest regards,\n{company.name}")


def card(m, o, where=""):
    with st.container(border=True):
        badge = ":blue-badge[possible match]" if o.type == "funding" else ""
        moved = ""
        if m.prev_rank and m.prev_rank != m.rank:
            moved = f" :green[↑{m.prev_rank - m.rank}]" if m.prev_rank > m.rank else f" :red[↓{m.rank - m.prev_rank}]"
        st.markdown(f"**[{o.title}]({o.url})** {badge}{moved}  \n"
                    f"{DATE_LABEL[o.type]}: {o.deadline or o.start_date or 'not stated'} · source: {o.source} · "
                    f"retrieved {o.retrieved_at:%Y-%m-%d}" + (" · :orange-badge[SIMULATED]" if o.simulated else ""))
        ex = explained.get((company.id, o.id))
        if ex:
            st.markdown(f"**Why it fits:** {ex.why}  \n**Uncertain:** {ex.uncertain}")
        else:
            st.markdown("**Why it may fit:** " + "; ".join(r.text for r in m.reasons[:2]))
            if m.uncertainties:
                st.markdown("**Uncertain:** " + "; ".join(m.uncertainties))
        with st.expander("Next step"):
            st.write(m.next_step)
            if o.requirements:
                st.markdown("**Requirements, as published by the source (not assessed):**")
                for r in o.requirements:
                    st.markdown(f"> {r}")
            if o.contact:
                st.write(f"Contact: {o.contact}")
            st.text_area("Draft intro email", email(o), height=170, key=f"mail-{where}{o.id}")
        up, down, _ = st.columns([1, 1, 6])
        if up.button("👍", key=f"up-{where}{o.id}", help="More like this"):
            give_feedback(company.id, o.id, "up", user.id)
            st.rerun()
        if down.button("👎", key=f"down-{where}{o.id}", help="Less like this"):
            give_feedback(company.id, o.id, "down", user.id)
            st.rerun()


top_tab, *type_tabs = st.tabs(["Top matches"] + [label for _, label in TABS])
with top_tab:
    st.caption("Best matches across funding, events and testbeds. Your priorities on the Profile page move types up here.")
    for m in [m for m in matches if m.llm_score > 0 and m.opportunity_id in opps][:PER_TYPE]:
        card(m, opps[m.opportunity_id], "top")

for tab, (kind, label) in zip(type_tabs, TABS):
    with tab:
        ranked = [m for m in matches if m.opportunity_id in opps and opps[m.opportunity_id].type == kind]
        relevant = [m for m in ranked if m.llm_score > 0]  # judged relevant in the re-rank step
        if not relevant:
            st.info(f"No {label.lower()} judged relevant for {company.name} right now.")
        for m in relevant[:PER_TYPE]:
            card(m, opps[m.opportunity_id], kind)
        rest = [m for m in ranked if m.llm_score == 0]
        if rest:
            with st.expander(f"Other {label.lower()} ({len(rest)}): similar by text only, not judged relevant"):
                for m in rest:
                    o = opps[m.opportunity_id]
                    st.markdown(f"- [{o.title}]({o.url}) · {DATE_LABEL[kind]} {o.deadline or o.start_date or 'not stated'}")
