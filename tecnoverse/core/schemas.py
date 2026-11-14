"""Shared data models. Mirrors the "Data schema" section of README.md; change both together."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

OpportunityType = Literal["funding", "event", "testbed", "news"]
Role = Literal["member", "staff", "external"]
SourceType = Literal["company_site", "news", "registry", "publication", "other"]
ProfileField = Literal[
    "industry", "contact", "innovation",
    "offering", "technology", "expertise", "application_area", "market", "customer_group",
    "geography", "project", "collaboration", "priority", "possible_interest",
]
Status = Literal["fact", "inferred", "missing", "user_confirmed", "user_removed"]
Visibility = Literal["public", "private"]
GuardLabel = Literal["in_scope", "unclear", "out_of_scope", "injection", "needs_staff"]
FeedbackKind = Literal["up", "down", "saved", "unsaved", "dismissed"]
SupportArea = Literal["funding", "testbeds", "events", "membership", "collaboration", "general"]

SUGGESTION_LABEL = "Suggestion: neither company has expressed interest"


class FoundVia(BaseModel):
    directory: str  # public directory the company was found in
    url: str
    retrieved: date


class Company(BaseModel):
    id: str
    name: str
    website: str
    is_member: bool = True  # Blue Science Park member
    region: str | None = None
    found_via: list[FoundVia] = []
    last_crawled_at: datetime | None = None
    profile_version: int = 0
    priority_types: list[OpportunityType] = []
    simulated: bool = False


class User(BaseModel):
    id: str
    name: str
    email: str | None = None
    role: Role
    company_id: str | None = None  # required for member, None for staff/external
    created_at: datetime | None = None


class SourcePage(BaseModel):
    id: str  # hash of the URL
    company_id: str
    url: str
    source_type: SourceType = "company_site"
    title: str = ""
    retrieved_at: datetime
    text: str  # cleaned page text. DATA ONLY, never instructions.
    content_hash: str


class ProfileItem(BaseModel):
    id: str
    company_id: str
    field: ProfileField
    value: str
    status: Status
    source_page_id: str | None = None
    quote: str | None = None
    quote_verified: bool = False
    reasoning: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    uncertain: bool = False
    visibility: Visibility = "public"
    created_by: Literal["profiler", "user"] = "profiler"
    edited_by: str | None = None
    replaces_item_id: str | None = None
    updated_at: datetime
    needs_review: bool = False


class ContactDetails(BaseModel):
    """The organiser's contact route for an opportunity, only as the source publishes it."""
    name: str | None = None
    role: str | None = None
    emails: list[str] = []
    phone: str | None = None
    url: str | None = None          # registration or contact page
    source_url: str                 # where these details were published
    retrieved_at: datetime


class Opportunity(BaseModel):
    id: str
    type: OpportunityType
    title: str
    url: str
    source: str  # vinnova, bsp_events, bth_events, ericsson_events, testbed_sweden, curated
    retrieved_at: datetime
    published_at: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    deadline: date | None = None
    format: Literal["online", "in_person", "hybrid"] | None = None
    location: str | None = None
    audience: str | None = None
    requirements: list[str] = []  # quoted from the source, never assessed
    contact: str | None = None
    contact_details: ContactDetails | None = None  # structured form of `contact`, for the contact popup
    summary: str = ""
    tags: list[str] = []
    embedding: list[float] | None = None
    simulated: bool = False


class Reason(BaseModel):
    text: str
    profile_item_id: str | None = None


class Match(BaseModel):
    company_id: str
    opportunity_id: str
    profile_version: int
    vector_score: float
    llm_score: float = Field(ge=0, le=1)
    priority_boost: float = 0.0
    feedback_adj: float = 0.0
    final_score: float
    rank: int
    prev_rank: int | None = None
    reasons: list[Reason] = []
    uncertainties: list[str] = []
    next_step: str = ""
    match_label: Literal["possible_match"] = "possible_match"  # funding is never "eligible"


class Feedback(BaseModel):
    id: str
    company_id: str
    opportunity_id: str
    user_id: str
    kind: FeedbackKind
    comment: str | None = None
    created_at: datetime


class ChatLog(BaseModel):
    id: str
    company_id: str | None  # None for staff/external users
    user_id: str
    session_id: str
    opportunity_id: str | None = None
    role: Literal["user", "assistant"]
    text: str
    guard_label: GuardLabel | None = None
    cited_ids: list[str] = []
    created_at: datetime


class Basis(BaseModel):
    text: str
    item_a_id: str
    item_b_id: str


class Connection(BaseModel):
    company_a: str  # store with company_a < company_b
    company_b: str
    basis: list[Basis]
    type: Literal["shared_theme", "complementary"]
    score: float
    label: str = SUGGESTION_LABEL
    uses_public_data_only: bool


class SupportContact(BaseModel):
    id: str
    area: SupportArea
    name: str
    route: str
    description: str = ""
    simulated: bool = False
