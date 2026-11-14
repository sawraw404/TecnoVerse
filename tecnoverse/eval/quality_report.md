# Quality check

Run 2026-11-14 06:09 on 38 companies, 31 opportunities. Automated checks: `python -m eval.quality`. No network or LLM is used.

## Traceability
- Profile items shown with a source page, link and retrieval date: **509/509**
- Opportunities with a link: **31/31**; funding and events with a deadline or start date: **26/26** (testbeds are standing offers without a date)
- Match explanations that point to an existing company and opportunity: **97/97**

## Profile accuracy
- Facts whose quote is found again in the stored page text (contacts: the address or number): **403/403**
- Hand spot-check of 25 randomly sampled facts (seed 14), value compared with its quote and page: **24/25 correct**. Reviewed by Claude Code, not by a person.
  - ba0cf6ebd3a264d9: Ericsson contact was the park mailbox info@bluesciencepark.se, taken from a park news page. Same error found for Lysa, Dosify and Parkerra. Fixed: removed, and the Profiler now takes contacts from the company's own site only.
- Contacts taken from the company's own site (rule: its published contact route, nothing from third parties): **0 from another site**
- Companies with no contact route: **0** 

## Relevance
- Demo edit, EmbeddedArt ticks "testing is a priority": average testbed rank **13.4 → 9.2**
- Different companies get different rankings: average overlap of two companies' top-5 judged matches is **8%**
- Companies with no judged match (dashboard shows only keyword overlap): **0** 
- Explanations or connections that say "eligible" or "you qualify": **0**
- Judged connections still backed by public items: **15/15**

Relevance judgements were written offline by Claude Code, so the ranking numbers check that the system behaves as designed, not that a company would agree. That needs member feedback (the thumbs on the dashboard).
