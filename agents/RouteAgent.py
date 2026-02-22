"""
Google Maps Distance Matrix API integration for travel route planning.

Computes walking and transit travel times between consecutive itinerary
locations.  Falls back to realistic mock data when GOOGLE_MAPS_API_KEY
is not set.

Usage (from planning_agent or main):
    from agents.RouteAgent import compute_routes_for_day

    items_with_routes = compute_routes_for_day(items, city)
    # Each item (except the first) gains a 'travel_info' dict.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

log = logging.getLogger(__name__)

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# Simple in-memory cache (origin|dest|mode → result)
_route_cache: dict[str, dict] = {}
_route_cache_lock = threading.Lock()


def _get_gmaps_key() -> str:
    """Read the API key lazily so that dotenv has loaded by the time we need it."""
    return os.getenv("GOOGLE_MAPS_API_KEY", "")


# ---------------------------------------------------------------------------
# Google Maps Distance Matrix API
# ---------------------------------------------------------------------------

def _gmaps_distance_matrix(
    origin: str,
    destination: str,
    mode: str = "walking",
    city: str = "",
) -> Optional[Dict[str, Any]]:
    """Call the Distance Matrix API for a single origin→destination pair.

    Args:
        origin: Place name or address (e.g. "Tokyo Tower")
        destination: Place name or address (e.g. "Senso-ji Temple")
        mode: "walking" or "transit"
        city: City context appended to place names for disambiguation

    Returns:
        dict with {duration_text, duration_value, distance_text, distance_value,
                    transit_details} or None on failure.
    """
    api_key = _get_gmaps_key()
    if not api_key or _requests is None:
        return None

    # Append city for disambiguation if the location doesn't already mention it
    def _qualify(place: str) -> str:
        if city and city.lower() not in place.lower():
            return f"{place}, {city}"
        return place

    origin_q = _qualify(origin)
    dest_q = _qualify(destination)

    cache_key = f"{origin_q}|{dest_q}|{mode}"
    with _route_cache_lock:
        if cache_key in _route_cache:
            return _route_cache[cache_key]

    try:
        params = {
            "origins": origin_q,
            "destinations": dest_q,
            "mode": mode,
            "key": api_key,
        }
        resp = _requests.get(_DISTANCE_MATRIX_URL, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "OK":
            return None

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return None

        result: Dict[str, Any] = {
            "duration_text": element["duration"]["text"],
            "duration_value": element["duration"]["value"],  # seconds
            "distance_text": element["distance"]["text"],
            "distance_value": element["distance"]["value"],  # meters
        }

        # For transit, try to extract line/summary info
        if mode == "transit" and "transit_details" in element:
            td = element["transit_details"]
            result["transit_name"] = td.get("line", {}).get("short_name", "")
            result["transit_vehicle"] = td.get("line", {}).get("vehicle", {}).get("type", "")

        with _route_cache_lock:
            _route_cache[cache_key] = result

        return result

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Mock fallback  —  generates realistic travel estimates
# ---------------------------------------------------------------------------

# Typical walking speed ~5 km/h, transit average ~25 km/h in cities
_TRANSIT_TYPES = ["metro", "bus", "tram", "subway", "light rail"]


def _deterministic_seed(origin: str, destination: str) -> int:
    """Produce a stable seed so mock data is consistent for same pair."""
    h = hashlib.md5(f"{origin}|{destination}".encode()).hexdigest()
    return int(h[:8], 16)


def _mock_route(origin: str, destination: str) -> Dict[str, Any]:
    """Generate plausible mock walking + transit data for two locations."""
    seed = _deterministic_seed(origin, destination)
    rng = random.Random(seed)

    # Random straight-line distance 0.3–5 km
    distance_km = round(rng.uniform(0.3, 5.0), 1)
    distance_m = int(distance_km * 1000)

    # Walking: ~5 km/h → ~12 min/km
    walk_seconds = int(distance_km * 12 * 60)
    walk_minutes = max(1, walk_seconds // 60)

    # Transit: faster but with wait time
    transit_speed_factor = rng.uniform(2.0, 4.0)
    transit_seconds = int(walk_seconds / transit_speed_factor) + rng.randint(120, 360)  # add wait
    transit_minutes = max(2, transit_seconds // 60)

    transit_type = rng.choice(_TRANSIT_TYPES)

    return {
        "walking": {
            "duration_text": f"{walk_minutes} mins",
            "duration_value": walk_seconds,
            "distance_text": f"{distance_km} km",
            "distance_value": distance_m,
        },
        "transit": {
            "duration_text": f"{transit_minutes} mins",
            "duration_value": transit_seconds,
            "distance_text": f"{distance_km} km",
            "distance_value": distance_m,
            "transit_name": transit_type,
        },
    }


# ---------------------------------------------------------------------------
# Core public API
# ---------------------------------------------------------------------------

def _pick_recommendation(
    walking: dict,
    transit: dict,
    travel_prefs: Optional[Dict[str, List[str]]] = None,
) -> tuple[str, str]:
    """Choose the better mode and build a user-friendly display string.

    *travel_prefs* may contain:
        {"avoid": ["walking"], "prefer": ["transit"]}  — or vice-versa.
    Recognised mode tokens: "walking", "transit".

    Returns (recommended_mode, display_string).
    """
    prefs = travel_prefs or {}
    avoid = {m.lower() for m in prefs.get("avoid", [])}
    prefer = {m.lower() for m in prefs.get("prefer", [])}

    walk_secs = walking.get("duration_value", 9999)
    transit_secs = transit.get("duration_value", 9999)
    walk_mins = max(1, walk_secs // 60)
    transit_mins = max(1, transit_secs // 60)
    transit_label = transit.get("transit_name", "transit")

    # --- preference overrides ---------------------------------------------------
    if "walking" in avoid and "transit" not in avoid:
        return "transit", f"🚇 Transit {transit_mins} min ({transit_label})"
    if "transit" in avoid and "walking" not in avoid:
        return "walking", f"🚶 Walk {walk_mins} min"
    if "walking" in prefer:
        return "walking", f"🚶 Walk {walk_mins} min"
    if "transit" in prefer:
        return "transit", f"🚇 Transit {transit_mins} min ({transit_label})"

    # --- default heuristic (no overrides) ----------------------------------------
    if walk_mins <= 15 or walk_secs <= transit_secs:
        return "walking", f"🚶 Walk {walk_mins} min"
    else:
        return "transit", f"🚇 Transit {transit_mins} min ({transit_label})"


def get_route(
    origin: str,
    destination: str,
    city: str = "",
    travel_prefs: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Get walking + transit route info between two locations.

    *travel_prefs*: optional {"avoid": [...], "prefer": [...]} with mode
    tokens like "walking" / "transit".  Passed to ``_pick_recommendation``.

    Tries Google Maps API first, falls back to mock data.
    Returns a dict suitable for storing in itinerary item travel_info:
    {
        "walking": { duration_text, duration_value, distance_text, distance_value },
        "transit": { duration_text, duration_value, distance_text, distance_value, transit_name },
        "recommended": "walking" | "transit",
        "display": "🚶 Walk 12 min" | "🚇 Transit 8 min (metro)",
    }
    """
    # Fetch walking and transit in parallel for speed
    walking = None
    transit = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        fw = pool.submit(_gmaps_distance_matrix, origin, destination, "walking", city)
        ft = pool.submit(_gmaps_distance_matrix, origin, destination, "transit", city)
        walking = fw.result()
        transit = ft.result()

    # Use mock to fill in whichever mode(s) the API didn't return
    if not walking or not transit:
        mock = _mock_route(origin, destination)
        if not walking:
            log.debug("Walking API miss for %s → %s, using mock", origin, destination)
            walking = mock["walking"]
        if not transit:
            log.debug("Transit API miss for %s → %s, using mock", origin, destination)
            transit = mock["transit"]

    rec, display = _pick_recommendation(walking, transit, travel_prefs)
    return {
        "walking": walking,
        "transit": transit,
        "recommended": rec,
        "display": display,
    }


