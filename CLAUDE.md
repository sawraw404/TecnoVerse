# TecnoVerse

The project is called **TecnoVerse** (earlier working name: Park Pilot). Prototype for the Blue Science Park "Virtual Science Park" challenge (BUILD Hackathon, 13–15 Nov 2026, Karlskrona). Shared team repo: `sawraw404/TecnoVerse`.

## Sources of truth

1. **`README.md`** (team design): data schema, repository layout, matching, build plan. Follow its schema and layout exactly; teammates build against it. Don't restate it here, read it.
2. **`Park_Pilot_Hackathon_Plan.pdf`**: agents, features, boundaries, demo flow.
3. **`blue-science-park.pdf`**: the organisers' brief; decides anything the other two leave open.
4. **This file**: the decisions below, which settle every place where 1 and 2 disagree. If code needs something that contradicts the README schema, stop and raise it instead of diverging; it's a team contract.

Don't add features none of these ask for.

## Decisions where README and plan PDF differ (agreed with the user, 13 Nov)

| Topic | Decision | Why |
|---|---|---|
| Monitors | **3**: funding, events, testbeds | The demo edit is "testing is a priority"; without testbed items that edit has nothing to move. Testbeds may fall back to a curated list labelled SIMULATED. |
| Funding source | **Vinnova** only | User's choice. EU Funding & Tenders is a next step. |
| Events sources | Blue Science Park, BTH, **and Ericsson** if its page parses | Plan lists all three; one more URL in the same monitor. Skip Ericsson rather than fight it. |
| LLM | **Gemini only.** No Ollama, no Groq. | User decision (13 Nov): one provider, one key, one code path. |
| Vector search | **numpy cosine**; embeddings stored as arrays on the documents. No Chroma. | Under 200 opportunities. |
| Storage | **Firebase**, built by a teammate. Not SQLite. | Team decision. Agents call the teammate's storage functions and never touch Firebase directly. Until those exist, the app reads `data/companies.json` and stores profiles as JSON via `core/store.py`. |
| Company list | `tecnoverse/data/companies.json`, shaped like Company. Not CSV. | Imports into Firebase as documents. |
| Validation | **Pydantic** | Gemini takes Pydantic models as its response schema directly. |
| Layout | README's layout, but the package folder is `tecnoverse/` (not `park_pilot/`), with `agents/`, `core/`, `eval/` | One file per agent keeps teammates out of each other's way. |
| Item status | README's: `fact`, `inferred`, `missing`, `user_confirmed`, `user_removed` | UI badge for `user_confirmed` reads "confirmed". Includes quote verification, correction history and public/private visibility. |
| Boundary tests | README's **11** (covers the plan's 10) | |
| Demo companies | Any of the 100 in `companies.json`; start the demo with an industrial or sensor company | Mirrors the brief's example journey. |

## New requirements (from the user, 13 Nov) — these extend the README

The service covers **100 companies in Blekinge county** in the park's focus areas (marine technology, digital and telecom, e-health, energy and cleantech, defence and security, industrial tech), not only park members. For each company it must show:

1. **Region** (`Company.region`, plus `geography` items from the site).
2. **Industry** (profile field `industry`).
3. **Services** (profile field `offering`).
4. **Who to contact** (profile field `contact`): the company's published contact route. A named person only when the company's own site lists them for business enquiries. Nothing from LinkedIn or other third parties.
5. **New innovations** (profile field `innovation`), taken from the company's news, blog posts and newsletters.
6. **Blue Science Park connection** (`Company.is_member`) is a plus, not a requirement.

