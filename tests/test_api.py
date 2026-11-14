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


def test_graph_is_staff_only_and_public():
    assert client.get("/graph", headers=EMB).status_code == 403
    assert client.get("/graph", headers={"X-User-Id": "guest"}).status_code == 403
    g = client.get("/graph", headers={"X-User-Id": "staff"}).json()
    kinds = {e["kind"] for e in g["edges"]}
    assert kinds == {"member", "area", "collaboration", "suggestion"}
    for n in g["nodes"]:
        if n["kind"] == "company":
            items = load_profile(n["id"]).items
            for f in n["facts"]:
                assert any(i.value == f["value"] and i.visibility == "public" for i in items)


def test_chats_are_private_and_stored(monkeypatch, tmp_path):
    import shutil
    import agents.assistant as assistant
    import api
    import core.store as store
    for cid in ("embeddedart", "kiwa"):  # profiles only; nothing is written to the real cache
        shutil.copytree(store.CACHE / cid, tmp_path / cid, ignore=shutil.ignore_patterns("*.html", "pages.json", "chats.json"))
    monkeypatch.setattr(store, "CACHE", tmp_path)
    monkeypatch.setattr(api, "reply", lambda m, h, c, s=None: assistant.Reply(label="in_scope", text=f"seen {len(h)} turns"))
    first = client.post("/chat", json={"message": "Which funding fits us?"}, headers=EMB).json()
    again = client.post("/chat", json={"message": "And events?", "session_id": first["session_id"]}, headers=EMB).json()
    assert again["text"] == "seen 2 turns"  # history comes from the stored conversation
    assert [s["session_id"] for s in client.get("/chats", headers=EMB).json()] == [first["session_id"]]
    kiwa = {"X-User-Id": "rep-kiwa"}
    assert client.get("/chats", headers=kiwa).json() == []
    assert client.get(f"/chats/{first['session_id']}", headers=kiwa).status_code == 404
    assert client.post("/chat", json={"message": "hi", "session_id": first["session_id"]}, headers=kiwa).status_code == 404


def test_private_item_leaves_staff_views(monkeypatch, tmp_path):
    import shutil
    import core.store as store
    for c in store.load_companies():
        shutil.copytree(store.CACHE / c.id, tmp_path / c.id, ignore=shutil.ignore_patterns("*.html", "pages.json", "chats.json"))
    monkeypatch.setattr(store, "CACHE", tmp_path)
    staff = {"X-User-Id": "staff"}
    before = client.get("/staff", headers=staff).json()["connections"]
    kiwa_item = next(e for c in before for e in c["evidence"] if e["company_id"] == "kiwa")
    item_id = next(i.id for i in store.load_profile("kiwa").items if i.value == kiwa_item["value"])
    r = client.post(f"/profile/items/{item_id}/visibility", json={"visibility": "private"}, headers={"X-User-Id": "rep-kiwa"})
    assert r.status_code == 200
    after = client.get("/staff", headers=staff).json()["connections"]
    assert len(after) == len(before) - 1 and all(e["value"] != kiwa_item["value"] for c in after for e in c["evidence"])
    assert client.post(f"/profile/items/{item_id}/visibility", json={"visibility": "public"}, headers=EMB).status_code == 404


def test_staff_chat_about_a_company(monkeypatch, tmp_path):
    import shutil
    import agents.assistant as assistant
    import api
    import core.store as store
    for c in store.load_companies():
        shutil.copytree(store.CACHE / c.id, tmp_path / c.id, ignore=shutil.ignore_patterns("*.html", "pages.json", "chats.json"))
    monkeypatch.setattr(store, "CACHE", tmp_path)
    seen = {}
    monkeypatch.setattr(api, "reply", lambda m, h, c, s=None: (seen.update(subject=s), assistant.Reply(label="in_scope", text="ok"))[1])
    staff = {"X-User-Id": "staff"}
    r = client.post("/chat", json={"message": "What does Kiwa do?", "company_id": "kiwa"}, headers=staff).json()
    client.post("/chat", json={"message": "And its matches?", "session_id": r["session_id"]}, headers=staff)
    assert seen["subject"] == "kiwa"  # the follow-up keeps the company from the stored conversation
    assert client.get("/chats", headers=staff).json()[0]["company"] == {"id": "kiwa", "name": "Kiwa"}
    assert client.post("/chat", json={"message": "hi", "company_id": "kiwa"}, headers=EMB).status_code == 403
    # private items never reach the context, public ones do
    p = store.load_profile("kiwa")
    public, private = p.items[0], next(i for i in p.items[1:] if i.value)
    private.visibility = "private"
    store.save_profile(p)
    ctx = assistant._subject("kiwa", {})
    assert public.value in ctx or public.visibility != "public"
    assert private.value not in ctx
