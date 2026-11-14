"""Local JSON snapshots of profiles in data/cache/<company_id>/profile.json.

Page text is kept out of profile.json and stored next to it in pages.json, which is gitignored:
the repo is public and the text is other companies' web content. profile.json keeps each page's
URL, title, date and hash, and every quote used as evidence.

Interim storage until the Firebase layer exists; afterwards it stays as the offline demo fallback.
Keep these two function signatures when swapping the backend.
"""
import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from core.schemas import Company, ProfileItem, SourcePage

DATA = Path(__file__).parent.parent / "data"
CACHE = DATA / "cache"


class Profile(BaseModel):
    company: Company
    pages: list[SourcePage]
    items: list[ProfileItem]
    extracted_by: str = "TecnoVerse Profiler (Gemini)"  # who read the pages; shown on the Profile page


def load_companies() -> list[Company]:
    return [Company(**c) for c in json.loads((DATA / "companies.json").read_text(encoding="utf-8"))]


def save_profile(profile: Profile) -> None:
    save_pages(profile.company.id, profile.pages)
    shareable = profile.model_copy(update={"pages": [p.model_copy(update={"text": ""}) for p in profile.pages]})
    path = CACHE / profile.company.id / "profile.json"
    path.write_text(shareable.model_dump_json(indent=1), encoding="utf-8")


def save_pages(company_id: str, pages: list[SourcePage]) -> None:
    path = CACHE / company_id / "pages.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TypeAdapter(list[SourcePage]).dump_json(pages, indent=1).decode("utf-8"), encoding="utf-8")


def load_pages(company_id: str) -> list[SourcePage]:
    path = CACHE / company_id / "pages.json"
    return TypeAdapter(list[SourcePage]).validate_json(path.read_text(encoding="utf-8")) if path.exists() else []


def load_profile(company_id: str) -> Profile | None:
    """Text is re-attached from pages.json when it exists locally; otherwise pages have text "" (re-crawl to get it)."""
    path = CACHE / company_id / "profile.json"
    if not path.exists():
        return None
    profile = Profile.model_validate_json(path.read_text(encoding="utf-8"))
    texts = {p.id: p.text for p in load_pages(company_id)}
    profile.pages = [p.model_copy(update={"text": p.text or texts.get(p.id, "")}) for p in profile.pages]
    return profile
