"""Contacts/locations attached to a production are shared with its admins."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.contact_service as cs
import services.location_service as ls
import services.production_location_service as pls
import services.production_sharing  # noqa: F401
from test_production_member_routes import MockSupabase

OWNER, ADMIN_A, ADMIN_B, OUTSIDER = "owner", "adminA", "adminB", "outsider"


def _store():
    return {
        "productions": [{"id": "p1", "owner_id": OWNER}, {"id": "p2", "owner_id": OWNER}],
        "production_members": [
            {"production_id": "p1", "user_id": ADMIN_A, "role": "admin"},
            {"production_id": "p1", "user_id": ADMIN_B, "role": "admin"},
            {"production_id": "p1", "user_id": OUTSIDER, "role": "viewer"},
        ],
        # cA: A's contact on p1 crew.  cA2: A's private, unattached.
        # cP2: owner's contact only on p2 crew.
        "contacts": [
            {"id": "cA", "owner_id": ADMIN_A, "name": "Josh", "kind": "person"},
            {"id": "cA2", "owner_id": ADMIN_A, "name": "Private", "kind": "person"},
            {"id": "cP2", "owner_id": OWNER, "name": "OtherProd", "kind": "person"},
        ],
        "production_crew": [
            {"id": "w1", "production_id": "p1", "contact_id": "cA"},
            {"id": "w2", "production_id": "p2", "contact_id": "cP2"},
        ],
        "locations": [
            {"id": "lA", "owner_id": ADMIN_A, "name": "Barn"},
            {"id": "lA2", "owner_id": ADMIN_A, "name": "Secret"},
        ],
        "production_locations": [{"id": "pl1", "production_id": "p1", "location_id": "lA"}],
        "location_photos": [],
    }


def _patch(monkeypatch):
    mock = MockSupabase(_store())
    for mod in (cs, ls, pls):
        monkeypatch.setattr(mod, "get_supabase_admin", lambda: mock)
    return mock


def test_other_admin_can_get_and_update_attached_contact(monkeypatch):
    _patch(monkeypatch)
    assert cs.get_contact_with_usage(ADMIN_B, "cA")["contact"]["name"] == "Josh"
    out = cs.update_contact(ADMIN_B, "cA", {"phone": "123"})
    assert out["phone"] == "123"


def test_unattached_contact_stays_private(monkeypatch):
    _patch(monkeypatch)
    assert cs.get_contact_with_usage(ADMIN_B, "cA2") is cs.NOT_FOUND
    assert cs.update_contact(ADMIN_B, "cA2", {"phone": "1"}) is cs.NOT_FOUND


def test_viewer_and_outsider_cannot_edit_attached_contact(monkeypatch):
    _patch(monkeypatch)
    assert cs.update_contact(OUTSIDER, "cA", {"phone": "1"}) is cs.NOT_FOUND
    assert cs.update_contact("stranger", "cA", {"phone": "1"}) is cs.NOT_FOUND


def test_list_contacts_pools_production_books_only_when_asked(monkeypatch):
    _patch(monkeypatch)
    assert [c["id"] for c in cs.list_contacts(ADMIN_B)] == []
    got = {c["id"] for c in cs.list_contacts(ADMIN_B, production_id="p1")}
    assert got == {"cA", "cA2", "cP2"}     # pooled: every admin's + the owner's book


def test_list_contacts_production_filter_ignored_for_non_manager(monkeypatch):
    _patch(monkeypatch)
    assert cs.list_contacts(OUTSIDER, production_id="p1") == []


def test_shared_contact_cannot_be_deleted_by_non_owner(monkeypatch):
    _patch(monkeypatch)
    assert cs.delete_contact(ADMIN_B, "cA") == "in_use"


def test_other_admin_can_edit_linked_location_not_unlinked(monkeypatch):
    _patch(monkeypatch)
    assert ls.update_location(ADMIN_B, "lA", {"notes": "n"})["notes"] == "n"
    assert ls.update_location(ADMIN_B, "lA2", {"notes": "n"}) is ls.NOT_FOUND


def test_list_locations_includes_linked_for_production(monkeypatch):
    _patch(monkeypatch)
    assert {l["id"] for l in ls.list_locations(ADMIN_B, production_id="p1")} == {"lA", "lA2"}
    assert ls.list_locations(ADMIN_B) == []


def test_link_location_accepts_actors_own_location(monkeypatch):
    _patch(monkeypatch)
    out = pls.link_location("p1", "lA2", OWNER, actor_id=ADMIN_A)
    assert out["location_id"] == "lA2"
    assert pls.link_location("p1", "lA2", OWNER, actor_id=ADMIN_B) == "exists"
    assert pls.link_location("p1", "lZZ", OWNER, actor_id=ADMIN_B) == "not_owned"


def test_pooled_list_includes_every_admins_book_but_not_outsiders(monkeypatch):
    mock = _patch(monkeypatch)
    mock.store["contacts"].append({"id": "cB", "owner_id": ADMIN_B, "name": "Bee", "kind": "person"})
    mock.store["contacts"].append({"id": "cX", "owner_id": "stranger", "name": "No", "kind": "person"})
    got = {c["id"] for c in cs.list_contacts(ADMIN_B, production_id="p1")}
    assert got == {"cA", "cA2", "cB", "cP2"}   # admins' + owner's books; strangers not
    assert cs.list_contacts(OUTSIDER, production_id="p1") == []


def test_pooled_locations(monkeypatch):
    _patch(monkeypatch)
    got = {l["id"] for l in ls.list_locations(ADMIN_B, production_id="p1")}
    assert got == {"lA", "lA2"}


def test_add_crew_accepts_fellow_admins_contact(monkeypatch):
    import services.production_crew_service as pcs
    mock = _patch(monkeypatch)
    monkeypatch.setattr(pcs, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("services.production_service.get_production_owner_id", lambda pid: OWNER)
    out = pcs.add_crew("p1", ADMIN_B, {"contact_id": "cA2", "role": "Gaffer"})
    assert out["contact_id"] == "cA2"
    assert pcs.add_crew("p1", ADMIN_B, {"contact_id": "nope"}) == "bad_contact"


def test_link_location_accepts_fellow_admins_location(monkeypatch):
    _patch(monkeypatch)
    assert pls.link_location("p1", "lA2", OWNER, actor_id=ADMIN_B)["location_id"] == "lA2"
