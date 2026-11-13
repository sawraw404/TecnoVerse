import streamlit as st

company = st.session_state["company"]

st.title("Dashboard")
st.caption(f"Opportunities for {company.name}" if company else "All opportunities (no personalised ranking)")
st.info("Not built yet: funding, events and testbeds, ranked, with links, dates and next steps.")
