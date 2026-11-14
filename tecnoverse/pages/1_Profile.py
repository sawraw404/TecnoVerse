import streamlit as st

from agents import editor
from agents.profiler import profile_company
from core.llm import LLMError
from core.store import load_matches, load_opportunities, load_profile

FIELD_LABELS = {
    "industry": "Industry",
    "offering": "Products and services",
    "technology": "Technologies",
    "expertise": "Expertise",
    "application_area": "Application areas",
    "market": "Markets and industries",
    "customer_group": "Customer groups",
    "geography": "Geography",
    "contact": "Who to contact",
    "innovation": "New innovations (from news, blog posts and newsletters)",
    "project": "Projects",
    "collaboration": "Collaborations",
    "priority": "Stated development priorities",
    "possible_interest": "Possible interests (inferred, not confirmed by the company)",
}
BADGES = {  # status -> (label, colour)
    "fact": ("fact", "green"),
    "inferred": ("inferred", "orange"),
    "user_confirmed": ("confirmed", "blue"),
}

company = st.session_state["company"]
user = st.session_state["user"]


def apply(edit, *args):
    """Run an edit, then remember how the dashboard ranking moved so the page can show it."""
    before = {m.opportunity_id: m.rank for m in load_matches(company.id)}
    after = edit(company.id, *args, user.id)
    opps = {o.id: o for o in load_opportunities()}
    moved = [(before[m.opportunity_id] - m.rank, opps[m.opportunity_id].title, m.rank)
             for m in after if m.opportunity_id in before and m.opportunity_id in opps
             and abs(before[m.opportunity_id] - m.rank) >= 2 and m.rank <= 10]  # skip 1-step knock-on shifts
    st.session_state["rank_moves"] = sorted(moved, key=lambda x: -abs(x[0]))[:5]
    st.rerun()

st.title("Profile")
if company is None:
    st.info("Profiles belong to member companies. Log in as a company representative to see one.")
    st.stop()

profile = load_profile(company.id)

left, right = st.columns([3, 1])
left.subheader(company.name)
left.write(f"Website: {company.website}")
if company.is_member:
    left.markdown(":blue-badge[Blue Science Park member]")
if company.found_via:
    left.caption(f"Region: {company.region}. Listed in: "
                 + ", ".join(f"[{f.directory}]({f.url}) ({f.retrieved})" for f in company.found_via))
label = "Re-crawl and rebuild profile" if profile else "Generate baseline profile"
if right.button(label, type="primary" if not profile else "secondary"):
    with st.spinner(f"Reading up to 8 pages of {company.website} and extracting a profile..."):
        try:
            profile = profile_company(company)
        except (LLMError, RuntimeError) as e:
            st.error(f"Could not build the profile: {e}")
            st.stop()

if profile is None:
    st.info("No profile yet. Generate a baseline profile from the company's public website.")
    st.stop()

if profile.company.simulated:
    st.warning("SIMULATED: the live website could not be reached, so this profile was built from cached pages.")

if moves := st.session_state.pop("rank_moves", None):
    st.success("Profile saved. Dashboard ranking updated:  \n" + "  \n".join(
        f"{'↑' if d > 0 else '↓'}{abs(d)} {t} (now #{r})" for d, t, r in moves))

with st.container(border=True):
    st.markdown("**Current priorities** (set by you; they raise matching opportunities on the dashboard)")
    labels = {"funding": "Funding is a priority", "event": "Events are a priority", "testbed": "Testing is a priority"}
    chosen = [t for t, label in labels.items()
              if st.checkbox(label, value=t in profile.company.priority_types, key=f"prio-{t}")]
    if chosen != list(profile.company.priority_types) and st.button("Save priorities", type="primary"):
        apply(editor.set_priorities, chosen)

pages = {p.id: p for p in profile.pages}
shown = [i for i in profile.items if i.status != "user_removed"]
counts = {s: sum(i.status == s for i in shown) for s in ("fact", "inferred", "missing")}
st.caption(
    f"Built from {len(pages)} public pages, retrieved {profile.company.last_crawled_at:%Y-%m-%d}. "
    f"{counts['fact']} facts, {counts['inferred']} inferred, {counts['missing']} fields with nothing found. "
    "Facts are backed by a quote found on the page. Inferred items are the system's guesses."
)
if "Claude Code" in profile.extracted_by:
    st.info(f"Extracted by Claude Code: read by {profile.extracted_by}, not by the app's own Profiler. "
            "Every quote was checked against the stored page text.")
else:
    st.caption(f"Extracted by: {profile.extracted_by}")

for field, title in FIELD_LABELS.items():
    items = [i for i in shown if i.field == field]
    st.markdown(f"#### {title}")
    with st.popover(f"Add to {title.split(' (')[0].lower()}"):
        new = st.text_input("Value", key=f"add-{field}")
        if st.button("Add (private, confirmed by you)", key=f"addbtn-{field}") and new.strip():
            apply(editor.add, field, new)
    if not items or all(i.status == "missing" for i in items):
        st.badge("missing", color="gray")
        st.caption("Nothing found on the public pages. Not filled in with a guess.")
        continue
    for item in items:
        badge, colour = BADGES[item.status]
        tags = f":{colour}-badge[{badge}]" + (" :red-badge[uncertain]" if item.uncertain else "")
        page = pages.get(item.source_page_id)
        if page:
            source = f"[source]({page.url}) · retrieved {page.retrieved_at:%Y-%m-%d}"
        else:
            source = "no source page"
        if item.created_by == "user":
            source = f"added by you · {item.updated_at:%Y-%m-%d}" + (" · :gray-badge[private]" if item.visibility == "private" else "")
        st.markdown(f"{tags} **{item.value}**  \n{source}")
        with st.popover("Edit"):
            if item.status != "user_confirmed" and st.button("Confirm as correct", key=f"ok-{item.id}"):
                apply(editor.confirm, item.id)
            fixed = st.text_input("Correct to", value=item.value, key=f"fix-{item.id}")
            if st.button("Save correction", key=f"fixbtn-{item.id}") and fixed.strip() and fixed != item.value:
                apply(editor.correct, item.id, fixed)
            if st.button("Remove", key=f"rm-{item.id}"):
                apply(editor.remove, item.id)
        if item.quote or item.reasoning:
            with st.expander("Evidence"):
                if item.quote and item.quote_verified:
                    st.markdown(f"> {item.quote}")
                    st.caption(f"Quote found on {page.url if page else 'the page'}")
                elif item.quote:
                    st.markdown(f"> {item.quote}")
                    st.caption("This quote was NOT found on the page.")
                if item.reasoning:
                    st.write(item.reasoning)

removed = [i for i in profile.items if i.status == "user_removed"]
if removed:
    with st.expander(f"Corrected or removed by you ({len(removed)})"):
        for i in removed:
            st.markdown(f"- ~~{i.value}~~ ({FIELD_LABELS.get(i.field, i.field)}) · {i.updated_at:%Y-%m-%d}")

with st.expander(f"Pages read ({len(pages)})"):
    for p in pages.values():
        st.markdown(f"- [{p.title or p.url}]({p.url}) · retrieved {p.retrieved_at:%Y-%m-%d %H:%M} UTC")
