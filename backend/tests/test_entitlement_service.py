"""Entitlement is the single source of truth. Decorators must fail CLOSED."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

import pytest
import services.entitlement_service as es


def _profile(plan='tier_1_pay_per_breakdown', status='active', signup_plan=None):
    return {'subscription_plan': plan, 'subscription_status': status,
            'subscription_expires_at': '2099-01-01T00:00:00Z',
            'signup_plan': signup_plan}


def test_tier2_active_can_run_breakdown_with_zero_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'active'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 5)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 2)
    ent = es.get_entitlement('u1')
    assert ent['can_run_breakdown'] is True   # unlimited
    assert ent['can_use_teams'] is True


def test_tier1_needs_a_positive_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)

    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    assert es.get_entitlement('u1')['can_run_breakdown'] is False

    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 2)
    assert es.get_entitlement('u1')['can_run_breakdown'] is True


def test_tier1_never_gets_teams(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 99)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    assert es.get_entitlement('u1')['can_use_teams'] is False


def test_expired_tier2_loses_teams(monkeypatch):
    # Failed renewal: downgrade to tier 1 behaviour, team features read-only.
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'expired'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 3)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 1)
    ent = es.get_entitlement('u1')
    assert ent['can_use_teams'] is False
    assert ent['can_run_breakdown'] is False


def test_unknown_user_fails_closed(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: None)
    ent = es.get_entitlement('ghost')
    assert ent['can_run_breakdown'] is False
    assert ent['can_use_teams'] is False


def test_get_entitlement_includes_signup_plan(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile",
                         lambda uid: _profile('none', 'none', signup_plan='tier_2_annual_team'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    ent = es.get_entitlement('u1')
    assert ent['signup_plan'] == 'tier_2_annual_team'


def test_unknown_user_signup_plan_is_none(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: None)
    ent = es.get_entitlement('ghost')
    assert ent['signup_plan'] is None


def test_consume_is_noop_for_tier2(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'active'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 1)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    called = []
    monkeypatch.setattr(es, "_insert_spend", lambda uid, sid: called.append(sid))
    assert es.consume_breakdown('u1', 's1') is True
    assert called == []   # no ledger write — tier 2 is unlimited


def test_consume_spends_one_credit_for_tier1(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 1)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    # Not already charged, so the spend must proceed. (The brief's original
    # test omitted this monkeypatch, which made consume_breakdown fall
    # through to a real, unmocked _script_already_charged and hit the
    # network — see task-5-report.md.)
    monkeypatch.setattr(es, "_script_already_charged", lambda uid, sid: False)
    called = []
    monkeypatch.setattr(es, "_insert_spend", lambda uid, sid: called.append(sid) or True)
    assert es.consume_breakdown('u1', 's1') is True
    assert called == ['s1']


def test_consume_is_free_when_script_already_charged(monkeypatch):
    # The DB unique index rejects the second spend; that means "already paid", not an error.
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)   # broke, but already paid
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    monkeypatch.setattr(es, "_script_already_charged", lambda uid, sid: True)
    assert es.consume_breakdown('u1', 's1') is True


def test_consume_raises_at_zero_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    monkeypatch.setattr(es, "_script_already_charged", lambda uid, sid: False)
    with pytest.raises(es.InsufficientCredits):
        es.consume_breakdown('u1', 's1')


def test_decorator_fails_closed_with_no_user(monkeypatch):
    # The bug in the OLD decorator: it read g.user_id (never set) and passed everything through.
    from flask import Flask
    app = Flask(__name__)

    monkeypatch.setattr(es, "get_user_id", lambda: None)

    @es.require_team_tier
    def handler():
        return "reached"

    with app.test_request_context('/'):
        resp = handler()
    assert resp[1] == 401       # NOT "reached"


def test_team_decorator_403s_for_tier1(monkeypatch):
    from flask import Flask
    app = Flask(__name__)
    monkeypatch.setattr(es, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(es, "get_entitlement", lambda uid: {'can_use_teams': False})

    @es.require_team_tier
    def handler():
        return "reached"

    with app.test_request_context('/'):
        resp = handler()
    assert resp[1] == 403


class _FakeSeatsAdmin:
    """Routes get_supabase_admin().table(name) calls by table name for
    _fetch_seats_used tests. Each table's canned rows are passed in."""

    def __init__(self, members=None, invites=None, profiles=None,
                 account_seats=None, productions=None, production_members=None,
                 production_invites=None):
        self._data = {
            'script_members': members or [],
            'script_invites': invites or [],
            'profiles': profiles or [],
            'account_seats': account_seats or [],
            'productions': productions or [],
            'production_members': production_members or [],
            'production_invites': production_invites or [],
        }

    def table(self, name):
        return _FakeSeatsQuery(self._data[name])


class _FakeSeatsQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *a, **k):
        return self

    def eq(self, field, value):
        self._filters.append(('eq', field, value))
        return self

    def gt(self, field, value):
        self._filters.append(('gt', field, value))
        return self

    def in_(self, field, values):
        self._filters.append(('in', field, values))
        return self

    def execute(self):
        # Apply all filters to rows. Skip filters if no row has the field
        # (backwards compatibility with old tests that don't include all fields).
        filtered = self._rows
        for op, field, value in self._filters:
            # Check if any row has this field before filtering
            if not any(field in r for r in filtered):
                continue

            if op == 'eq':
                filtered = [r for r in filtered if r.get(field) == value]
            elif op == 'gt':
                filtered = [r for r in filtered if r.get(field) and r.get(field) > value]
            elif op == 'in':
                filtered = [r for r in filtered if r.get(field) in value]

        class Resp:
            data = filtered
        return Resp()


