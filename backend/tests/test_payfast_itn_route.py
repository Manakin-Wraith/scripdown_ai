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


def _pass_all(monkeypatch, calls):
    """
    calls collects (charge_type, user_id, quantity) tuples appended by the
    mocked _claim_and_grant, standing in for what the real RPC call would
    have granted. Default: 'granted'.
    """
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: True)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: True)
    monkeypatch.setattr(pr, "_load_intent", lambda m: _intent())
    monkeypatch.setattr(pr, "_already_processed", lambda pf: False)

    def _fake_claim_and_grant(txn_id, pf_payment_id, payload, charge_type,
                               user_id, quantity, payfast_token, billing_cycle):
        calls.append((charge_type, user_id, quantity))
        return 'granted'

    monkeypatch.setattr(pr, "_claim_and_grant", _fake_claim_and_grant)


def _post(form=None):
    body = {'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
            'amount_gross': '450.00', 'payment_status': 'COMPLETE'}
    if form:
        body.update(form)
    return _client().post("/api/payfast/notify", data=body)


def test_valid_itn_grants_credits(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    resp = _post()
    assert resp.status_code == 200
    assert calls == [('tier_1_credits', 'u1', 1)]


def test_bad_signature_grants_nothing(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: False)
    resp = _post()
    assert resp.status_code == 200      # always 200, or PayFast retries forever
    assert calls == []                  # but nothing granted


def test_failed_confirmation_grants_nothing(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: False)
    _post()
    assert calls == []


def test_unknown_intent_grants_nothing(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_load_intent", lambda m: None)
    _post()
    assert calls == []


def test_amount_mismatch_grants_nothing(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    _post({'amount_gross': '1.00'})     # tampered
    assert calls == []


def test_replay_is_idempotent(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_already_processed", lambda pf: True)
    _post()
    assert calls == []


def test_query_param_cannot_override_the_intent(monkeypatch):
    # The endpoint is public. ?type=tier_2_license must NOT grant a licence
    # when the intent says credits.
    calls = []
    _pass_all(monkeypatch, calls)
    _client().post("/api/payfast/notify?type=tier_2_license",
                   data={'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
                         'amount_gross': '450.00', 'payment_status': 'COMPLETE'})
    assert calls == [('tier_1_credits', 'u1', 1)]     # intent wins


def test_custom_str2_cannot_override_the_intent(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    _post({'custom_str2': 'tier_2_license'})
    assert calls == [('tier_1_credits', 'u1', 1)]


def test_seats_grant_uses_intent_quantity(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='tier_2_seats',
                                          expected_amount='1000.00', quantity=4))
    _post({'amount_gross': '1000.00', 'custom_int1': '99'})   # lying client
    assert calls == [('tier_2_seats', 'u1', 4)]       # intent quantity, not custom_int1


def test_non_complete_status_grants_nothing(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    _post({'payment_status': 'FAILED'})
    assert calls == []


def test_losing_a_concurrent_claim_grants_nothing(monkeypatch):
    # Two ITNs for the same payment can both pass _already_processed before
    # either writes. payfast_claim_and_grant (migration 043) is what
    # actually prevents a double grant: it returns 'duplicate' for the
    # loser, at the database layer -- verified directly against a real
    # Postgres in the payfast-atomic-claim-grant design's pre-deploy
    # check, not here. Here we only confirm Python's response to a
    # 'duplicate' result.
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_claim_and_grant", lambda *a, **k: 'duplicate')
    resp = _post()
    assert resp.status_code == 200
    assert calls == []


def test_grant_failure_still_returns_200(monkeypatch):
    # If the RPC call raises (DB-side failure), the function's own
    # exception has already rolled back any partial writes, including
    # the claim (migration 043) -- there is nothing to release here.
    # This only verifies the failure doesn't propagate as a 500 and no
    # partial grant occurs. Per this module's docstring, the 200 returned
    # here does NOT mean "PayFast will retry" -- a 200 is what tells
    # PayFast to stop. The real retry protection this atomic fix provides
    # is for the crash path (no HTTP response at all, so PayFast's own
    # timeout/retry logic eventually resends and finds the row rolled
    # back to 'pending'). This caught-exception path is different: it's
    # a genuine application-level failure, and returning 200 here is a
    # deliberate choice to avoid a PayFast retry storm -- but it means
    # this attempt is a lost grant unless someone intervenes manually or
    # PayFast happens to redeliver the same ITN for unrelated reasons.
    calls = []
    _pass_all(monkeypatch, calls)

    def _boom(*a, **k):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(pr, "_claim_and_grant", _boom)
    resp = _post()
    assert resp.status_code == 200      # no 500 propagates; not a "retry signal"
    assert calls == []


def test_unknown_charge_type_is_rejected_without_claiming(monkeypatch):
    claimed = []
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='free_stuff'))
    monkeypatch.setattr(pr, "_claim_and_grant",
                        lambda *a, **k: claimed.append(1) or 'granted')
    _post()
    assert calls == []
    assert claimed == []                # validated before the row is touched
