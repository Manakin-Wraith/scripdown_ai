# backend/tests/test_geocode_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.geocode_service as gs


def _resp(status=200, json_body=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body or {}
    return m


def test_returns_none_when_key_missing(monkeypatch):
    monkeypatch.delenv("MAPBOX_SECRET_TOKEN", raising=False)
    assert gs.geocode("1 Main Rd, Cape Town") is None


def test_returns_none_for_blank_address(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    assert gs.geocode("   ") is None


def test_parses_coordinates_from_mapbox_v6(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    body = {"features": [{"geometry": {"type": "Point", "coordinates": [18.42, -33.92]}}]}
    with patch("services.geocode_service.requests.get", return_value=_resp(200, body)) as g:
        out = gs.geocode("1 Main Rd, Cape Town")
    assert out == {"lat": -33.92, "lng": 18.42}
    assert g.call_args.kwargs.get("timeout") == 5


def test_returns_none_on_empty_features(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", return_value=_resp(200, {"features": []})):
        assert gs.geocode("nowhere") is None


def test_returns_none_on_http_error(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", return_value=_resp(422, {})):
        assert gs.geocode("x") is None


def test_returns_none_on_exception(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", side_effect=RuntimeError("boom")):
        assert gs.geocode("x") is None
