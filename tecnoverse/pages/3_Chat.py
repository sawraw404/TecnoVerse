import streamlit as st

from agents.assistant import reply
from core.store import load_opportunities

LABELS = {"in_scope": ("in scope", "green"), "unclear": ("clarifying", "orange"), "out_of_scope": ("out of scope", "gray"),
          "injection": ("blocked: rule change", "red"), "needs_staff": ("referred to staff", "blue")}

company = st.session_state["company"]
opps = {o.id: o for o in load_opportunities()}


def with_sources(text: str, cited: list[str]) -> str:
    """Every opportunity the answer used is listed with its link and date, so it can be checked."""
    lines = [f"- [{opps[i].title}]({opps[i].url}) · {opps[i].deadline or opps[i].start_date or 'no date stated'}"
             for i in cited if i in opps]
    return text + ("\n\n**Sources:**\n" + "\n".join(lines) if lines else "")


user = st.session_state["user"]

st.title("Chat")
st.caption("Ask about funding, events, test environments, partners, your profile and recommendations, "
           "or the right contact at Blue Science Park. Answers use only your own company's data.")

# one conversation per logged-in user; switching user starts a new one, so chats never mix
key = f"chat-{user.id}"
history = st.session_state.setdefault(key, [])

for role, text, label in history:
    with st.chat_message(role):
        if label:
            name, colour = LABELS[label]
            st.markdown(f":{colour}-badge[{name}]")
        st.markdown(text)

if message := st.chat_input("Ask a question"):
    with st.chat_message("user"):
        st.markdown(message)
    with st.chat_message("assistant"), st.spinner("Checking the question..."):
        r = reply(message, [(h[0], h[1]) for h in history], company.id if company else None)
        name, colour = LABELS[r.label]
        st.markdown(f":{colour}-badge[{name}]")
        text = with_sources(r.text, r.cited)
        st.markdown(text)
    history += [("user", message, None), ("assistant", text, r.label)]
