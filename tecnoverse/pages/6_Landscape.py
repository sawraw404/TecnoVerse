import streamlit as st
import streamlit.components.v1 as components

from core.landscape import build_map, industries, load_locations, matches_search, public_topics
from core.store import load_companies, load_profile

st.title("Blekinge innovation map")
st.caption("Explore public company capabilities and sourced locations.")
st.warning(
    "SIMULATED: locations are a manually checked snapshot and profiles are cached. "
    "Capabilities are not confirmed company interests or priorities."
)

companies = load_companies()
profiles = {company.id: load_profile(company.id) for company in companies}
locations = load_locations()
industry_options = sorted({value for profile in profiles.values() for value in industries(profile)})

left, right = st.columns(2)
query = left.text_input("Search company or capability", placeholder="For example: marine, energy, cloud")
industry = right.selectbox("Industry (as described in profiles)", ["All industries", *industry_options])

filtered = [
    company for company in companies
    if matches_search(company, profiles[company.id], query)
    and (industry == "All industries" or industry in industries(profiles[company.id]))
]
mapped = [company for company in filtered if company.id in locations]
unmapped = [company for company in filtered if company.id not in locations]

st.caption(
    f"{len(mapped)} of {len(filtered)} matching companies have a mapped location. "
    f"{len(unmapped)} are not mapped. Zoom in to separate clusters; click a marker for its source."
)
if mapped:
    components.html(build_map(mapped, locations, profiles).get_root().render(), height=560, scrolling=False)
    st.caption(
        "Blue markers are approximate address locations; orange markers show a municipality "
        "reference point, not the company's office. "
        "Map tiles and interactive map libraries need an internet connection. "
        "Map data © OpenStreetMap contributors."
    )
else:
    st.info("No verified, mappable locations match these filters.")

with st.expander(f"Mapped companies and location evidence ({len(mapped)})"):
    for company in mapped:
        location = locations[company.id]
        st.markdown(f"**{company.name}** · {location.municipality} · SIMULATED")
        st.write(location.address)
        st.caption(
            f"Location source retrieved {location.retrieved_at}: {location.source_quote} "
            f"Coordinate note: {location.coordinate_note}"
        )
        st.link_button("Location source", str(location.source_url), key=f"location-{company.id}")
        st.link_button("Coordinate source", str(location.coordinate_source), key=f"coordinates-{company.id}")
        topics = [item for item in public_topics(profiles[company.id]) if item.field == "industry"]
        for item in topics:
            page = next((p for p in profiles[company.id].pages if p.id == item.source_page_id), None)
            st.write(f"Industry: {item.value} ({item.status}; SIMULATED snapshot)")
            if page:
                st.markdown(f"[Industry source]({page.url}) · retrieved {page.retrieved_at:%Y-%m-%d}")

with st.expander(f"Not mapped ({len(unmapped)})"):
    st.caption("A company is not placed until its location and coordinates are checked.")
    for company in unmapped:
        st.write(company.name)
