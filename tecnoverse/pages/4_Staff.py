import streamlit as st

if st.session_state["user"].role != "staff":
    st.error("Staff only.")
    st.stop()

st.title("Staff view")
st.caption("Built from public profile items only. Connections are suggestions; no company has expressed interest.")
st.info("Not built yet: shared themes and suggested connections across members.")
