"""Streamlit entry point: streamlit run tecnoverse/app.py"""
import json
from pathlib import Path

import streamlit as st

from core.schemas import Company, User

MEMBERS = Path(__file__).parent / "data" / "members.json"


@st.cache_data
def load_companies() -> list[Company]:
    # Until the Firebase storage layer exists, the member list is read straight from the file.
    return [Company(**c) for c in json.loads(MEMBERS.read_text(encoding="utf-8"))]


def demo_users(companies: list[Company]) -> list[User]:
    users = [
        User(id=f"rep-{c.id}", name=f"{c.name} representative", role="member", company_id=c.id)
        for c in companies
    ]
    users.append(User(id="staff", name="Blue Science Park staff", role="staff"))
    users.append(User(id="guest", name="External visitor", role="external"))
    return users


st.set_page_config(page_title="TecnoVerse", page_icon="🔭", layout="wide")

companies = load_companies()
users = demo_users(companies)

with st.sidebar:
    st.title("TecnoVerse")
    st.caption("Virtual Science Park prototype")
    user = st.selectbox("Log in as", users, format_func=lambda u: u.name)
    st.warning("SIMULATED login. No real accounts or passwords.")

st.session_state["user"] = user
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
