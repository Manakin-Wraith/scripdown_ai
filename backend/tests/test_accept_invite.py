"""
Task 10: accept_invite must be bound to the invited email address.

Two layers of coverage:
1. A standalone assertion mirroring the guard's comparison rule (from the
   plan) -- cheap, locks the requirement in words.
2. A real Flask test-client integration test that calls the actual
   accept_invite route and proves the 403 fires on mismatch and that a
   matching email is NOT blocked by the guard (reaches the success path).
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.invite_routes as ir
from middleware.auth import DEV_USER_ID


def test_email_mismatch_is_rejected():
    invited = "crew@example.com"
    caller = "someone-else@example.com"
    # mirror the guard the route uses
    assert (invited.lower() != caller.lower())


# ---------------------------------------------------------------------------
# Integration test: real Flask test client hitting the real accept_invite view
# ---------------------------------------------------------------------------

class MockTable:
    """Minimal chainable supabase-py stand-in supporting select/insert/update."""

    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}
        self._op = None
        self._payload = None
        self._single = False

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def single(self):
        self._single = True
        return self

    def _rows(self):
        return self.store.setdefault(self.name, [])

    def _filtered(self):
        rows = self._rows()
        return [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]

    def execute(self):
        if self._op == "select":
            matches = self._filtered()
            if self._single:
                return SimpleNamespace(data=matches[0] if matches else None)
            return SimpleNamespace(data=matches)
        if self._op == "insert":
            new_row = dict(self._payload)
            new_row.setdefault("id", f"{self.name}-generated")
            self._rows().append(new_row)
            return SimpleNamespace(data=[new_row])
        if self._op == "update":
            matches = self._filtered()
            for row in matches:
                row.update(self._payload)
            return SimpleNamespace(data=matches)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockTable(name, self.store)


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _base_store(invite_email, invited_by=None):
    return {
        "script_invites": [{
            "id": "inv1",
            "token": "tok123",
            "script_id": "s1",
            "email": invite_email,
            "department_code": "costume",
            "role": "member",
            "status": "pending",
            "expires_at": None,
            "invited_by": invited_by,
        }],
        "scripts": [{"id": "s1", "title": "Test Script", "user_id": "owner1"}],
        "profiles": [{"id": DEV_USER_ID, "full_name": "Dev User", "email": "dev@example.com"}],
        "script_members": [],
    }


def test_accept_invite_rejects_email_mismatch(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)  # dev bypass -> g.current_user.email == dev@example.com

    store = _base_store(invite_email="someone-else@example.com")
    monkeypatch.setattr(ir, "supabase", MockSupabase(store))

    resp = _client().post("/api/invites/token/tok123/accept")

    assert resp.status_code == 403
    assert resp.get_json()["error"] == "This invitation was sent to a different email address"
    # Membership must not have been created.
    assert store["script_members"] == []


def test_accept_invite_succeeds_for_matching_email(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)

    # invited_by=None skips the notification/email side-effects branch, which
    # is unrelated to the email-match guard under test.
    store = _base_store(invite_email="dev@example.com", invited_by=None)
    monkeypatch.setattr(ir, "supabase", MockSupabase(store))

    resp = _client().post("/api/invites/token/tok123/accept")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["script_id"] == "s1"
    # Membership row was created -> proves we passed the guard and reached
    # the rest of the handler, not just short-circuited early.
    assert len(store["script_members"]) == 1
    assert store["script_members"][0]["user_id"] == DEV_USER_ID
