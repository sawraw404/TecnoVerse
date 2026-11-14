"""Adapters: turn profiler and monitor output into the inputs the scorer reads.

The scorer (agents/scoring.py) only ever sees ScoringProfile and ScoringOpp. When the profiler's
final output format lands, change `adapt_profile` here and leave the scorer alone.

Today's input is the README schema: Company + list[ProfileItem], and Opportunity.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from core.schemas import Company, Opportunity, ProfileItem

# --- Tunable tables -----------------------------------------------------------------------------

# How much a profile item counts, by status. user_removed and missing are never used.
STATUS_WEIGHTS = {"user_confirmed": 1.0, "fact": 0.8, "inferred": 0.3}
EVIDENCE_STATUSES = {"user_confirmed", "fact"}

# Profile fields that describe what a company does. Used for topic fit.
TOPIC_FIELDS = {"offering", "technology", "expertise", "application_area", "market"}

# Region scope for now: Blekinge only. Keys are normalised (lowercase, no diacritics).
BLEKINGE_MUNICIPALITIES = {
    "karlskrona": "Karlskrona",
    "ronneby": "Ronneby",
    "karlshamn": "Karlshamn",
    "solvesborg": "Sölvesborg",
    "olofstrom": "Olofström",
}
ONLINE_WORDS = ("online", "digital", "webinar", "virtual", "distans", "zoom", "teams")

STOPWORDS = set("""
a an and are as at be by for from in into is it of on or our the their to with we you your
using based via new more other all also its this that these those over under within
och att det som för med till av den ett en är på vi har vår våra de om eller
""".split())


# --- Data the scorer reads ----------------------------------------------------------------------

@dataclass(frozen=True)
class Topic:
    text: str
    tokens: frozenset[str]
    weight: float
    item_id: str
    field: str
    status: str
    public: bool

    @property
    def is_evidence(self) -> bool:
        return self.status in EVIDENCE_STATUSES


@dataclass(frozen=True)
class Region:
    """status: municipality | blekinge | outside | online | national | unknown"""
    status: str
    municipality: str | None = None
    item_id: str | None = None
    text: str = ""


@dataclass
class ScoringProfile:
    company_id: str
    name: str
    is_member: bool
    profile_version: int
    priority_types: list[str]
    topics: list[Topic]
    region: Region          # from all usable geography items (own company's matching)
    public_region: Region   # from public geography items only (company-to-company)

    @property
    def public_topics(self) -> list[Topic]:
        return [t for t in self.topics if t.public]


@dataclass
class ScoringOpp:
    opportunity_id: str
    type: str
    title: str
    url: str
    tokens: frozenset[str]
    region: Region          # where it physically takes place
    online_option: bool     # can be joined online (online or hybrid)
    deadline: date | None
    contact: str | None
    simulated: bool
    requirements: list[str] = field(default_factory=list)


# --- Helpers ------------------------------------------------------------------------------------

def _fold(text: str) -> str:
    """Lowercase and drop Swedish diacritics so 'Sölvesborg' == 'solvesborg'."""
    return text.lower().translate(str.maketrans("åäöéü", "aaoeu"))


def tokens(text: str) -> frozenset[str]:
    """Keyword set for overlap matching. Placeholder until embeddings exist."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", _fold(text)):
        if len(w) < 3 or w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s"):  # crude plural folding: sensors -> sensor
            w = w[:-1]
        out.add(w)
    return frozenset(out)


def locate(text: str) -> Region:
    """Place a free-text location inside Blekinge. Empty text is unknown, never 'outside'."""
    folded = _fold(text)
    if not folded.strip():
        return Region("unknown")
    for key, name in BLEKINGE_MUNICIPALITIES.items():
        if re.search(rf"\b{key}\b", folded):
            return Region("municipality", name, text=text)
    if "blekinge" in folded:
        return Region("blekinge", text=text)
    if any(w in folded for w in ONLINE_WORDS):
        return Region("online", text=text)
    return Region("outside", text=text)


def _company_region(items: list[ProfileItem]) -> Region:
    """Most specific Blekinge location stated in the geography items.

    A company whose geography only says e.g. 'Nordic countries' is 'unknown', not 'outside':
    that line usually describes its market, not where it sits.
    """
    geo = sorted(
        (i for i in items if i.field == "geography" and i.status in STATUS_WEIGHTS and i.value),
        key=lambda i: -STATUS_WEIGHTS[i.status],  # user-confirmed location wins
    )
    best = Region("unknown")
    for item in geo:
        r = locate(item.value)
        if r.status == "municipality":
            return Region("municipality", r.municipality, item.id, item.value)
        if r.status == "blekinge" and best.status == "unknown":
            best = Region("blekinge", None, item.id, item.value)
    return best


# --- Adapters -----------------------------------------------------------------------------------

def adapt_profile(company: Company, items: list[ProfileItem]) -> ScoringProfile:
    """Current profiler output (README schema) -> ScoringProfile. Swap this when the profiler changes."""
    usable = [i for i in items if i.company_id == company.id]
    topics = [
        Topic(text=i.value, tokens=tokens(i.value), weight=STATUS_WEIGHTS[i.status], item_id=i.id,
              field=i.field, status=i.status, public=i.visibility == "public")
        for i in usable
        if i.field in TOPIC_FIELDS and i.status in STATUS_WEIGHTS and i.value.strip() and tokens(i.value)
    ]
    return ScoringProfile(
        company_id=company.id,
        name=company.name,
        is_member=company.is_member,
        profile_version=company.profile_version,
        priority_types=list(company.priority_types),
        topics=topics,
        region=_company_region(usable),
        public_region=_company_region([i for i in usable if i.visibility == "public"]),
    )


def adapt_profile_obj(profile) -> ScoringProfile:
    """For the profiler branch's `Profile(company, pages, items)` object, or anything shaped like it."""
    return adapt_profile(profile.company, profile.items)


def adapt_opportunity(opp: Opportunity) -> ScoringOpp:
    text = " ".join([opp.title, opp.summary, opp.audience or "", " ".join(opp.tags)])
    if opp.location:
        region = locate(opp.location)
    elif opp.format == "online":
        region = Region("online", text="online")
    elif opp.type == "funding":
        region = Region("national")  # calls without a location are open nationally
    else:
        region = Region("unknown")
    return ScoringOpp(
        opportunity_id=opp.id, type=opp.type, title=opp.title, url=opp.url, tokens=tokens(text),
        region=region, online_option=opp.format in ("online", "hybrid") or region.status == "online",
        deadline=opp.deadline or opp.start_date, contact=opp.contact,
        simulated=opp.simulated, requirements=list(opp.requirements),
    )
