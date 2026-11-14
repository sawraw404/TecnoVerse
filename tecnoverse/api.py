"""HTTP API over the agents, for the Next.js frontend (web/). User decision, 14 Nov.

Run from the repo root: uvicorn api:app --app-dir tecnoverse --host 127.0.0.1 --port 8000

Auth is the SIMULATED "log in as" selector: the frontend's server sends the chosen user id in the
X-User-Id header. The company is always derived from that user on this side, never taken from the
request, so a member can only read and edit its own company. The staff view is staff only and uses
public items only. The browser never calls this API directly; only the Next server does.
"""
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from agents import editor
from agents.assistant import reply
from agents.mapper import Graph, knowledge_graph, live
from agents.matcher import current_matches, feedback_state, give_feedback, load_explanations
from agents.profiler import profile_company
from agents.scoring import rank_connections
from core.llm import LLMError
from core.schemas import ChatLog, Company, Match, Opportunity, ProfileItem, User
from core.store import load_chats, load_companies, load_opportunities, load_profile, save_chats

app = FastAPI(title="TecnoVerse API")

FIELD_LABELS = {
    "industry": "Industry",
    "offering": "Products and services",
    "technology": "Technologies",
    "expertise": "Expertise",
    "application_area": "Application areas",
    "market": "Markets and industries",
    "customer_group": "Customer groups",
    "geography": "Geography",
    "contact": "Who to contact",
    "innovation": "New innovations",
    "project": "Projects",
    "collaboration": "Collaborations",
    "priority": "Stated development priorities",
    "possible_interest": "Possible interests",
}


# --- users (SIMULATED login) ---------------------------------------------------------------------

def users() -> dict[str, User]:
    out = [User(id=f"rep-{c.id}", name=f"{c.name} representative", role="member", company_id=c.id)
           for c in load_companies()]
    out += [User(id="staff", name="Blue Science Park staff", role="staff"),
            User(id="guest", name="External visitor", role="external")]
    return {u.id: u for u in out}


def current_user(x_user_id: str = Header(default="guest")) -> User:
    user = users().get(x_user_id)
    if user is None:
        raise HTTPException(401, "Unknown user")
    return user


def member(user: User = Depends(current_user)) -> User:
    if user.role != "member" or not user.company_id:
        raise HTTPException(403, "Only a company representative can do this")
    return user


def staff(user: User = Depends(current_user)) -> User:
    if user.role != "staff":
        raise HTTPException(403, "Staff only")
    return user


@app.get("/users")
def list_users() -> list[User]:
    return list(users().values())


class Me(BaseModel):
    user: User
    company: Company | None


@app.get("/me")
def me(user: User = Depends(current_user)) -> Me:
    company = next((c for c in load_companies() if c.id == user.company_id), None)
    return Me(user=user, company=company)


# --- profile -------------------------------------------------------------------------------------

class PageRef(BaseModel):
    id: str
    url: str
    title: str
    retrieved_at: datetime


class ProfileView(BaseModel):
    company: Company
    extracted_by: str
    field_labels: dict[str, str]
    items: list[ProfileItem]          # everything except user_removed
    removed: list[ProfileItem]        # correction history
    pages: list[PageRef]              # page text stays on the server
    counts: dict[str, int]


@app.get("/profile")
def get_profile(user: User = Depends(member)) -> ProfileView | None:
    p = load_profile(user.company_id)
    if p is None:
        return None
    shown = [i for i in p.items if i.status != "user_removed"]
    return ProfileView(
        company=p.company, extracted_by=p.extracted_by,
        field_labels=FIELD_LABELS, items=shown, removed=[i for i in p.items if i.status == "user_removed"],
        pages=[PageRef(id=pg.id, url=pg.url, title=pg.title, retrieved_at=pg.retrieved_at) for pg in p.pages],
        counts={s: sum(i.status == s for i in shown) for s in ("fact", "inferred", "missing", "user_confirmed")})


class Move(BaseModel):
    delta: int        # positive = moved up
    title: str
    rank: int


