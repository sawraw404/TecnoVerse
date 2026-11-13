import streamlit as st

from agents.profiler import profile_company
from core.llm import LLMError
from core.store import load_profile

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

pages = {p.id: p for p in profile.pages}
shown = [i for i in profile.items if i.status != "user_removed"]
counts = {s: sum(i.status == s for i in shown) for s in ("fact", "inferred", "missing")}
st.caption(
    f"Built from {len(pages)} public pages, retrieved {profile.company.last_crawled_at:%Y-%m-%d}. "
    f"{counts['fact']} facts, {counts['inferred']} inferred, {counts['missing']} fields with nothing found. "
    "Facts are backed by a quote found on the page. Inferred items are the system's guesses."
)

for field, title in FIELD_LABELS.items():
    items = [i for i in shown if i.field == field]
    st.markdown(f"#### {title}")
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
        st.markdown(f"{tags} **{item.value}**  \n{source}")
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

with st.expander(f"Pages read ({len(pages)})"):
    for p in pages.values():
        st.markdown(f"- [{p.title or p.url}]({p.url}) · retrieved {p.retrieved_at:%Y-%m-%d %H:%M} UTC")
