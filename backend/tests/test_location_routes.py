# backend/tests/test_location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.location_service as svc
import routes.location_routes as lr  # noqa: F401


def _client():
    from flask import Flask
    from routes.location_routes import locations_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(locations_bp)
    return app.test_client()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    return _client()


def test_list_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/locations").status_code == 401


def test_create_requires_name(client):
    assert client.post("/api/locations", json={}).status_code == 400
    assert client.post("/api/locations", json={"name": "  "}).status_code == 400


def test_create_and_list(client):
    with patch.object(svc, "create_location", return_value={"id": "l1", "name": "Stage 6"}):
        r = client.post("/api/locations", json={"name": "Stage 6"})
    assert r.status_code == 201 and r.get_json()["location"]["name"] == "Stage 6"


def test_get_404(client):
    with patch.object(svc, "get_location_with_usage", return_value=svc.NOT_FOUND):
        assert client.get("/api/locations/nope").status_code == 404


def test_delete_conflict_returns_409_with_used_in(client):
    with patch.object(svc, "delete_location", return_value="in_use"), \
         patch.object(svc, "location_usage",
                      return_value=[{"production_id": "p1", "production_title": "F"}]):
        r = client.delete("/api/locations/l1")
    assert r.status_code == 409 and r.get_json()["used_in"][0]["production_id"] == "p1"


def test_geocode_route_passes_through(client):
    with patch("routes.location_routes.geocode_service.geocode",
               return_value={"lat": 1.0, "lng": 2.0}):
        r = client.post("/api/locations/geocode", json={"address": "1 Main Rd"})
    assert r.get_json() == {"lat": 1.0, "lng": 2.0}


def test_geocode_route_degraded(client):
    with patch("routes.location_routes.geocode_service.geocode", return_value=None):
        r = client.post("/api/locations/geocode", json={"address": "x"})
    assert r.get_json() == {"lat": None, "lng": None}