def _apply(user: User, edit, *args) -> list[Move]:
    """Run an edit, then report how the ranking moved (2+ places, top 10, at most 5)."""
    before = {m.opportunity_id: m.rank for m in current_matches(user.company_id)}
    try:
        after = edit(user.company_id, *args, user.id)
    except StopIteration:
        raise HTTPException(404, "No such profile item")
    except ValueError as e:
        raise HTTPException(422, str(e))
    opps = {o.id: o for o in load_opportunities()}
    moved = [Move(delta=before[m.opportunity_id] - m.rank, title=opps[m.opportunity_id].title, rank=m.rank)
             for m in after if m.opportunity_id in before and m.opportunity_id in opps
             and abs(before[m.opportunity_id] - m.rank) >= 2 and m.rank <= 10]
    return sorted(moved, key=lambda x: -abs(x.delta))[:5]


class Value(BaseModel):
    value: str


class NewItem(BaseModel):
    field: Literal[tuple(FIELD_LABELS)]
    value: str


class Priorities(BaseModel):
    types: list[Literal["funding", "event", "testbed"]]


@app.post("/profile/items/{item_id}/confirm")
def confirm(item_id: str, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.confirm, item_id)


@app.post("/profile/items/{item_id}/remove")
def remove(item_id: str, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.remove, item_id)


@app.post("/profile/items/{item_id}/correct")
def correct(item_id: str, body: Value, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.correct, item_id, body.value)


@app.post("/profile/items")
def add(body: NewItem, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.add, body.field, body.value)


class VisibilityIn(BaseModel):
    visibility: Literal["public", "private"]


@app.post("/profile/items/{item_id}/visibility")
def visibility(item_id: str, body: VisibilityIn, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.set_visibility, item_id, body.visibility)


@app.put("/profile/priorities")
def priorities(body: Priorities, user: User = Depends(member)) -> list[Move]:
    return _apply(user, editor.set_priorities, body.types)


@app.post("/profile/rebuild")
def rebuild(user: User = Depends(member)) -> dict:
    company = next(c for c in load_companies() if c.id == user.company_id)
    try:
        profile_company(company)
    except (LLMError, RuntimeError) as e:
        raise HTTPException(503, f"Could not build the profile: {e}")
    return {"ok": True}


# --- dashboard -----------------------------------------------------------------------------------

class Card(BaseModel):
    opportunity: Opportunity
    match: Match | None = None
    why: str | None = None          # stored judgement: why it fits
    uncertain: str | None = None
    judged: bool = False
    saved: bool = False
    vote: Literal["up", "down"] | None = None


class Dashboard(BaseModel):
    ranked: bool                    # false for staff and external users: everything, no personal ranking
    company: Company | None
    top: list[Card]
    by_type: dict[str, list[Card]]  # judged relevant, best first (all opportunities when not ranked)
    rest: dict[str, list[Card]]     # keyword overlap only, not judged relevant
    saved: list[Card] = []          # saved by the company, in ranking order


PER_TYPE = 5
TYPES = ("funding", "event", "testbed", "news")  # news = trend monitor


@app.get("/dashboard")
def dashboard(user: User = Depends(current_user)) -> Dashboard:
    opps = {o.id: o for o in load_opportunities()}
    for o in opps.values():
        o.embedding = None
    if user.role != "member":
        by_type = {t: [Card(opportunity=o) for o in sorted((o for o in opps.values() if o.type == t),
                                                             key=lambda o: str(o.deadline or o.start_date))]
                   for t in TYPES}
        by_type["news"].sort(key=lambda c: str(c.opportunity.published_at), reverse=True)  # newest first
        return Dashboard(ranked=False, company=None, top=[], by_type=by_type, rest={t: [] for t in TYPES})
    company = next(c for c in load_companies() if c.id == user.company_id)
    matches = current_matches(company.id)  # rebuilt when out of date (e.g. new trends since it was saved)
    expl = load_explanations()
    saved, votes = feedback_state(company.id)

    def card(m: Match) -> Card:
        e = expl.get((company.id, m.opportunity_id))
        return Card(opportunity=opps[m.opportunity_id], match=m, why=e.why if e else None,
                    uncertain=e.uncertain if e else None, judged=m.llm_score > 0,
                    saved=m.opportunity_id in saved, vote=votes.get(m.opportunity_id))

    cards = [card(m) for m in matches if m.opportunity_id in opps]
    return Dashboard(
        ranked=True, company=company, top=[c for c in cards if c.judged and c.opportunity.type != "news"][:PER_TYPE],
        by_type={t: [c for c in cards if c.judged and c.opportunity.type == t][:PER_TYPE] for t in TYPES},
        rest={t: [c for c in cards if not c.judged and c.opportunity.type == t] for t in TYPES},
        saved=[c for c in cards if c.saved])


