import streamlit as st

st.title("About TecnoVerse")
st.markdown(
    """
A prototype for the Blue Science Park *Virtual Science Park* challenge (BUILD Hackathon 2026).

**Agents**

- **Profiler** builds a baseline profile from a company's public website. Every item has a source, a date and a status.
- **Monitors** collect funding calls, events and testbeds from public sources.
- **Matcher** ranks opportunities for each company and explains the fit and the uncertainties.
- **Assistant** answers questions within the science park's purpose and redirects everything else.
- **Staff mapper** suggests connections between members from public information only.

**What the labels mean**

- **fact**: stated on a public page, with a verified quote.
- **inferred**: the system's guess. Not a confirmed company priority.
- **missing**: nothing found.
- **confirmed**: set or corrected by the company.
- **Claude Code**: extracted or written offline by Claude Code during development, with the same quote check.
- **SIMULATED**: cached, curated or placeholder data, and the simulated login. Not a live result.

Funding is always a *possible match*, never confirmed eligibility. Decisions and commitments are made by
Blue Science Park staff, not by this service.
"""
)
