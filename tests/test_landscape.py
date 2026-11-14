import json
from datetime import datetime, timezone

import pytest

from core.landscape import build_map, industries, load_locations, matches_search, public_topics
from core.schemas import Company, ProfileItem, SourcePage
from core.store import Profile, load_companies


def item(field, value, *, status="fact", visibility="public", company_id="example"):
    return ProfileItem(
        id=value, company_id=company_id, field=field, value=value,
        status=status, visibility=visibility, updated_at=datetime.now(timezone.utc),
    )


def test_search_uses_public_capabilities_not_private_or_possible_interests():
    company = Company(id="example", name="Example", website="https://example.com")
    profile = Profile(company=company, pages=[], items=[
        item("industry", "Marine technology", status="inferred"),
        item("offering", "Sensor services"),
        item("offering", "Secret capability", visibility="private"),
        item("possible_interest", "Funding", status="inferred"),
        item("industry", "Removed industry", status="user_removed"),
        item("offering", "Other company's data", company_id="other"),
    ])
    assert matches_search(company, profile, "MARINE")
    assert matches_search(company, profile, "sensor")
    assert not matches_search(company, profile, "secret")
    assert not matches_search(company, profile, "funding")
    assert not matches_search(company, profile, "removed")
    assert not matches_search(company, profile, "other company")
    assert industries(profile) == {"Marine technology"}
    assert len(public_topics(profile)) == 2
    assert matches_search(company, None, "example")


def test_locations_are_unique_and_link_to_current_companies(tmp_path):
    locations = load_locations()
    company_ids = {company.id for company in load_companies()}
    assert set(locations) <= company_ids
    assert all(location.source_quote and location.coordinate_note for location in locations.values())
    assert {location.precision for location in locations.values()} == {"address", "municipality"}

    data = [location.model_dump(mode="json") for location in locations.values()]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps([data[0], data[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate company IDs"):
        load_locations(path)


def test_map_clusters_only_mapped_companies_and_labels_municipality_points():
    locations = load_locations()
    companies = load_companies()
    mapped = next(company for company in companies if company.id == "storegate")
    unknown = next(company for company in companies if company.id not in locations)
    html = build_map([mapped, unknown], locations, {}).get_root().render()

    assert "markerClusterGroup" in html
    assert "maxClusterRadius" in html
    assert "Municipality reference point, not the office" in html
    assert "SIMULATED snapshot" in html
    assert str(locations[mapped.id].source_url) in html
    assert str(locations[mapped.id].retrieved_at) in html
    assert unknown.name not in html


def test_map_escapes_company_names():
    locations = load_locations()
    company = next(company for company in load_companies() if company.id in locations)
    company = company.model_copy(update={"name": '<img src=x onerror="alert(1)">'})
    html = build_map([company], locations, {}).get_root().render()
    assert '<img src=x onerror="alert(1)">' not in html


def test_popup_shows_sourced_public_capabilities_but_not_private_items():
    company = next(company for company in load_companies() if company.id == "afry")
    now = datetime.now(timezone.utc)
    page = SourcePage(
        id="source", company_id=company.id, url="https://example.com/public",
        retrieved_at=now, text="", content_hash="hash",
    )
    public = item("offering", "Public offering", company_id=company.id).model_copy(
        update={"source_page_id": page.id}
    )
    private = item("industry", "Private industry", visibility="private", company_id=company.id).model_copy(
        update={"source_page_id": page.id}
    )
    profile = Profile(company=company, pages=[page], items=[public, private])
    html = build_map([company], load_locations(), {company.id: profile}).get_root().render()
    assert "Public offering" in html
    assert "https://example.com/public" in html
    assert "Private industry" not in html