class FeedbackIn(BaseModel):
    opportunity_id: str
    kind: Literal["up", "down", "saved", "unsaved"]


@app.post("/feedback")
def feedback(body: FeedbackIn, user: User = Depends(member)) -> dict:
    if body.opportunity_id not in {o.id for o in load_opportunities()}:
        raise HTTPException(404, "No such opportunity")
    give_feedback(user.company_id, body.opportunity_id, body.kind, user.id)
    return {"ok": True}


# --- chat (stored per company, private) -------------------------------------------------------

class Turn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None       # None starts a new conversation
    opportunity_id: str | None = None   # "Ask about this": the opportunity the conversation is about
    company_id: str | None = None       # staff only (graph view): the company the conversation is about


class Source(BaseModel):
    id: str
    title: str
    url: str
    date: date | None


class ChatOut(BaseModel):
    session_id: str
    label: str
    text: str
    sources: list[Source]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    label: str | None
    sources: list[Source]
    created_at: datetime


class CompanyRef(BaseModel):
    id: str
    name: str


class Session(BaseModel):
    session_id: str
    title: str
    opportunity: Source | None
    company: CompanyRef | None = None   # staff chats about a company
    updated_at: datetime
    messages: int


def _owner(user: User) -> str:
    """Chats belong to the company; staff and visitors keep their own, under `_<user id>`."""
    return user.company_id or f"_{user.id}"


def _source(o: Opportunity) -> Source:
    return Source(id=o.id, title=o.title, url=o.url, date=o.deadline or o.start_date)


@app.post("/chat")
def chat(body: ChatIn, user: User = Depends(current_user)) -> ChatOut:
    message = body.message.strip()[:2000]
    if not message:
        raise HTTPException(422, "Empty message")
    opps = {o.id: o for o in load_opportunities()}
    owner = _owner(user)
    logs = load_chats(owner)
    session = body.session_id or uuid.uuid4().hex[:12]
    earlier = [c for c in logs if c.session_id == session]
    if body.session_id and not earlier:
        raise HTTPException(404, "No such conversation")
    about = body.opportunity_id or next((c.opportunity_id for c in earlier if c.opportunity_id), None)
    # staff may chat about one company (graph view); for staff chats ChatLog.company_id records that company
    subject = None
    if user.role == "staff":
        subject = body.company_id or next((c.company_id for c in earlier if c.company_id), None)
        if subject and subject not in {c.id for c in load_companies()}:
            raise HTTPException(404, "No such company")
    elif body.company_id:
        raise HTTPException(403, "Only park staff can ask about another company")
    if about and about not in opps:
        raise HTTPException(404, "No such opportunity")
    # history comes from the stored conversation, not from the browser
    history = [(c.role, c.text) for c in earlier][-12:]
    asked = message
    if about:
        o = opps[about]
        asked = (f"[The user opened this chat from the opportunity {o.id}: \"{o.title}\" ({o.type}, "
                 f"{o.deadline or o.start_date or 'no date'}, {o.url}).]\n{message}")
    r = reply(asked, history, user.company_id, subject)
    logged_company = user.company_id or subject
    now = datetime.now(timezone.utc)
    n = len(logs)
    logs += [ChatLog(id=f"{session}-{n + 1}", company_id=logged_company, user_id=user.id, session_id=session,
                     opportunity_id=about, role="user", text=message, created_at=now),
             ChatLog(id=f"{session}-{n + 2}", company_id=logged_company, user_id=user.id, session_id=session,
                     opportunity_id=about, role="assistant", text=r.text, guard_label=r.label,
                     cited_ids=r.cited, created_at=now)]
    save_chats(owner, logs)
    return ChatOut(session_id=session, label=r.label, text=r.text,
                   sources=[_source(opps[i]) for i in r.cited if i in opps])


@app.get("/chats")
def chats(user: User = Depends(current_user)) -> list[Session]:
    opps = {o.id: o for o in load_opportunities()}
    names = {c.id: c.name for c in load_companies()}
    by: dict[str, list[ChatLog]] = defaultdict(list)
    for c in load_chats(_owner(user)):
        by[c.session_id].append(c)
    out = []
    for sid, turns in by.items():
        first = next((t.text for t in turns if t.role == "user"), "Conversation")
        about = next((t.opportunity_id for t in turns if t.opportunity_id), None)
        subject = next((t.company_id for t in turns if t.company_id), None) if user.role == "staff" else None
        out.append(Session(session_id=sid, title=first[:80], updated_at=max(t.created_at for t in turns),
                           opportunity=_source(opps[about]) if about in opps else None, messages=len(turns),
                           company=CompanyRef(id=subject, name=names[subject]) if subject in names else None))
    return sorted(out, key=lambda s: s.updated_at, reverse=True)


