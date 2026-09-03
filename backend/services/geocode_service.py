# backend/services/geocode_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Thin server-side geocoder (Mapbox Geocoding v6). Never raises; returns
None on any failure so callers can degrade to manual lat/lng entry."""
import os

import requests

_FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"


def geocode(address):
    token = os.getenv("MAPBOX_SECRET_TOKEN")
    if not token or not address or not str(address).strip():
        return None
    try:
        resp = requests.get(
            _FORWARD_URL,
            params={"q": str(address).strip(), "limit": 1, "access_token": token},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        features = resp.json().get("features") or []
        if not features:
            return None
        lng, lat = features[0]["geometry"]["coordinates"][:2]
        return {"lat": float(lat), "lng": float(lng)}
    except Exception:
        return None
