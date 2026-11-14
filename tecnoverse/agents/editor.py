"""Profile edits by the company: confirm, correct, add, remove items and set priorities.

Rules (CLAUDE.md, README "Status rules"):
- Confirming keeps the source and quote and sets status user_confirmed.
- Correcting never deletes: the original becomes user_removed and a new user_confirmed item points
  back to it with replaces_item_id.
- Items a user adds or corrects are private by default.
- Every edit bumps profile_version and re-runs the matcher, so the dashboard re-ranks at once.
"""
import hashlib
from datetime import datetime, timezone

from agents.matcher import match_company
from core.schemas import ProfileItem
from core.store import Profile, load_profile, save_profile

PRIORITY_TYPES = ("funding", "event", "testbed")


def _now():
    return datetime.now(timezone.utc)


def _save(profile: Profile, user_id: str):
    profile.company = profile.company.model_copy(update={"profile_version": profile.company.profile_version + 1})
    save_profile(profile)
    return match_company(profile.company.id)


def _find(profile: Profile, item_id: str) -> ProfileItem:
    return next(i for i in profile.items if i.id == item_id)


def confirm(company_id: str, item_id: str, user_id: str):
    p = load_profile(company_id)
    i = _find(p, item_id)
    i.status, i.edited_by, i.updated_at, i.uncertain = "user_confirmed", user_id, _now(), False
    return _save(p, user_id)


def remove(company_id: str, item_id: str, user_id: str):
    p = load_profile(company_id)
    i = _find(p, item_id)
    i.status, i.edited_by, i.updated_at = "user_removed", user_id, _now()
    return _save(p, user_id)


def add(company_id: str, field: str, value: str, user_id: str, replaces: str | None = None):
    value = value.strip()
    if not value:
        raise ValueError("empty value")
    p = load_profile(company_id)
    p.items = [i for i in p.items if not (i.field == field and i.status == "missing")]
    item_id = hashlib.sha1(f"{company_id}|{field}|{value}|user".encode("utf-8")).hexdigest()[:16]
    p.items.append(ProfileItem(id=item_id, company_id=company_id, field=field, value=value,
                               status="user_confirmed", confidence=1.0, visibility="private",
                               created_by="user", edited_by=user_id, replaces_item_id=replaces,
                               updated_at=_now()))
    return _save(p, user_id)


def correct(company_id: str, item_id: str, new_value: str, user_id: str):
    p = load_profile(company_id)
    old = _find(p, item_id)
    old.status, old.edited_by, old.updated_at = "user_removed", user_id, _now()
    save_profile(p)
    return add(company_id, old.field, new_value, user_id, replaces=item_id)


def set_priorities(company_id: str, types: list[str], user_id: str):
    p = load_profile(company_id)
    p.company = p.company.model_copy(update={"priority_types": [t for t in PRIORITY_TYPES if t in types]})
    return _save(p, user_id)


def keep_user_edits(old: Profile | None, new: Profile) -> Profile:
    """For a re-crawl: user-confirmed and user-removed items and priorities survive; the crawl only adds.

    A re-crawled item whose value the user removed or corrected is not added back. A crawled item
    that now contradicts nothing is kept as usual. (A finer 'needs_review' check is left for later.)
    """
    if old is None:
        return new
    user_items = [i for i in old.items if i.status in ("user_confirmed", "user_removed")]
    blocked = {(i.field, i.value.strip().lower()) for i in user_items}
    kept = [i for i in new.items if (i.field, i.value.strip().lower()) not in blocked]
    have_field = {i.field for i in user_items if i.status == "user_confirmed"}
    kept = [i for i in kept if not (i.status == "missing" and i.field in have_field)]
    new.items = kept + user_items
    new.company = new.company.model_copy(update={"priority_types": old.company.priority_types})
    return new


if __name__ == "__main__":  # self-check, no network: cd tecnoverse && python -m agents.editor
    from core.schemas import Company
    c = Company(id="acme", name="Acme", website="https://acme.se/", priority_types=["testbed"])
    t = _now()
    mk = lambda id, f, v, s: ProfileItem(id=id, company_id="acme", field=f, value=v, status=s, updated_at=t)
    old = Profile(company=c, pages=[], items=[mk("1", "application_area", "Pumps", "user_removed"),
                                              mk("2", "application_area", "Wind turbines", "user_confirmed")])
    new = Profile(company=c.model_copy(update={"priority_types": []}), pages=[],
                  items=[mk("3", "application_area", "pumps", "fact"), mk("4", "market", "Energy", "fact")])
    merged = keep_user_edits(old, new)
    assert {i.id for i in merged.items} == {"1", "2", "4"}, [i.id for i in merged.items]  # removed value not re-added
    assert merged.company.priority_types == ["testbed"]
    print("ok")
