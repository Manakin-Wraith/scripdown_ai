"""ITN grants entitlement only after full validation, and only from the intent row."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.payfast_routes as pr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _intent(**over):
    base = {'id': 'txn-1', 'user_id': 'u1', 'charge_type': 'tier_1_credits',
            'expected_amount': '450.00', 'quantity': 1, 'status': 'pending'}
    base.update(over)
    return base


def _pass_all(monkeypatch, grants):
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: True)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: True)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: True)
    monkeypatch.setattr(pr, "_load_intent", lambda m: _intent())
    monkeypatch.setattr(pr, "_already_processed", lambda pf: False)
    monkeypatch.setattr(pr, "_claim_intent", lambda *a, **k: True)
    monkeypatch.setattr(pr, "_release_claim", lambda *a, **k: None)
    monkeypatch.setattr(pr, "grant_credits", lambda u, n, t: grants.append(('credits', u, n)))
    monkeypatch.setattr(pr, "activate_license", lambda u, t: grants.append(('license', u)))
    monkeypatch.setattr(pr, "grant_seats", lambda u, n, t: grants.append(('seats', u, n)))


def _post(form=None):
    body = {'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
            'amount_gross': '450.00', 'payment_status': 'COMPLETE'}
    if form:
        body.update(form)
    return _client().post("/api/payfast/notify", data=body)


def test_valid_itn_grants_credits(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    resp = _post()
    assert resp.status_code == 200
    assert grants == [('credits', 'u1', 1)]


def test_bad_signature_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: False)
    resp = _post()
    assert resp.status_code == 200      # always 200, or PayFast retries forever
    assert grants == []                 # but nothing granted


def test_bad_ip_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: False)
    _post()
    assert grants == []


def test_failed_confirmation_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: False)
    _post()
    assert grants == []


def test_unknown_intent_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_load_intent", lambda m: None)
    _post()
    assert grants == []


def test_amount_mismatch_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'amount_gross': '1.00'})     # tampered
    assert grants == []


def test_replay_is_idempotent(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_already_processed", lambda pf: True)
    _post()
    assert grants == []


def test_query_param_cannot_override_the_intent(monkeypatch):
    # The endpoint is public. ?type=tier_2_license must NOT grant a licence
    # when the intent says credits.
    grants = []
    _pass_all(monkeypatch, grants)
    _client().post("/api/payfast/notify?type=tier_2_license",
                   data={'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
                         'amount_gross': '450.00', 'payment_status': 'COMPLETE'})
    assert grants == [('credits', 'u1', 1)]     # intent wins


def test_custom_str2_cannot_override_the_intent(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'custom_str2': 'tier_2_license'})
    assert grants == [('credits', 'u1', 1)]


def test_seats_grant_uses_intent_quantity(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='tier_2_seats',
                                          expected_amount='600.00', quantity=4))
    _post({'amount_gross': '600.00', 'custom_int1': '99'})   # lying client
    assert grants == [('seats', 'u1', 4)]       # intent quantity, not custom_int1


def test_non_complete_status_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'payment_status': 'FAILED'})
    assert grants == []


def test_losing_a_concurrent_claim_grants_nothing(monkeypatch):
    # Two ITNs for the same payment can both pass _already_processed before
    # either writes. The atomic claim is what actually prevents a double
    # grant: the loser gets no row back and must not grant.
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_claim_intent", lambda *a, **k: False)
    resp = _post()
    assert resp.status_code == 200
    assert grants == []


def test_claim_happens_before_granting(monkeypatch):
    # Ordering is the whole point: claiming after granting would leave the
    # double-grant window open.
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_claim_intent",
                        lambda *a, **k: calls.append(('claim',)) or True)
    monkeypatch.setattr(pr, "grant_credits",
                        lambda u, n, t: calls.append(('credits', u, n)))
    _post()
    assert calls == [('claim',), ('credits', 'u1', 1)]


def test_failed_grant_releases_the_claim(monkeypatch):
    # If granting blows up we must hand the row back, or PayFast's retry
    # finds it already 'complete' and the user has paid for nothing.
    released = []
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_release_claim", lambda t: released.append(t))

    def _boom(u, n, t):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(pr, "grant_credits", _boom)
    resp = _post()
    assert resp.status_code == 200      # still 200 — PayFast will retry
    assert released == ['txn-1']


def test_unknown_charge_type_is_rejected_without_claiming(monkeypatch):
    claimed = []
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='free_stuff'))
    monkeypatch.setattr(pr, "_claim_intent",
                        lambda *a, **k: claimed.append(1) or True)
    _post()
    assert grants == []
    assert claimed == []                # validated before the row is touched