def compute_routes_for_day(
    items: List[Dict[str, Any]],
    city: str = "",
    travel_prefs: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Enrich a day's itinerary items with travel_info between consecutive items.

    The first item gets no travel_info (or an empty dict).
    Each subsequent item gets travel_info showing how to get from the
    previous location to this one.

    Args:
        items: list of itinerary item dicts (must have 'location' or 'title')
        city: city name for disambiguation
        travel_prefs: optional {"avoid": [...], "prefer": [...]} mode prefs

    Returns:
        The same list, mutated in-place (and returned for convenience).
    """
    items[0]["travel_info"] = {}

    # Build list of (index, origin, destination) pairs to look up
    pairs = []
    for i in range(1, len(items)):
        prev = items[i - 1]
        origin = prev.get("location") or prev.get("title", "")
        destination = items[i].get("location") or items[i].get("title", "")
        if origin and destination and origin != destination:
            pairs.append((i, origin, destination))
        else:
            items[i]["travel_info"] = {}

    # Fetch all routes in parallel (max 6 concurrent to be kind to API)
    if pairs:
        with ThreadPoolExecutor(max_workers=min(len(pairs), 6)) as pool:
            futures = {
                pool.submit(get_route, orig, dest, city, travel_prefs): idx
                for idx, orig, dest in pairs
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    items[idx]["travel_info"] = future.result()
                except Exception:
                    log.warning("Route lookup failed for item %d, skipping", idx)
                    items[idx]["travel_info"] = {}

    return items
