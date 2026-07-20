"""Role-management endpoint: guardrail spec (unit) + real route (integration).

Two complementary test styles are required here:
  1. `_allowed()` — the plan's own local helper, kept as written. It locks
     the intended rule (owner unreachable, no self-elevation) independent
     of any Flask wiring.
  2. `TestUpdateMemberRoleRoute` — hits the actual
     `PATCH /api/scripts/<script_id>/members/<member_id>` route through a
     real Flask test client, proving the guardrails are enforced in the
     real code path (not just re-derived by a duplicate helper).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware.authorization import ROLE_RANK
import routes.invite_routes as ir
import middleware.authorization as authz


# ---------------------------------------------------------------------------
# Style 1: the plan's local helper, kept exactly as specified.
# ---------------------------------------------------------------------------

def _allowed(actor_role, new_role):
    if new_role not in ("viewer", "member", "admin"):
        return False
    return ROLE_RANK[new_role] <= ROLE_RANK[actor_role]


def test_admin_cannot_grant_owner():
    assert _allowed("admin", "owner") is False


def test_admin_cannot_elevate_above_self():
    # This is the only place the in-view rank check
    # (`ROLE_RANK[new_role] > ROLE_RANK[g.script_role]` in
    # update_member_role) gets exercised at all. No live route call can
    # reach it: the route is gated by @require_script_role('admin'), so
    # g.script_role is always 'admin' (rank 3) or 'owner' (rank 4) by the
    # time the view body runs, and `new_role` is capped at 'admin' (rank 3)
    # by the value check above it. There's no combination of an
    # admin-floor-or-higher actor and a viewer/member/admin target where
    # the target outranks the actor. `_allowed()` re-derives the same rule
    # so the logic is still verified, even though the route can't prove it
    # live today -- see the NOTE above the check in invite_routes.py, and
    # TestUpdateMemberRoleRoute.test_member_rank_actor_rejected_by_decorator_before_reaching_rank_check
    # for the route-level test that documents the same gap.
    assert _allowed("admin", "admin") is True
    assert _allowed("member", "admin") is False


def test_valid_downgrade_allowed():
    assert _allowed("admin", "member") is True


# ---------------------------------------------------------------------------
# Style 2: real Flask test-client integration test against the actual route.
# ---------------------------------------------------------------------------

class FakeMemberTable:
    """Minimal chainable stand-in for the script_members query builder,
    supporting the select/eq/limit/execute and update/eq/execute chains
    the route actually uses."""

    def __init__(self, rows):
        self._rows = rows
        self._filters = {}
        self._pending_update = None

    def select(self, *_a, **_k):
        return self

    def update(self, values):
        self._pending_update = values
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _n):
        return self

    def execute(self):
        matches = [r for r in self._rows
                   if all(r.get(k) == v for k, v in self._filters.items())]
        if self._pending_update is not None:
            for r in matches:
                r.update(self._pending_update)
            self._pending_update = None
            self._filters = {}
            return type("Res", (), {"data": matches})()
        self._filters = {}
        return type("Res", (), {"data": matches})()


class FakeSupabase:
    def __init__(self, members):
        self._members = members

    def table(self, name):
        assert name == "script_members", f"unexpected table: {name}"
        return FakeMemberTable(self._members)


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _setup(monkeypatch, actor_role, members):
    """Wire DEV_MODE auth bypass, the caller's script role, and a fake
    script_members table backing the route's DB calls."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ir, "get_user_id", lambda: "actor-1")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: actor_role)
    fake = FakeSupabase(members)
    monkeypatch.setattr(ir, "supabase", fake)
    return fake


class TestUpdateMemberRoleRoute:
    def test_admin_cannot_grant_owner_returns_400(self, monkeypatch):
        # 'owner' isn't a valid `role` value at all, so this is a 400
        # ("Invalid role") raised by the value check -- it never reaches
        # the rank comparison.
        members = [{"id": "m1", "script_id": "s1", "role": "member"}]
        self._setup_and_assert(monkeypatch, "admin", members, "owner", 400)
        assert members[0]["role"] == "member"  # untouched

    def test_valid_downgrade_returns_200_and_persists(self, monkeypatch):
        members = [{"id": "m1", "script_id": "s1", "role": "admin"}]
        resp = self._setup_and_assert(monkeypatch, "admin", members, "member", 200)
        assert resp.get_json()["role"] == "member"
        assert members[0]["role"] == "member"  # persisted

    def test_member_not_found_returns_404(self, monkeypatch):
        members = []
        self._setup_and_assert(monkeypatch, "admin", members, "member", 404)

    def _setup_and_assert(self, monkeypatch, actor_role, members, new_role, expected_status):
        self._setup(monkeypatch, actor_role, members)
        resp = _client().patch(
            "/api/scripts/s1/members/m1",
            json={"role": new_role},
        )
        assert resp.status_code == expected_status, resp.get_json()
        return resp

    @staticmethod
    def _setup(monkeypatch, actor_role, members):
        return _setup(monkeypatch, actor_role, members)

    def test_member_rank_actor_rejected_by_decorator_before_reaching_rank_check(self, monkeypatch):
        # @require_script_role('admin') gates entry; a mere 'member' should
        # never reach the view body at all (403 from the decorator itself).
        #
        # This subsumes what a previous test here
        # (`test_admin_cannot_elevate_above_own_rank_returns_403`, removed)
        # claimed to prove: it set actor_role="member" and asserted a 403,
        # but that 403 always comes from this decorator, not from the
        # in-view `ROLE_RANK[new_role] > ROLE_RANK[g.script_role]` check --
        # a 'member'-rank actor never gets past @require_script_role('admin')
        # to reach that line. The in-view check is unreachable via any live
        # route call today (see the NOTE above it in invite_routes.py and
        # the comment on test_admin_cannot_elevate_above_self above, which
        # is what actually exercises that check's logic in isolation).
        members = [{"id": "m1", "script_id": "s1", "role": "member"}]
        self._setup(monkeypatch, "member", members)
        resp = _client().patch("/api/scripts/s1/members/m1", json={"role": "admin"})
        assert resp.status_code == 403
        assert members[0]["role"] == "member"  # untouched
