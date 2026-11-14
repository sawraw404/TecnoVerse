"""Streamlit entry point: streamlit run tecnoverse/app.py"""
import streamlit as st

from core.schemas import Company, User
from core.store import load_companies


def demo_users(companies: list[Company]) -> list[User]:
    users = [
        User(id=f"rep-{c.id}", name=f"{c.name} representative", role="member", company_id=c.id)
        for c in companies
    ]
    users.append(User(id="staff", name="Blue Science Park staff", role="staff"))
    users.append(User(id="guest", name="External visitor", role="external"))
    return users


st.set_page_config(page_title="TecnoVerse", page_icon="🔭", layout="wide")

companies = st.cache_data(load_companies)()  # read from the file until the Firebase layer exists
users = demo_users(companies)

with st.sidebar:
    st.title("TecnoVerse")
    st.caption("Virtual Science Park prototype")
    user = st.selectbox("Log in as", users, format_func=lambda u: u.name)
    st.warning("SIMULATED login. No real accounts or passwords.")

st.session_state["user"] = user
st.session_state["companies"] = companies
st.session_state["company"] = next((c for c in companies if c.id == user.company_id), None)

pages = [
    st.Page("pages/1_Profile.py", title="Profile", icon="🏢"),
    st.Page("pages/2_Dashboard.py", title="Dashboard", icon="📋"),
    st.Page("pages/3_Chat.py", title="Chat", icon="💬"),
]
if user.role == "staff":  # the staff view is not even routable for other roles
    pages.append(st.Page("pages/4_Staff.py", title="Staff", icon="🗺️"))
pages.append(st.Page("pages/5_About.py", title="About", icon="ℹ️"))

st.navigation(pages).run()