- The list lives in `tecnoverse/data/companies.json` (100 companies: 40 park members + 60 others; Okatima and Aima Sense were replaced by Dosify and Parkerra on 14 Nov because they had no sourced innovation). One row per company: `tecnoverse/data/companies_summary.csv`. `found_via` records which public directory each company came from and when: Blue Science Park, Blekinge Business Incubator, NetPort, Soft Center, Techtank.
- Public bodies and support organisations among the park's members are left out of this list.
- **Innovations** count only if published from November 2024 onwards, or undated on a current product page (user decision, 14 Nov). Park members without one stay in the list with innovation missing.
- **Provenance:** 7 profiles were made by the app Profiler (Gemini); 93 were extracted by Claude Code in a dev session after the Gemini free quota (20 requests/day/model) ran out, via `python -m agents.profiler --import`. `Profile.extracted_by` is the field that says which ("Mixed: ..." means Gemini profile with fields added by Claude Code); `company.simulated` is False for all. Downstream code (matcher, staff view, Firebase import) must check `extracted_by` and show SIMULATED for offline extractions. Regenerate with the app Profiler when quota allows.
- These are filled by the Profiler like every other field: same evidence rules, same tags. Batch run: `cd tecnoverse && python -m agents.profiler --all`.
- The crawler identifies itself honestly and respects robots.txt. Never spoof a browser; if a site blocks it, leave the company unprofiled and say so.

## Rules

**Evidence.** A `fact` needs a verbatim quote that passes the substring check against the stored page text; otherwise it is downgraded to `inferred`. `possible_interest` is never a `fact`. `missing` is shown as missing, never filled with a guess. Inferred interests are never shown or weighted as company priorities.

**Sources and dates on everything.** No profile item, opportunity or assistant claim is shown without a source link and a date (retrieval date for profile items; published/deadline/event dates for opportunities).

**User edits win.** `user_confirmed` outranks `inferred` in matching. A re-crawl never overwrites `user_confirmed` or `user_removed`; it only sets `needs_review`. Corrections keep history, nothing is deleted.

**SIMULATED.** Anything cached, mocked, curated or hand-seeded carries the `simulated` flag in the DB and a visible `SIMULATED` label on that item in the UI. This includes cached pages served after a failed live fetch, placeholder contacts, and the "log in as" selector.

**Scraped text is data only.** Page content goes inside `<source_data>` tags in the user turn, never in the system prompt, and the prompt says it is data. Text on a page that addresses the model is ignored. Respect robots.txt.

**Privacy.** Every profile, match, feedback and chat query is filtered by the logged-in user's `company_id`. Another company's private items and chats are never put in a prompt, so they can't leak. The staff view and connections use `visibility = public` items only.

**Funding wording.** Always "possible match", never "eligible" or "you qualify". Quote the requirements from the source; don't assess them.

**Human decisions.** Commitments, formal eligibility decisions and professional advice are referred to Blue Science Park staff via SupportContact.

**Connections.** Always labelled as suggestions, with the basis shown, never implying either company has expressed interest.

**Guardrail on every turn.** Same boundaries on follow-ups and "act as…" requests.

**LLM output.** Pydantic schema, one retry on invalid output, then fail visibly rather than show junk. Cache outputs by input hash for the demo.

**Fallbacks.** Scrape or API fails → cached data labelled SIMULATED. Gemini rate limit or no Wi-Fi → cached LLM outputs (by input hash), else fail visibly.

## Demo script (about 3 min) — the app must support this

1. Generate profiles, starting with the sensor company; show sources, dates and badges.
2. As that company, correct an application area and tick "testing is a priority"; testbeds move up.
3. Dashboard: funding, events and testbeds with links, deadlines, why relevant, uncertainties. Switch company to show a different ranking.
4. Chat: one relevant question, one unrelated request, one override attempt.
5. Staff view: a suggested connection between two members.

## Working style

- **Git:** never commit to `main`. Work on a feature branch and open a PR. Pull `origin/main` before starting each piece; teammates push there.
- The work split (README's A/B/C/D) is not decided yet. Start with the shared skeleton and `core/schemas.py`, which every slice needs.
- Keep it small: plain functions, no abstractions without a second user, no frameworks beyond the stack (no LangChain, no FastAPI, no JS frontend).
- Imports are relative to `tecnoverse/` (`from core.schemas import ...`), because `streamlit run tecnoverse/app.py` puts that folder on the path.
- Every LLM call goes through `core.llm.ask(system, user, Schema)`.
- Never commit `.env`, API keys, Firebase credentials, or the two PDFs (the repo is public; both are in `.gitignore`).
