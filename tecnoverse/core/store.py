"""Local JSON snapshots of profiles in data/cache/<company_id>/profile.json.

Interim storage until the Firebase layer exists; afterwards it stays as the offline demo fallback.
Keep these two function signatures when swapping the backend.
"""
from pathlib import Path

from pydantic import BaseModel

from core.schemas import Company, ProfileItem, SourcePage

CACHE = Path(__file__).parent.parent / "data" / "cache"


class Profile(BaseModel):
    company: Company
    pages: list[SourcePage]
    items: list[ProfileItem]


def save_profile(profile: Profile) -> None:
    path = CACHE / profile.company.id / "profile.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.model_dump_json(indent=1), encoding="utf-8")


def load_profile(company_id: str) -> Profile | None:
    path = CACHE / company_id / "profile.json"
    return Profile.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None