@app.get("/chats/{session_id}")
def chat_messages(session_id: str, user: User = Depends(current_user)) -> list[Message]:
    opps = {o.id: o for o in load_opportunities()}
    turns = [c for c in load_chats(_owner(user)) if c.session_id == session_id]
    if not turns:
        raise HTTPException(404, "No such conversation")
    return [Message(role=c.role, text=c.text, label=c.guard_label, created_at=c.created_at,
                    sources=[_source(opps[i]) for i in c.cited_ids if i in opps]) for c in turns]


@app.get("/opportunities/{opportunity_id}")
def opportunity(opportunity_id: str, user: User = Depends(current_user)) -> Source:
    o = next((o for o in load_opportunities() if o.id == opportunity_id), None)
    if not o:
        raise HTTPException(404, "No such opportunity")
    return _source(o)


# --- staff view ----------------------------------------------------------------------------------

class Evidence(BaseModel):
    company_id: str
    company: str
    field: str
    value: str
    url: str | None
    retrieved_at: datetime | None


class ConnectionView(BaseModel):
    company_a: str
    company_b: str
    name_a: str
    name_b: str
    members: bool               # both are park members
    member_a: bool
    member_b: bool
    theme: str
    type: str
    label: str
    why: str
    uncertain: str
    evidence: list[Evidence]


class Pair(BaseModel):
    name_a: str
    name_b: str
    score: float
    basis: str


class Theme(BaseModel):
    theme: str
    companies: list[str]


class StaffView(BaseModel):
    company_count: int
    themes: list[Theme]
    connections: list[ConnectionView]
    other_pairs: list[Pair]


@app.get("/staff")
def staff_view(user: User = Depends(staff)) -> StaffView:
    profiles = {c.id: load_profile(c.id) for c in load_companies()}
    profiles = {k: v for k, v in profiles.items() if v}
    judged = live(profiles)

    def evidence(cid: str, item_id: str) -> Evidence:
        p = profiles[cid]
        item = next(i for i in p.items if i.id == item_id)
        page = next((pg for pg in p.pages if pg.id == item.source_page_id), None)
        return Evidence(company_id=cid, company=p.company.name, field=FIELD_LABELS.get(item.field, item.field),
                        value=item.value, url=page.url if page else None,
                        retrieved_at=page.retrieved_at if page else None)

    themes = defaultdict(set)
    views = []
    for j in judged:
        c = j.connection
        a, b = profiles[c.company_a].company, profiles[c.company_b].company
        themes[j.theme] |= {a.name, b.name}
        views.append(ConnectionView(
            company_a=a.id, company_b=b.id, name_a=a.name, name_b=b.name, members=a.is_member and b.is_member,
            member_a=a.is_member, member_b=b.is_member, theme=j.theme, type=c.type.replace("_", " "),
            label=c.label, why=j.why, uncertain=j.uncertain,
            evidence=[e for x in c.basis for e in (evidence(a.id, x.item_a_id), evidence(b.id, x.item_b_id))]))
    pairs = {(j.connection.company_a, j.connection.company_b) for j in judged}
    rest = [s for s in rank_connections([(p.company, p.items) for p in profiles.values()])
            if (s.connection.company_a, s.connection.company_b) not in pairs][:20]
    return StaffView(
        company_count=len(profiles),
        themes=[Theme(theme=t, companies=sorted(n)) for t, n in sorted(themes.items(), key=lambda t: -len(t[1]))],
        connections=views,
        other_pairs=[Pair(name_a=s.names[0], name_b=s.names[1], score=round(s.breakdown["final"], 2),
                          basis=s.connection.basis[0].text if s.connection.basis else "") for s in rest])


@app.get("/graph")
def graph(user: User = Depends(staff)) -> Graph:
    """Knowledge graph of park members and external companies. Staff only, public items only."""
    return knowledge_graph({c.id: load_profile(c.id) for c in load_companies()})