def _future():
    """Return an ISO datetime string in the future for mocking expires_at."""
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()


def _seat_store(profiles=None, account_seats=None, script_members=None,
                script_invites=None, productions=None, production_members=None,
                production_invites=None):
    """Helper to build a mock Supabase admin with all seat-related tables."""
    return _FakeSeatsAdmin(
        members=script_members,
        invites=script_invites,
        profiles=profiles,
        account_seats=account_seats,
        productions=productions,
        production_members=production_members,
        production_invites=production_invites,
    )


def _patch_seats(monkeypatch, store):
    """Helper to patch get_supabase_admin() to return the mock store."""
    monkeypatch.setattr(es, "get_supabase_admin", lambda: store)


def test_fetch_seats_used_dedupes_by_user_not_membership_row(monkeypatch):
    # A single person invited to 3 scripts must consume 1 seat, not 3.
    admin = _FakeSeatsAdmin(members=[
        {'user_id': 'p1'}, {'user_id': 'p1'}, {'user_id': 'p1'},
    ])
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_counts_pending_invite(monkeypatch):
    # A pending (not yet accepted) invite must already reserve a seat.
    admin = _FakeSeatsAdmin(
        members=[],
        invites=[{'email': 'new@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_counts_pending_and_accepted_together(monkeypatch):
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'accepted1'}],
        invites=[{'email': 'pending@x.com'}],
        profiles=[{'id': 'accepted1', 'email': 'accepted1@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 2


def test_fetch_seats_used_dedupes_pending_invite_already_accepted_elsewhere(monkeypatch):
    # Same person: accepted on one script, still has an unrelated pending
    # invite row lingering (e.g. re-invited to a second script under the
    # same owner before the first invite's status caught up). Must count
    # as one seat, not two.
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'jane_id'}],
        invites=[{'email': 'jane@x.com'}],
        profiles=[{'id': 'jane_id', 'email': 'jane@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_fetch_seats_used_email_match_is_case_insensitive(monkeypatch):
    admin = _FakeSeatsAdmin(
        members=[{'user_id': 'jane_id'}],
        invites=[{'email': 'JANE@X.COM'}],
        profiles=[{'id': 'jane_id', 'email': 'jane@x.com'}],
    )
    monkeypatch.setattr(es, "get_supabase_admin", lambda: admin)
    assert es._fetch_seats_used('owner1') == 1


def test_activate_license_handles_leap_day_now(monkeypatch):
    # datetime.now().replace(year=+1) raises ValueError on 29 Feb -> no such day next year.
    leap_day = datetime(2028, 2, 29, 12, 0, 0, tzinfo=timezone.utc)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return leap_day

    monkeypatch.setattr(es, "datetime", FrozenDatetime)

    captured = {}

    class FakeUpdateQuery:
        def eq(self, *a, **k):
            return self
        def execute(self):
            return None

    class FakeInsertQuery:
        def execute(self):
            return None

    class FakeTable:
        def __init__(self, name):
            self.name = name
        def update(self, payload):
            captured['payload'] = payload
            return FakeUpdateQuery()
        def insert(self, payload):
            captured['seats_payload'] = payload
            return FakeInsertQuery()

    class FakeAdmin:
        def table(self, name):
            assert name in ('profiles', 'account_seats')
            return FakeTable(name)

    monkeypatch.setattr(es, "get_supabase_admin", lambda: FakeAdmin())

    # Must not raise. Default cadence is 'annual' (3 included seats), so
    # this also exercises the included-seats account_seats insert.
    es.activate_license('u1', 'txn1')
    assert 'subscription_expires_at' in captured['payload']
    assert captured['seats_payload']['seats_granted'] == 3
    # 'txn1' isn't a real UUID (admin manual-approval reference) -- must
    # not be attached as the FK.
    assert captured['seats_payload']['payfast_transaction_id'] is None


def test_seats_used_counts_production_member(monkeypatch):
    store = _seat_store(
        profiles=[{"id": "owner", "email": "o@x.com"}],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[{"production_id": "p1", "user_id": "u-lp", "role": "admin"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_dedupes_person_across_both_systems(monkeypatch):
    store = _seat_store(
        profiles=[{"id": "u-both", "email": "both@x.com"}],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[{"user_id": "u-both", "invited_by": "owner"}],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[{"production_id": "p1", "user_id": "u-both", "role": "viewer"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_counts_pending_production_invite(monkeypatch):
    store = _seat_store(
        profiles=[],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[],
        production_invites=[{"production_id": "p1", "email": "new@x.com",
                            "status": "pending", "expires_at": _future()}],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_ignores_other_owners_production_members(monkeypatch):
    store = _seat_store(
        profiles=[],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[], script_invites=[],
        productions=[{"id": "p9", "owner_id": "someone-else"}],
        production_members=[{"production_id": "p9", "user_id": "u-x", "role": "admin"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 0
