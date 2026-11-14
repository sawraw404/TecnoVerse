"""Public, sourced company locations and map filtering."""
from datetime import date
from html import escape
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import folium
from folium.plugins import MarkerCluster
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter

from core.schemas import Company, ProfileItem
from core.store import DATA, Profile

LOCATIONS = DATA / "company_locations.json"
SEARCH_FIELDS = {"industry", "offering", "technology", "expertise", "application_area"}
VISIBLE_STATUSES = {"fact", "inferred", "user_confirmed"}


class CompanyLocation(BaseModel):
    company_id: str
    municipality: str
    address: str
    latitude: float = Field(ge=55, le=57)
    longitude: float = Field(ge=14, le=16)
    precision: Literal["address", "municipality"]
    source_url: HttpUrl
    source_quote: str
    retrieved_at: date
    coordinate_source: HttpUrl
    coordinate_note: str


def load_locations(path: Path = LOCATIONS) -> dict[str, CompanyLocation]:
    locations = TypeAdapter(list[CompanyLocation]).validate_json(path.read_text(encoding="utf-8"))
    result = {location.company_id: location for location in locations}
    if len(result) != len(locations):
        raise ValueError("Duplicate company IDs in company_locations.json")
    return result


def public_topics(profile: Profile | None) -> list[ProfileItem]:
    if profile is None:
        return []
    return [
        item for item in profile.items
        if item.company_id == profile.company.id
        and item.field in SEARCH_FIELDS
        and item.visibility == "public"
        and item.status in VISIBLE_STATUSES
        and item.value.strip()
    ]


def matches_search(company: Company, profile: Profile | None, query: str) -> bool:
    query = query.strip().casefold()
    return not query or query in company.name.casefold() or any(
        query in item.value.casefold() for item in public_topics(profile)
    )


def industries(profile: Profile | None) -> set[str]:
    return {item.value for item in public_topics(profile) if item.field == "industry"}


def build_map(
    companies: list[Company], locations: dict[str, CompanyLocation], profiles: dict[str, Profile | None]
) -> folium.Map:
    result = folium.Map(location=[56.20, 15.15], zoom_start=9, tiles="OpenStreetMap")
    cluster = MarkerCluster(name="Company locations", options={"maxClusterRadius": 70}).add_to(result)
    for company in companies:
        location = locations.get(company.id)
        if location is None:
            continue
        source = escape(str(location.source_url), quote=True)
        position = (
            "Municipality reference point, not the office"
            if location.precision == "municipality" else "Approximate address position"
        )
        popup = (
            f"<strong>{escape(company.name)}</strong><br>"
            f"{escape(location.address)}<br>"
            f"<small>{position} · SIMULATED snapshot</small><br>"
            f'<a href="{source}" target="_blank" rel="noopener noreferrer">Location source</a>'
            f" · {location.retrieved_at:%Y-%m-%d}"
        )
        profile = profiles.get(company.id)
        if profile:
            pages = {page.id: page for page in profile.pages if page.company_id == company.id}
            for field, label in (("industry", "Industry"), ("offering", "Offering")):
                for item in public_topics(profile):
                    page = pages.get(item.source_page_id)
                    if item.field != field or not page or urlparse(page.url).scheme not in {"http", "https"}:
                        continue
                    badge = f"{item.status}{', uncertain' if item.uncertain else ''}"
                    popup += (
                        f"<br><br><strong>{label}</strong>: {escape(item.value)} "
                        f"<small>({escape(badge)})</small><br>"
                        f'<a href="{escape(page.url, quote=True)}" target="_blank" '
                        f'rel="noopener noreferrer">Source</a> · {page.retrieved_at:%Y-%m-%d}'
                    )
                    break
        folium.Marker(
            location=[location.latitude, location.longitude],
            tooltip=escape(company.name),
            popup=folium.Popup(popup, max_width=300),
            icon=folium.Icon(
                color="orange" if location.precision == "municipality" else "blue",
                icon="building", prefix="fa",
            ),
        ).add_to(cluster)
    return result
