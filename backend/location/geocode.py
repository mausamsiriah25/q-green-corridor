"""
Thin, optional proxy to the Google Geocoding API.

This is ONLY used if GOOGLE_MAPS_API_KEY is set as a *server-side*
environment variable. It exists for deployments that would rather keep
the Maps key off the browser entirely (see README "Google Maps setup"
-> "server-side key" option). The default/simplest setup instead uses
a browser-restricted key with the Places Autocomplete widget directly
in the frontend (frontend/src/services/googleMaps.js) -- this file is
not required for that path.

Every function degrades gracefully: if no key is configured, or the
request fails, callers get {"available": False, ...} back instead of
an exception, so a missing/invalid key never breaks the prototype.
"""
import json
import os
import urllib.parse
import urllib.request

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def _api_key() -> str:
    # read lazily (not at import time) so a .env file loaded by main.py
    # after this module is imported is still picked up
    return os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()


def is_configured() -> bool:
    return bool(_api_key())


def _get(params: dict) -> dict:
    params = {**params, "key": _api_key()}
    url = f"{GEOCODE_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network/DNS/timeout -- never crash the demo
        return {"available": False, "error": str(exc)}

    if data.get("status") != "OK" or not data.get("results"):
        return {"available": False, "error": data.get("status", "NO_RESULTS")}

    result = data["results"][0]
    loc = result["geometry"]["location"]
    return {
        "available": True,
        "address": result.get("formatted_address"),
        "lat": loc["lat"],
        "lon": loc["lng"],
    }


def geocode_address(address: str) -> dict:
    if not is_configured():
        return {"available": False, "error": "GOOGLE_MAPS_API_KEY not configured on the server"}
    return _get({"address": address})


def reverse_geocode(lat: float, lon: float) -> dict:
    if not is_configured():
        return {"available": False, "error": "GOOGLE_MAPS_API_KEY not configured on the server"}
    return _get({"latlng": f"{lat},{lon}"})
