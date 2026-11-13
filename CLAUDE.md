# Park Pilot

Prototype for the Blue Science Park "Virtual Science Park" challenge (BUILD Hackathon, 13–15 Nov 2026, Karlskrona). Shared team repo: `sawraw404/TecnoVerse`.

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
| LLM | **Gemini → Ollama**. No Groq. | Ollama is installed and ready; a third provider is a second key and code path for no demo gain. Add Groq only if Gemini limits actually bite. |
| Vector search | **numpy cosine** over the `embeddings` SQLite table. No Chroma. | Under 200 opportunities. |
| Validation | **Pydantic** | Gemini takes Pydantic models as its response schema directly. |
| Layout | README's `park_pilot/` with `agents/`, `core/`, `eval/` | One file per agent keeps teammates out of each other's way. |
| Item status | README's: `fact`, `inferred`, `missing`, `user_confirmed`, `user_removed` | UI badge for `user_confirmed` reads "confirmed". Includes quote verification, correction history and public/private visibility. |
| Boundary tests | README's **11** (covers the plan's 10) | |
| Demo companies | **5** from the BSP member list, clearly different, **one sensor/industrial** | User's choice; the sensor company mirrors the brief's example journey. |

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

**Fallbacks.** Scrape or API fails → cached data labelled SIMULATED. Rate limit or no Wi-Fi → Ollama.

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
- Never commit `.env`, API keys, or the two PDFs (the repo is public; both are in `.gitignore`).
