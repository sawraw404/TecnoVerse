"""API access rules. No network, no LLM, no writes. Run from the repo root: pytest"""
from fastapi.testclient import TestClient

from api import app
from core.store import load_profile

client = TestClient(app)
EMB = {"X-User-Id": "rep-embeddedart"}


def test_member_reads_only_own_profile():
    r = client.get("/profile", headers=EMB)
    assert r.status_code == 200 and r.json()["company"]["id"] == "embeddedart"
    # there is no way to ask for another company: the id comes from the user, never the request
    assert client.get("/profile?company_id=saab", headers=EMB).json()["company"]["id"] == "embeddedart"


def test_roles():
    assert client.get("/profile", headers={"X-User-Id": "staff"}).status_code == 403
    assert client.get("/profile", headers={"X-User-Id": "nobody"}).status_code == 401
    assert client.get("/staff", headers=EMB).status_code == 403
    assert client.get("/staff", headers={"X-User-Id": "guest"}).status_code == 403
    assert client.post("/feedback", json={"opportunity_id": "x", "kind": "up"},
                       headers={"X-User-Id": "guest"}).status_code == 403


def test_staff_view_uses_public_items_only():
    r = client.get("/staff", headers={"X-User-Id": "staff"})
    assert r.status_code == 200 and r.json()["connections"]
    for c in r.json()["connections"]:
        for e in c["evidence"]:
            item = next(i for i in load_profile(e["company_id"]).items if i.value == e["value"])
            assert item.visibility == "public" and item.status not in ("missing", "user_removed")


def test_dashboard():
    ranked = client.get("/dashboard", headers=EMB).json()
    assert ranked["ranked"] and ranked["top"] and all(c["judged"] for c in ranked["top"])
    guest = client.get("/dashboard", headers={"X-User-Id": "guest"}).json()
    assert not guest["ranked"] and guest["by_type"]["funding"]
