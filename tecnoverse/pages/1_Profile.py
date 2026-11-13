import streamlit as st

company = st.session_state["company"]

st.title("Profile")
if company is None:
    st.info("Profiles belong to member companies. Log in as a company representative to see one.")
else:
    st.subheader(company.name)
    st.write(f"Website: {company.website}")
    st.info("Not built yet: the Profiler will fill this page with sourced, dated, tagged profile items.")
