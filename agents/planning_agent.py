"""
Direct LLM Trip Planner (litellm — no CrewAI overhead)

Replaces the CrewAI multi-agent crew with direct litellm.completion() calls.
Same 5 logical steps, but each is a single LLM call (or no LLM at all for
flights/hotels which are pure API lookups):

  1. Research + City Selection  → 1 LLM call
  2. Flight search              → direct Amadeus / mock (no LLM)
  3. Accommodation search       → direct Amadeus / mock (no LLM)
  4. Itinerary generation       → 1 LLM call  (receives flights + hotels + research)
  5. Validation (optional)      → 1 LLM call

Total: 3 LLM round-trips instead of ~25 with CrewAI's ReAct loops.

The coordination that mattered in the old system is preserved:
  • Research informs city selection (same LLM call).
  • Cities determine which flights/hotels to search (direct API calls).
  • Flight arrival times + hotel locations are passed as context to the
    itinerary generator so it can plan Day 1 around arrival, cluster
    activities near the hotel, etc.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

import litellm

logger = logging.getLogger(__name__)

# Silence litellm's own verbose logging
litellm.suppress_debug_info = True
# Drop params unsupported by the active model (e.g. temperature on gpt-5)
litellm.drop_params = True

# Thread-safe caches — avoid duplicate API calls
_flight_cache: dict[str, list] = {}
_hotel_cache: dict[str, list] = {}
_cache_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Import Amadeus-backed tools from sub-agents.
# ---------------------------------------------------------------------------
try:
    from .FlightAgent import search_flights as _amadeus_flights_tool
    from .AccomAgent import search_hotels as _amadeus_hotels_tool
except ImportError:
    from FlightAgent import search_flights as _amadeus_flights_tool  # type: ignore
    from AccomAgent import search_hotels as _amadeus_hotels_tool  # type: ignore

_amadeus_flights_fn = _amadeus_flights_tool.func
_amadeus_hotels_fn = _amadeus_hotels_tool.func

# Optional: web search tools (kept for travel-guide endpoint in main.py)
_web_search_tools: list = []
try:
    if os.getenv("TAVILY_API_KEY"):
        from crewai_tools import TavilySearchTool
        _web_search_tools.append(TavilySearchTool())
    elif os.getenv("SERPER_API_KEY"):
        from crewai_tools import SerperDevTool
        _web_search_tools.append(SerperDevTool())
except Exception:
    pass

try:
    from crewai_tools import ScrapeWebsiteTool
    _scrape_tool = ScrapeWebsiteTool()
except Exception:
    _scrape_tool = None


# ---------------------------------------------------------------------------
# Direct web search (Tavily / Serper — no CrewAI agent overhead)
# ---------------------------------------------------------------------------

def _web_search(query: str, max_results: int = 5) -> str:
    """Run a web search via Tavily or Serper for real-time destination info.

    Returns a string of search-result snippets, or empty string if
    no search API key is configured.
    """
    # Try Tavily first
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            result = client.search(query, max_results=max_results)
            snippets = []
            for r in result.get("results", []):
                title = r.get("title", "")
                content = r.get("content", "")[:300]
                snippets.append(f"- {title}: {content}")
            if snippets:
                return "\n".join(snippets)
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)

    # Try Serper
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            import requests
            resp = requests.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": max_results},
                headers={"X-API-KEY": serper_key},
                timeout=10,
            )
            data = resp.json()
            snippets = []
            for r in data.get("organic", []):
                title = r.get("title", "")
                snippet_text = r.get("snippet", "")
                snippets.append(f"- {title}: {snippet_text}")
            if snippets:
                return "\n".join(snippets)
        except Exception as exc:
            logger.warning("Serper search failed: %s", exc)

    return ""


def _gather_city_data(cities: list[str]) -> str:
    """Collect structured neighbourhood data for each city.

    Uses get_city_info() which provides SPECIFIC named restaurants, attractions,
    and food stalls grouped by neighbourhood/district.  This data is injected
    into LLM prompts so the model uses real place names instead of hallucinating.
    """
    from mock_data import get_city_info as _gci
    all_data = {}
    for city in cities:
        info = _gci(city)
        if info:
            all_data[city] = info
    if not all_data:
        return ""
    return json.dumps(all_data, indent=2, default=str)


from mock_data import (
    generate_mock_flights,
    generate_mock_accommodations,
    get_city_info,
    get_airport_for_city,
)

try:
    from .RouteAgent import compute_routes_for_day
except ImportError:
    from RouteAgent import compute_routes_for_day  # type: ignore

# ---------------------------------------------------------------------------
# IATA code mappings
# ---------------------------------------------------------------------------

_CITY_TO_AIRPORT: dict[str, str] = {
    "New York": "JFK", "London": "LHR", "Paris": "CDG", "Tokyo": "NRT",
    "Los Angeles": "LAX", "Chicago": "ORD", "Sydney": "SYD", "Dubai": "DXB",
    "Singapore": "SIN", "Bangkok": "BKK", "Barcelona": "BCN", "Rome": "FCO",
    "Amsterdam": "AMS", "Berlin": "BER", "Prague": "PRG", "Istanbul": "IST",
    "San Francisco": "SFO", "Miami": "MIA", "Boston": "BOS", "Kyoto": "KIX",
    "Osaka": "KIX", "Madrid": "MAD", "Lisbon": "LIS", "Vienna": "VIE",
    "Zurich": "ZRH", "Copenhagen": "CPH", "Stockholm": "ARN", "Seoul": "ICN",
    "Munich": "MUC", "Hamburg": "HAM", "Milan": "MXP", "Florence": "FLR",
    "Venice": "VCE", "Naples": "NAP", "Nice": "NCE", "Lyon": "LYS",
    "Seville": "SVQ", "Malaga": "AGP", "Athens": "ATH", "Edinburgh": "EDI",
    "Dublin": "DUB", "Brussels": "BRU", "Helsinki": "HEL", "Oslo": "OSL",
    "Warsaw": "WAW", "Budapest": "BUD", "Bucharest": "OTP", "Zagreb": "ZAG",
    "Marrakech": "RAK", "Cairo": "CAI", "Cape Town": "CPT", "Johannesburg": "JNB",
    "Nairobi": "NBO", "Mumbai": "BOM", "Delhi": "DEL", "Beijing": "PEK",
    "Shanghai": "PVG", "Hong Kong": "HKG", "Taipei": "TPE", "Hanoi": "HAN",
    "Ho Chi Minh City": "SGN", "Bali": "DPS", "Kuala Lumpur": "KUL",
    "Manila": "MNL", "Chiang Mai": "CNX", "Phuket": "HKT",
    "Buenos Aires": "EZE", "Lima": "LIM", "Bogota": "BOG",
    "Mexico City": "MEX", "Cancun": "CUN", "Sao Paulo": "GRU",
    "Rio de Janeiro": "GIG", "Toronto": "YYZ", "Vancouver": "YVR",
    "Montreal": "YUL", "Auckland": "AKL", "Queenstown": "ZQN",
    "Honolulu": "HNL", "Las Vegas": "LAS", "Denver": "DEN",
    "Seattle": "SEA", "Portland": "PDX", "Washington": "IAD",
    "Philadelphia": "PHL", "Atlanta": "ATL", "Dallas": "DFW",
    "Houston": "IAH", "Orlando": "MCO", "San Diego": "SAN",
    "Bath": "BRS",
}

_CITY_TO_IATA_CITY: dict[str, str] = {
    "New York": "NYC", "London": "LON", "Paris": "PAR", "Tokyo": "TYO",
    "Los Angeles": "LAX", "Chicago": "CHI", "Sydney": "SYD", "Dubai": "DXB",
    "Singapore": "SIN", "Bangkok": "BKK", "Barcelona": "BCN", "Rome": "ROM",
    "Amsterdam": "AMS", "Berlin": "BER", "Prague": "PRG", "Istanbul": "IST",
    "San Francisco": "SFO", "Miami": "MIA", "Boston": "BOS", "Kyoto": "OSA",
    "Osaka": "OSA", "Madrid": "MAD", "Lisbon": "LIS", "Vienna": "VIE",
    "Zurich": "ZRH", "Copenhagen": "CPH", "Stockholm": "STO", "Seoul": "SEL",
    "Munich": "MUC", "Hamburg": "HAM", "Milan": "MIL", "Florence": "FLR",
    "Venice": "VCE", "Naples": "NAP", "Nice": "NCE", "Lyon": "LYS",
    "Athens": "ATH", "Edinburgh": "EDI", "Dublin": "DUB",
    "Brussels": "BRU", "Helsinki": "HEL", "Oslo": "OSL",
    "Mumbai": "BOM", "Delhi": "DEL", "Beijing": "BJS",
    "Shanghai": "SHA", "Hong Kong": "HKG", "Taipei": "TPE",
    "Kuala Lumpur": "KUL", "Buenos Aires": "BUE",
    "Mexico City": "MEX", "Sao Paulo": "SAO", "Toronto": "YTO",
    "Montreal": "YMQ",
}

_iata_lookup_cache: dict[str, str] = {}


def _amadeus_location_lookup(city: str, subtype: str = "AIRPORT") -> Optional[str]:
    """Query the Amadeus Locations API for the IATA code of *city*."""
    cache_key = f"{subtype}|{city}"
    if cache_key in _iata_lookup_cache:
        return _iata_lookup_cache[cache_key]

    if not os.getenv("AMADEUS_CLIENT_ID"):
        return None
    try:
        from amadeus import Client, ResponseError
        _am = Client(
            client_id=os.getenv("AMADEUS_CLIENT_ID", ""),
            client_secret=os.getenv("AMADEUS_CLIENT_SECRET", ""),
        )
        resp = _am.reference_data.locations.get(keyword=city, subType=subtype)
        if resp.data:
            code = resp.data[0].get("iataCode", "")
            if code:
                _iata_lookup_cache[cache_key] = code
                return code
    except Exception:
        pass
    return None


def _airport_code(city: str) -> str:
    """Resolve a city name to an IATA airport code."""
    if city in _CITY_TO_AIRPORT:
        return _CITY_TO_AIRPORT[city]
    code = _amadeus_location_lookup(city, "AIRPORT")
    if code:
        _CITY_TO_AIRPORT[city] = code
        return code
    return get_airport_for_city(city)


def _city_iata(city: str) -> str:
    """Resolve a city name to an IATA *city* code (for hotel searches)."""
    if city in _CITY_TO_IATA_CITY:
        return _CITY_TO_IATA_CITY[city]
    code = _amadeus_location_lookup(city, "CITY")
    if code:
        _CITY_TO_IATA_CITY[city] = code
        return code
    apt = _CITY_TO_AIRPORT.get(city)
    if apt:
        return apt
    return city[:3].upper()


def _is_mock_flight(f: dict) -> bool:
    """True when a dict looks like mock-data format."""
    return "flight_type" in f and "airline" in f and "flight_number" in f


def _is_mock_accom(a: dict) -> bool:
    return "name" in a and "price_per_night" in a and "check_in_date" in a


_CARRIER_NAMES: dict[str, str] = {
    "AA": "American Airlines", "DL": "Delta Air Lines", "UA": "United Airlines",
    "LH": "Lufthansa", "BA": "British Airways", "AF": "Air France",
    "KL": "KLM", "EK": "Emirates", "QR": "Qatar Airways",
    "JL": "Japan Airlines", "NH": "ANA", "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific", "AY": "Finnair", "IB": "Iberia",
    "VS": "Virgin Atlantic", "TK": "Turkish Airlines", "LX": "Swiss",
    "OS": "Austrian Airlines", "SK": "SAS", "AZ": "ITA Airways",
    "QF": "Qantas", "AC": "Air Canada", "WN": "Southwest Airlines",
    "B6": "JetBlue", "AS": "Alaska Airlines", "HA": "Hawaiian Airlines",
    "PR": "Philippine Airlines", "MH": "Malaysia Airlines",
    "TG": "Thai Airways", "VN": "Vietnam Airlines", "GA": "Garuda Indonesia",
    "KE": "Korean Air", "OZ": "Asiana Airlines", "CI": "China Airlines",
    "BR": "EVA Air", "CZ": "China Southern", "MU": "China Eastern",
    "CA": "Air China", "EY": "Etihad Airways", "WS": "WestJet",
    "FR": "Ryanair", "U2": "easyJet", "W6": "Wizz Air",
}


def _parse_iso_duration(iso: str) -> int:
    """Convert ISO-8601 duration (e.g. 'PT14H15M') to total minutes."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso or "")
    if not m:
        return 0
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)


def _normalize_amadeus_flights(raw_offers: list[dict], origin_city: str,
                                dest_city: str) -> list[dict]:
    """Convert Amadeus FlightOffer objects into the DB-compatible schema."""
    normalized: list[dict] = []
    for idx, offer in enumerate(raw_offers):
        carriers_dict = offer.get("_carriers", {})
        price_total = float(offer.get("price", {}).get("grandTotal",
                            offer.get("price", {}).get("total", 0)))
        currency = offer.get("price", {}).get("currency", "USD")

        for itin_idx, itin in enumerate(offer.get("itineraries", [])):
            segments = itin.get("segments", [])
            if not segments:
                continue

            first_seg = segments[0]
            last_seg = segments[-1]
            carrier_code = first_seg.get("carrierCode", "")
            airline_name = (carriers_dict.get(carrier_code)
                           or _CARRIER_NAMES.get(carrier_code)
                           or carrier_code)
            flight_number = f"{carrier_code}{first_seg.get('number', '')}"
            from_airport = first_seg.get("departure", {}).get("iataCode", "")
            to_airport = last_seg.get("arrival", {}).get("iataCode", "")
            dep_dt = first_seg.get("departure", {}).get("at", "")
            arr_dt = last_seg.get("arrival", {}).get("at", "")
            duration_min = _parse_iso_duration(itin.get("duration", ""))
            flight_type = "outbound" if itin_idx == 0 else "return"
            booking_url = (
                f"https://www.google.com/travel/flights?q="
                f"{from_airport}+to+{to_airport}+{dep_dt[:10]}"
            )
            normalized.append({
                "id": f"flight_{flight_type}_{idx}",
                "flight_type": flight_type,
                "airline": airline_name,
                "flight_number": flight_number,
                "from_airport": from_airport,
                "to_airport": to_airport,
                "departure_datetime": dep_dt,
                "arrival_datetime": arr_dt,
                "duration_minutes": duration_min,
                "price": round(price_total / max(len(offer.get("itineraries", [1])), 1), 2),
                "currency": currency,
                "booking_url": booking_url,
                "status": "suggested",
            })
    return normalized


def _normalize_amadeus_hotels(raw_hotels: list[dict], city: str,
                               check_in: str, check_out: str) -> list[dict]:
    """Convert Amadeus HotelOffers objects into the DB-compatible schema."""
    from datetime import datetime as _dt
    try:
        nights = (_dt.strptime(check_out, "%Y-%m-%d") - _dt.strptime(check_in, "%Y-%m-%d")).days
    except Exception:
        nights = 1
    nights = max(nights, 1)

    normalized: list[dict] = []
    for idx, hotel_data in enumerate(raw_hotels):
        hotel_info = hotel_data.get("hotel", {})
        offers = hotel_data.get("offers", [])
        if not offers:
            continue
        best_offer = offers[0]

        total_price = float(best_offer.get("price", {}).get("total", 0))
        currency = best_offer.get("price", {}).get("currency", "USD")
        price_per_night = round(total_price / nights, 2)
        name = hotel_info.get("name", f"Hotel in {city}")
        lat = hotel_info.get("latitude")
        lon = hotel_info.get("longitude")
        room_desc = (best_offer.get("room", {}).get("description", {}).get("text", ""))
        amenities = []
        if "wifi" in room_desc.lower() or "internet" in room_desc.lower():
            amenities.append("wifi")
        if best_offer.get("boardType"):
            amenities.append(best_offer["boardType"].lower())

        booking_url = (
            f"https://www.google.com/travel/hotels?q="
            f"{name.replace(' ', '+')}+{city.replace(' ', '+')}"
        )
        normalized.append({
            "id": f"acc_{idx}",
            "name": name,
            "type": "hotel",
            "address": f"{name}, {city}",
            "city": city,
            "check_in_date": best_offer.get("checkInDate", check_in),
            "check_out_date": best_offer.get("checkOutDate", check_out),
            "price_per_night": price_per_night,
            "total_price": round(total_price, 2),
            "currency": currency,
            "rating": None,
            "amenities": amenities,
            "booking_url": booking_url,
            "status": "suggested",
            "_latitude": lat,
            "_longitude": lon,
        })
    return normalized


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COUNTRIES = {
    "Japan", "France", "Italy", "Spain", "Thailand", "Germany", "UK", "USA",
    "Australia", "Brazil", "India", "China", "Mexico", "Greece", "Turkey",
    "Vietnam", "Cambodia", "Malaysia", "Indonesia", "Philippines",
    "Netherlands", "Portugal", "Switzerland", "Austria", "Czech Republic",
    "South Korea", "Morocco", "Egypt", "Argentina", "Colombia", "Peru",
    "New Zealand", "Ireland", "Croatia", "Norway", "Sweden", "Denmark",
    "Finland", "Belgium", "Poland", "Hungary", "Romania",
    "United States", "United Kingdom",
}


def _is_likely_country(destination: str) -> bool:
    return destination.strip() in COUNTRIES


def _safe_json_parse(text: str) -> Any:
    """Extract and parse JSON from an LLM response that may include markdown fences."""
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
    return json.loads(cleaned.strip())


def _calc_duration(start: str, end: str) -> int:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    return (e - s).days + 1


def _gmaps_url(place: str, city: str) -> str:
    """Build a Google Maps search URL for a place in a city."""
    query = f"{place} {city}".replace(" ", "+")
    return f"https://www.google.com/maps/search/{query}"


def _fallback_day_plan(city: str, day_number: int) -> list[dict]:
    return [
        {"start_time": "08:30", "duration_minutes": 60, "title": f"Breakfast in {city}",
         "description": "Start the day with a local breakfast", "item_type": "meal",
         "location": f"{city} city center",
         "google_maps_url": _gmaps_url("breakfast cafe", city),
         "cost_usd": 15, "cost_local": "$15", "currency": "USD", "notes": ""},
        {"start_time": "10:00", "duration_minutes": 150, "title": f"Explore {city}",
         "description": "Walk around the main sights", "item_type": "attraction",
         "location": f"{city} city center",
         "google_maps_url": _gmaps_url("city center", city),
         "cost_usd": 0, "cost_local": "Free", "currency": "USD", "notes": ""},
        {"start_time": "12:30", "duration_minutes": 60, "title": f"Lunch in {city}",
         "description": "Midday meal at a popular spot", "item_type": "meal",
         "location": f"{city} dining district",
         "google_maps_url": _gmaps_url("restaurant", city),
         "cost_usd": 25, "cost_local": "$25", "currency": "USD", "notes": ""},
        {"start_time": "14:00", "duration_minutes": 180, "title": f"{city} main attraction",
         "description": "Visit the city highlight", "item_type": "attraction",
         "location": f"{city} main attraction",
         "google_maps_url": _gmaps_url("top attraction", city),
         "cost_usd": 20, "cost_local": "$20", "currency": "USD", "notes": ""},
        {"start_time": "18:00", "duration_minutes": 90, "title": f"Dinner in {city}",
         "description": "Evening meal", "item_type": "meal",
         "location": f"{city} restaurant district",
         "google_maps_url": _gmaps_url("dinner restaurant", city),
         "cost_usd": 35, "cost_local": "$35", "currency": "USD", "notes": ""},
    ]


# ---------------------------------------------------------------------------
# LLM model helper  (supports OpenAI, Gemini, Claude via LLM_PROVIDER)
# ---------------------------------------------------------------------------

_LLM_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-sonnet-4-20250514",
}


def _llm_name() -> str:
    """Return the litellm model string (provider/model format)."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    if provider not in _LLM_DEFAULTS:
        provider = "openai"
    model = os.getenv("LLM_MODEL", _LLM_DEFAULTS[provider])
    if provider == "openai":
        return model  # litellm uses bare model name for OpenAI
    return f"{provider}/{model}"


# ---------------------------------------------------------------------------
# Core LLM call wrapper
# ---------------------------------------------------------------------------

def _llm_call(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Make a single litellm.completion() call and return the text content.

    One call = one LLM round-trip, no ReAct loops.
    """
    response = litellm.completion(
        model=_llm_name(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Direct tool wrappers (no LLM needed — deterministic API calls)
# ---------------------------------------------------------------------------

def _search_flights_direct(origin: str, destination: str, departure_date: str,
                           return_date: str, num_travelers: int = 1) -> list[dict]:
    """Search flights via Amadeus (or mock fallback). No LLM involved."""
    cache_key = f"flights|{origin.strip().lower()}|{destination.strip().lower()}|{departure_date}|{return_date}|{num_travelers}"
    with _cache_lock:
        cached = _flight_cache.get(cache_key)
    if cached:
        return cached

    origin_code = _airport_code(origin)
    dest_code = _airport_code(destination)
    results = _amadeus_flights_fn(origin_code, dest_code, departure_date, return_date, num_travelers)

    if results and "error" not in results[0]:
        if not _is_mock_flight(results[0]):
            results = _normalize_amadeus_flights(results, origin, destination)
        with _cache_lock:
            _flight_cache[cache_key] = list(results)
        return results

    # Fallback to mock data
    results = generate_mock_flights(origin, destination, departure_date, return_date or None, num_travelers)
    with _cache_lock:
        _flight_cache[cache_key] = list(results)
    return results


def _search_hotels_direct(city: str, check_in: str, check_out: str,
                          num_guests: int = 1) -> list[dict]:
    """Search hotels via Amadeus (or mock fallback). No LLM involved."""
    cache_key = f"hotels|{city.strip().lower()}|{check_in}|{check_out}|{num_guests}"
    with _cache_lock:
        cached = _hotel_cache.get(cache_key)
    if cached:
        return cached

    city_code = _city_iata(city)
    results = _amadeus_hotels_fn(city_code, check_in, check_out, num_guests, "hotel")

    if results and "error" not in results[0]:
        if not _is_mock_accom(results[0]):
            results = _normalize_amadeus_hotels(results, city, check_in, check_out)
        with _cache_lock:
            _hotel_cache[cache_key] = list(results)
        return results

    results = generate_mock_accommodations(city, check_in, check_out, num_guests)
    with _cache_lock:
        _hotel_cache[cache_key] = list(results)
    return results


# ---------------------------------------------------------------------------
# Step 1: Research + City Selection (1 LLM call)
# ---------------------------------------------------------------------------

_RESEARCH_SYSTEM = """\
You are a seasoned travel researcher and city routing expert. You provide \
structured, actionable travel information and select optimal cities for \
multi-city trips. Always respond with valid JSON only — no markdown fences, \
no extra text."""


def _research_and_select_cities(
    dest: str, duration: int, interests: str, budget: str, is_country: bool,
) -> tuple[dict, list[str]]:
    """Run destination research + city selection in one LLM call.

    Enriched with web search (Tavily/Serper) and structured city data
    (neighbourhoods, specific restaurants, attractions from get_city_info).

    Returns (research_dict, list_of_cities).
    """
    # --- Real-time web search enrichment ---
    web_results = _web_search(
        f"{dest} travel guide best things to do {interests} 2026"
    )
    web_context = ""
    if web_results:
        web_context = (
            f"\n\nWEB SEARCH RESULTS (use for current, real information):\n"
            f"{web_results}\n"
        )

    # --- Structured city data with specific named places ---
    city_info = get_city_info(dest)  # works for city-level destinations
    city_data_context = ""
    if city_info and city_info.get("neighbourhoods"):
        city_data_context = (
            f"\n\nSTRUCTURED CITY DATA — use these SPECIFIC restaurants "
            f"and attractions:\n"
            f"{json.dumps(city_info, indent=2, default=str)[:3000]}\n"
        )

    if is_country:
        city_instruction = f"""Also select the best 2-4 cities to visit in {dest} for a \
{duration}-day trip. Order them in a logical route minimising backtracking. \
Include the most popular city. Add a "cities" key with a JSON array of city names."""
    else:
        city_instruction = f"""The destination is the single city "{dest}".
Add a "cities" key with the array ["{dest}"]."""

    prompt = f"""Research the travel destination **{dest}** for a {duration}-day trip.

Traveler interests: {interests}
Budget level: {budget}
{web_context}{city_data_context}
IMPORTANT: Use SPECIFIC named places, restaurants, and attractions — never generic
phrases like "local restaurant" or "popular attraction". If structured city data is
provided above, incorporate those exact restaurant and attraction names.

Return a single JSON object with these keys:
{{
  "overview": "2-3 sentence overview with specific highlights",
  "best_areas": ["Specific Neighbourhood/District 1", "Specific Neighbourhood/District 2"],
  "top_attractions": ["Specific Named Attraction 1", "Specific Named Attraction 2", ...],
  "local_food": ["Specific Restaurant Name — signature dish", ...],
  "transport_tips": "specific transport (metro line names, pass prices, etc.)",
  "safety_notes": "brief safety info",
  "budget_tips": "specific money-saving tips with actual prices",
  "cities": ["City1", "City2", ...]
}}

{city_instruction}

Return ONLY valid JSON."""

    try:
        raw = _llm_call(_RESEARCH_SYSTEM, prompt, temperature=0.5)
        result = _safe_json_parse(raw)
        cities = result.pop("cities", [dest])
        if not isinstance(cities, list) or not cities:
            cities = [dest]
        cities = [str(c) for c in cities[:4]]
        return result, cities
    except Exception as exc:
        logger.warning("Research LLM call failed: %s", exc)
        defaults = {
            "Japan": ["Tokyo", "Kyoto", "Osaka"],
            "France": ["Paris", "Nice", "Lyon"],
            "Italy": ["Rome", "Florence", "Venice"],
            "Spain": ["Barcelona", "Madrid", "Seville"],
            "Thailand": ["Bangkok", "Chiang Mai", "Phuket"],
            "UK": ["London", "Edinburgh", "Bath"],
            "USA": ["New York", "Los Angeles", "San Francisco"],
            "Germany": ["Berlin", "Munich", "Hamburg"],
        }
        cities = defaults.get(dest, [dest]) if is_country else [dest]
        research = {
            "overview": f"A {duration}-day trip to {dest}.",
            "best_areas": [],
            "top_attractions": [],
            "local_food": [],
            "transport_tips": "",
            "safety_notes": "",
            "budget_tips": "",
        }
        return research, cities


# ---------------------------------------------------------------------------
# Step 4: Itinerary Generation (1 LLM call)
#
# This receives the actual flight times + hotel names/locations as context
# so it can plan Day 1 around arrival, cluster activities near hotels, etc.
# ---------------------------------------------------------------------------

_ITINERARY_SYSTEM = """\
You are an expert itinerary designer, local food critic, and city logistics \
planner. Your TOP PRIORITY is geographic efficiency: group activities by \
neighbourhood so travellers walk between consecutive stops. You ALWAYS \
recommend places by name (e.g. 'Ichiran Ramen Shibuya', 'Le Bouillon Chartier'). \
You never use generic phrases like 'find a local restaurant'. You include a \
Google Maps URL for every single location. Always respond with valid JSON only."""


def _normalise_itinerary_items(itinerary: list[dict], dest: str) -> None:
    """Normalise item fields in-place (shared by generate / validate / modify)."""
    for day in itinerary:
        city_name = day.get("city", dest)
        for i, item in enumerate(day.get("items", [])):
            item.setdefault("id", f"day{day.get('day_number', 0)}_item{i}")
            item.setdefault("status", "planned")
            item.setdefault("delayed_to_day", None)
            item.setdefault("is_ai_suggested", 1)
            if "cost_usd" not in item:
                raw_cost = item.pop("cost", 0)
                item["cost_usd"] = raw_cost if isinstance(raw_cost, (int, float)) else 0
            item.setdefault("cost_local", f"${item['cost_usd']}")
            item.setdefault("currency", "USD")
            item["cost"] = item["cost_usd"]
            if not item.get("google_maps_url"):
                loc = item.get("location", item.get("title", city_name))
                item["google_maps_url"] = _gmaps_url(loc, city_name)


def _generate_itinerary(
    dest: str, cities: list[str], duration: int, start: str, end: str,
    travelers: int, interests: str, dietary: str, budget: str,
    research: dict, flights: list[dict], accommodations: list[dict],
) -> list[dict]:
    """Generate the day-by-day itinerary in a single LLM call.

    The prompt includes flight arrival/departure times and hotel locations
    so the LLM can coordinate the itinerary around them.
    """
    # Build compact context from research + flights + hotels + city neighbourhoods
    research_summary = json.dumps(research, default=str)[:2000]
    city_neighbourhood_data = _gather_city_data(cities)
    flight_summary = json.dumps(flights[:5], default=str)[:1500]
    accom_summary = json.dumps([
        {"city": a.get("city"), "name": a.get("name"),
         "address": a.get("address"), "price_per_night": a.get("price_per_night")}
        for a in accommodations[:6]
    ], default=str)[:1500]

    prompt = f"""Create a {duration}-day itinerary for {dest} ({start} to {end}).
Cities to visit: {json.dumps(cities)}

DESTINATION RESEARCH:
{research_summary}

CITY NEIGHBOURHOOD DATA — you MUST pick restaurants and attractions from this data.
Each neighbourhood lists specific restaurants, cafes, and attractions that are
geographically close together. Plan each day around ONE or TWO adjacent neighbourhoods:
{city_neighbourhood_data}

FLIGHTS (use arrival/departure times to plan Day 1 and last day):
{flight_summary}

ACCOMMODATIONS (plan activities near these hotels):
{accom_summary}

Travelers: {travelers} | Interests: {interests} | Diet: {dietary} | Budget: {budget}

CRITICAL RULES:
1. **USE THE NEIGHBOURHOOD DATA ABOVE** — For each day, pick ONE or TWO adjacent
   neighbourhoods from the CITY NEIGHBOURHOOD DATA and fill the day with restaurants
   and attractions listed there. Start near the hotel, breakfast at a restaurant from
   the nearest neighbourhood, group morning activities in the same area, lunch from
   the same neighbourhood's restaurant list, afternoon in one adjacent neighbourhood,
   dinner from that area. Include the neighbourhood name in each "location" field.
2. **Coordinate with flights** — Day 1: plan activities AFTER the flight arrives.
   Last day: plan departure activities BEFORE the return flight. Don't schedule a
   full day of sightseeing on arrival day if the flight lands in the evening.
3. **Coordinate with hotels** — Plan breakfast near the hotel each morning. Choose
   attractions and restaurants in the same district as the hotel when possible.
4. **Name every restaurant/cafe specifically** — NEVER say "find a local restaurant".
   Always give the real name.
5. **Google Maps link for EVERY location** — format: https://www.google.com/maps/search/PLACE+NAME+CITY
6. **Prices in local currency + USD** — use realistic local prices.
7. Each day: 5-7 items including breakfast, lunch, dinner (all named specifically).
8. Distribute cities evenly across {duration} days.

Return a JSON array:
[
  {{
    "day_number": 1,
    "date": "YYYY-MM-DD",
    "city": "CityName",
    "items": [
      {{
        "start_time": "09:00",
        "duration_minutes": 90,
        "title": "Breakfast at Cafe Name",
        "description": "Known for their fresh croissants and coffee",
        "item_type": "meal",
        "location": "Cafe Name, Neighborhood, City",
        "google_maps_url": "https://www.google.com/maps/search/Cafe+Name+City",
        "cost_local": "€12",
        "cost_usd": 13,
        "currency": "EUR",
        "notes": ""
      }}
    ]
  }}
]

Return ONLY valid JSON."""

    try:
        raw = _llm_call(_ITINERARY_SYSTEM, prompt, temperature=0.7)
        parsed = _safe_json_parse(raw)
        if isinstance(parsed, list) and len(parsed) > 0:
            _normalise_itinerary_items(parsed, dest)
            return parsed
    except Exception as exc:
        logger.warning("Itinerary LLM call failed: %s", exc)

    return []  # caller will use fallback


# ---------------------------------------------------------------------------
# Step 5: Validation (1 LLM call)
# ---------------------------------------------------------------------------

_VALIDATOR_SYSTEM = """\
You are a meticulous travel plan reviewer. You catch mistakes: restaurants at \
3 AM, museums on closed days, jumping across the city between items, 12 hours \
of back-to-back activities, unrealistic costs. You fix issues while preserving \
the plan's spirit. Always respond with valid JSON only."""


def _validate_and_fix_itinerary(
    itinerary: list[dict], dest: str, duration: int,
) -> tuple[list[dict], list[str]]:
    """Validate and fix the itinerary with a single LLM call."""
    if not itinerary:
        return itinerary, []

    itin_json = json.dumps(itinerary, indent=2, default=str)

    prompt = f"""Review this {duration}-day itinerary for {dest} and fix any issues.

--- ITINERARY ---
{itin_json}
--- END ---

CHECK FOR:
1. **Geographic coherence**: Are consecutive items in the same neighbourhood?
2. **Timing feasibility**: Realistic start times? Enough travel time between items?
3. **Cost realism**: Realistic prices for the destination?
4. **Meal coverage**: Breakfast, lunch, dinner at named restaurants each day?
5. **Activity density**: No more than 7-8 items per day.
6. **Google Maps URLs**: Every item should have a google_maps_url.

Return a JSON object:
{{
  "issues_found": ["issue 1", ...],
  "fixes_applied": ["fix 1", ...],
  "validated_itinerary": [ <the full itinerary — fixed if needed, unchanged if fine> ]
}}

If perfect, return empty arrays and the itinerary unchanged.
Return ONLY valid JSON."""

    try:
        raw = _llm_call(_VALIDATOR_SYSTEM, prompt, temperature=0.3)
        result = _safe_json_parse(raw)

        issues = result.get("issues_found", [])
        fixes = result.get("fixes_applied", [])
        validated = result.get("validated_itinerary", itinerary)

        if isinstance(validated, list) and len(validated) > 0:
            _normalise_itinerary_items(validated, dest)
            return validated, issues + fixes
        return itinerary, issues + fixes
    except Exception as exc:
        logger.warning("Plan validation failed: %s", exc)
        return itinerary, [f"Validation skipped: {exc}"]


# ---------------------------------------------------------------------------
# Auto-select best options
# ---------------------------------------------------------------------------

def _auto_select_best(flights: list[dict], accommodations: list[dict]) -> None:
    """Mark the best flight per type and best accommodation per city as 'selected'."""
    by_type: dict[str, list[dict]] = {}
    for f in flights:
        ft = f.get("flight_type", "outbound")
        by_type.setdefault(ft, []).append(f)

    for ft, group in by_type.items():
        for f in group:
            f["status"] = "suggested"
        best = min(group, key=lambda f: f.get("price", float("inf")))
        best["status"] = "selected"

    by_city: dict[str, list[dict]] = {}
    for a in accommodations:
        city = a.get("city", "unknown")
        by_city.setdefault(city, []).append(a)

    for city, group in by_city.items():
        for a in group:
            a["status"] = "suggested"
        best = min(
            group,
            key=lambda a: (-(a.get("rating") or 0), a.get("total_price", float("inf"))),
        )
        best["status"] = "selected"


# ---------------------------------------------------------------------------
# Route enrichment
# ---------------------------------------------------------------------------

def _enrich_itinerary_with_routes(
    itinerary: list[dict],
    travel_prefs: dict | None = None,
) -> None:
    """Add travel_info to each item in the itinerary (in-place)."""
    for day in itinerary:
        city = day.get("city", "")
        items = day.get("items", [])
        if len(items) > 1:
            try:
                compute_routes_for_day(items, city, travel_prefs)
            except Exception as exc:
                logger.warning("Route enrichment failed for day %s: %s",
                               day.get("day_number"), exc)
                for item in items:
                    item.setdefault("travel_info", {})
        elif items:
            items[0].setdefault("travel_info", {})


# ---------------------------------------------------------------------------
# Fallback itinerary builder
# ---------------------------------------------------------------------------

def _build_fallback_itinerary(
    cities: list[str], duration: int, start_date: str,
) -> list[dict]:
    n = len(cities)
    base = duration // max(n, 1)
    extra = duration % max(n, 1)
    days_per_city = [base + (1 if i < extra else 0) for i in range(n)]

    itinerary: list[dict] = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")

    for city_idx, city in enumerate(cities):
        for _ in range(days_per_city[city_idx]):
            day_number = len(itinerary) + 1
            date_str = current_date.strftime("%Y-%m-%d")
            items = _fallback_day_plan(city, day_number)
            for i, item in enumerate(items):
                item["id"] = f"day{day_number}_item{i}"
                item["status"] = "planned"
                item["delayed_to_day"] = None
                item["is_ai_suggested"] = 1

            itinerary.append({
                "day_number": day_number,
                "date": date_str,
                "city": city,
                "items": items,
            })
            current_date += timedelta(days=1)

    return itinerary


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TripPlanner:
    """High-level wrapper — direct litellm calls, no CrewAI overhead.

    Total LLM calls per plan_trip:
      1. Research + city selection  (1 call)
      2. Flights search             (0 calls — direct API)
      3. Hotels search              (0 calls — direct API)
      4. Itinerary generation       (1 call)
      5. Validation                 (1 call)
    = 3 LLM round-trips vs ~25 with CrewAI
    """

    @staticmethod
    def plan_trip(trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full planning pipeline."""
        dest = trip_data["destination"]
        origin = trip_data.get("origin_city", "New York")
        start = trip_data["start_date"]
        end = trip_data["end_date"]
        travelers = trip_data.get("num_travelers", 1)
        interests = ", ".join(trip_data.get("interests", [])) or "general sightseeing"
        dietary = ", ".join(trip_data.get("dietary_restrictions", [])) or "none"
        budget = trip_data.get("budget_level", "mid")
        duration = _calc_duration(start, end)
        is_country = _is_likely_country(dest)

        # --- Step 1: Research + City Selection (1 LLM call) ---
        research, cities = _research_and_select_cities(
            dest, duration, interests, budget, is_country,
        )

        # --- Step 2 & 3: Flights + Hotels (parallel, NO LLM calls) ---
        flights: list[dict] = []
        accommodations: list[dict] = []

        with ThreadPoolExecutor(max_workers=max(len(cities) + 1, 2)) as pool:
            flight_future = pool.submit(
                _search_flights_direct, origin, cities[0], start, end, travelers,
            )
            hotel_futures = {
                pool.submit(_search_hotels_direct, city, start, end, travelers): city
                for city in cities
            }
            flights = flight_future.result()
            for future in as_completed(hotel_futures):
                accommodations.extend(future.result()[:3])

        # --- Step 4: Itinerary (1 LLM call — receives flights + hotels context) ---
        itinerary = _generate_itinerary(
            dest, cities, duration, start, end, travelers,
            interests, dietary, budget, research, flights, accommodations,
        )
        if not itinerary:
            itinerary = _build_fallback_itinerary(cities, duration, start)

        # --- Step 5: Validate (1 LLM call) ---
        validation_notes: list[str] = []
        try:
            itinerary, validation_notes = _validate_and_fix_itinerary(
                itinerary, dest, duration,
            )
        except Exception as exc:
            logger.warning("Validator failed: %s", exc)

        # --- Post-processing ---
        _auto_select_best(flights, accommodations)
        _enrich_itinerary_with_routes(itinerary)

        summary = f"Planned {duration} days across {', '.join(cities)}"
        if validation_notes:
            summary += f" (validated: {len(validation_notes)} checks)"

        return {
            "cities": cities,
            "flights": flights,
            "accommodations": accommodations,
            "itinerary": itinerary,
            "is_country_level": is_country,
            "planning_summary": summary,
            "validation_notes": validation_notes,
        }

    @staticmethod
    def plan_trip_stream(
        trip_data: Dict[str, Any],
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields SSE progress events while planning."""
        import time as _time

        dest = trip_data["destination"]
        origin = trip_data.get("origin_city", "New York")
        start = trip_data["start_date"]
        end = trip_data["end_date"]
        travelers = trip_data.get("num_travelers", 1)
        interests = ", ".join(trip_data.get("interests", [])) or "general sightseeing"
        dietary = ", ".join(trip_data.get("dietary_restrictions", [])) or "none"
        budget = trip_data.get("budget_level", "mid")
        duration = _calc_duration(start, end)
        is_country = _is_likely_country(dest)

        # --- Step 1: Research + City Selection ---
        yield {
            "type": "progress", "agent": "DestinationResearcher",
            "status": "running",
            "message": f"Researching {dest}...",
        }

        result_holder: dict = {}
        error_holder: list = []

        def _run_research():
            try:
                r, c = _research_and_select_cities(
                    dest, duration, interests, budget, is_country,
                )
                result_holder["research"] = r
                result_holder["cities"] = c
            except Exception as exc:
                error_holder.append(exc)

        thread = threading.Thread(target=_run_research, daemon=True)
        thread.start()
        while thread.is_alive():
            _time.sleep(0.2)

        if error_holder:
            yield {"type": "error", "agent": "Orchestrator", "status": "error",
                   "message": str(error_holder[0])}
            return

        research = result_holder["research"]
        cities = result_holder["cities"]

        yield {
            "type": "progress", "agent": "DestinationResearcher",
            "status": "done",
            "message": f"Research on {dest} complete",
        }
        yield {
            "type": "progress", "agent": "CitySelector",
            "status": "done",
            "message": f"Cities selected: {', '.join(cities)}",
        }

        # --- Step 2 & 3: Flights + Hotels (parallel, no LLM) ---
        yield {
            "type": "progress", "agent": "FlightFinder",
            "status": "running",
            "message": "Searching for flights via Amadeus...",
        }
        yield {
            "type": "progress", "agent": "AccommodationFinder",
            "status": "running",
            "message": "Finding accommodations via Amadeus...",
        }

        flights: list[dict] = []
        accommodations: list[dict] = []

        def _run_search():
            nonlocal flights, accommodations
            try:
                with ThreadPoolExecutor(max_workers=max(len(cities) + 1, 2)) as pool:
                    flight_future = pool.submit(
                        _search_flights_direct, origin, cities[0], start, end, travelers,
                    )
                    hotel_futures = {
                        pool.submit(_search_hotels_direct, city, start, end, travelers): city
                        for city in cities
                    }
                    flights = flight_future.result()
                    for future in as_completed(hotel_futures):
                        accommodations.extend(future.result()[:3])
            except Exception as exc:
                error_holder.append(exc)

        error_holder.clear()
        thread = threading.Thread(target=_run_search, daemon=True)
        thread.start()
        while thread.is_alive():
            _time.sleep(0.2)

        if error_holder:
            yield {"type": "error", "agent": "Orchestrator", "status": "error",
                   "message": str(error_holder[0])}
            return

        yield {
            "type": "progress", "agent": "FlightFinder",
            "status": "done",
            "message": "Flight search complete",
        }
        yield {
            "type": "progress", "agent": "AccommodationFinder",
            "status": "done",
            "message": "Accommodation search complete",
        }

        # --- Step 4: Itinerary (1 LLM call) ---
        yield {
            "type": "progress", "agent": "ItineraryPlanner",
            "status": "running",
            "message": "Building your day-by-day itinerary...",
        }

        itinerary: list[dict] = []

        def _run_itinerary():
            nonlocal itinerary
            try:
                itinerary = _generate_itinerary(
                    dest, cities, duration, start, end, travelers,
                    interests, dietary, budget, research, flights, accommodations,
                )
            except Exception as exc:
                error_holder.append(exc)

        error_holder.clear()
        thread = threading.Thread(target=_run_itinerary, daemon=True)
        thread.start()
        while thread.is_alive():
            _time.sleep(0.2)

        if error_holder:
            yield {"type": "error", "agent": "Orchestrator", "status": "error",
                   "message": str(error_holder[0])}
            return

        if not itinerary:
            itinerary = _build_fallback_itinerary(cities, duration, start)

        yield {
            "type": "progress", "agent": "ItineraryPlanner",
            "status": "done",
            "message": "Itinerary planning complete",
        }

        # --- Step 5: Validation ---
        yield {
            "type": "progress", "agent": "PlanValidator",
            "status": "running",
            "message": "Validating itinerary for geographic coherence and timing...",
        }

        validation_notes: list[str] = []
        try:
            itinerary, validation_notes = _validate_and_fix_itinerary(
                itinerary, dest, duration,
            )
        except Exception as exc:
            logger.warning("Validator failed: %s", exc)

        yield {
            "type": "progress", "agent": "PlanValidator",
            "status": "done",
            "message": f"Validation complete — {len(validation_notes)} checks performed",
        }

        # --- Post-processing ---
        _auto_select_best(flights, accommodations)
        _enrich_itinerary_with_routes(itinerary)

        summary = f"Planned {duration} days across {', '.join(cities)}"
        if validation_notes:
            summary += f" (validated: {len(validation_notes)} checks)"

        plan_data = {
            "cities": cities,
            "flights": flights,
            "accommodations": accommodations,
            "itinerary": itinerary,
            "is_country_level": is_country,
            "planning_summary": summary,
            "validation_notes": validation_notes,
        }

        yield {
            "type": "complete",
            "agent": "Orchestrator",
            "status": "complete",
            "message": "Trip planning complete!",
            "plan": plan_data,
            "validation_notes": validation_notes,
        }

    @staticmethod
    def modify_itinerary_chat(
        trip_data: Dict[str, Any],
        current_itinerary: list[dict],
        user_message: str,
        chat_history: list[dict] | None = None,
    ) -> Dict[str, Any]:
        """Modify the itinerary based on a user chat message (1 LLM call).

        Returns {"itinerary": [...], "reply": "...", "travel_prefs": {...}}
        """
        dest = trip_data["destination"]
        start = trip_data["start_date"]
        end = trip_data["end_date"]
        duration = _calc_duration(start, end)
        interests = ", ".join(trip_data.get("interests", [])) or "general sightseeing"
        budget = f"${trip_data.get('budget_level', 1000):,} total"

        itin_json = json.dumps(current_itinerary, indent=2, default=str)

        # Gather neighbourhood data for cities in the itinerary
        itin_cities = list({day.get("city", dest) for day in current_itinerary if day.get("city")})
        city_data_for_modify = _gather_city_data(itin_cities or [dest])

        # Web search for current conditions if the message suggests real-time needs
        modify_web_results = ""
        if any(kw in user_message.lower() for kw in
               ("weather", "rain", "storm", "closed", "cancel", "strike", "event", "festival")):
            web_hits = _web_search(f"{dest} {user_message} current", max_results=3)
            if web_hits:
                modify_web_results = f"\n--- CURRENT WEB INFO ---\n{web_hits}\n--- END WEB INFO ---\n"

        history_context = ""
        if chat_history:
            history_lines = []
            for msg in chat_history[-10:]:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            history_context = "\n--- CONVERSATION HISTORY ---\n" + "\n".join(history_lines) + "\n--- END HISTORY ---\n\n"

        system_prompt = """\
You are an expert travel planner who adapts itineraries to real-world changes: \
weather, cancellations, new wishes, schedule conflicts. You know specific \
restaurants, attractions, and alternatives. When the user says it's raining you \
swap outdoor activities for museums. You always name exact places and include \
Google Maps URLs. You are also aware that the itinerary includes recommended \
travel routes between stops (walking / transit). When the user mentions conditions \
that affect HOW they travel — rain, transit strikes, wanting a walking day — \
reflect that in the travel_prefs field. Always respond with valid JSON only."""

        user_prompt = f"""You are modifying an existing {duration}-day itinerary for {dest}
({start} to {end}).  Interests: {interests}. Budget: {budget}.
{modify_web_results}
--- CITY DATA (use these specific restaurants/attractions as alternatives) ---
{city_data_for_modify}
--- END CITY DATA ---

{history_context}--- CURRENT ITINERARY (JSON) ---
{itin_json}
--- END CURRENT ITINERARY ---

THE USER SAYS:
\"{user_message}\"

INSTRUCTIONS:
1. Understand what the user wants changed.
2. Keep UNCHANGED days exactly as they are — copy them verbatim.
3. For CHANGED days, keep as many original items as possible.
4. Every location MUST have a google_maps_url.
5. Name every restaurant/cafe specifically — never say "find a local restaurant".
6. Include cost_usd, cost_local, currency for every item.

TRAVEL PREFERENCE DETECTION:
If the message implies a travel-mode constraint, include "travel_prefs":
- "It's raining"        → {{"avoid": ["walking"], "prefer": ["transit"]}}
- "Trains are cancelled" → {{"avoid": ["transit"], "prefer": ["walking"]}}
- No travel implications → {{"avoid": [], "prefer": []}}

Return a JSON object:
{{
  "reply": "Short 1-3 sentence confirmation of changes.",
  "travel_prefs": {{"avoid": [...], "prefer": [...]}},
  "itinerary": [ <full modified itinerary> ]
}}

Return ONLY valid JSON."""

        try:
            raw = _llm_call(system_prompt, user_prompt, temperature=0.7)
            result = _safe_json_parse(raw)
        except Exception:
            return {
                "itinerary": current_itinerary,
                "reply": "Sorry, I couldn't understand how to modify the itinerary. Please try rephrasing your request.",
                "travel_prefs": {},
            }

        new_itinerary = result.get("itinerary", current_itinerary)
        reply = result.get("reply", "Itinerary updated.")
        travel_prefs = result.get("travel_prefs") or {}

        if not isinstance(travel_prefs, dict):
            travel_prefs = {}
        for key in ("avoid", "prefer"):
            if key not in travel_prefs or not isinstance(travel_prefs[key], list):
                travel_prefs.setdefault(key, [])

        _normalise_itinerary_items(new_itinerary, dest)
        _enrich_itinerary_with_routes(new_itinerary, travel_prefs)

        return {
            "itinerary": new_itinerary,
            "reply": reply,
            "travel_prefs": travel_prefs,
        }

    @staticmethod
    def regenerate_itinerary(
        trip_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        flights: list[dict],
        accommodations: list[dict],
    ) -> Dict[str, Any]:
        """Re-run only the itinerary generation using cached context.

        Called by the /regenerate-itinerary endpoint to avoid re-running
        the full pipeline (research, flights, hotels).  Still only 2 LLM
        calls: itinerary generation + validation.
        """
        dest = trip_data["destination"]
        start = trip_data["start_date"]
        end = trip_data["end_date"]
        travelers = trip_data.get("num_travelers", 1)
        interests = ", ".join(trip_data.get("interests", [])) or "general sightseeing"
        dietary = ", ".join(trip_data.get("dietary_restrictions", [])) or "none"
        budget = trip_data.get("budget_level", "mid")
        duration = _calc_duration(start, end)

        cities = plan_data.get("cities", [dest])
        research = {
            "overview": plan_data.get("planning_summary", ""),
            "top_attractions": [],
            "local_food": [],
        }

        itinerary = _generate_itinerary(
            dest, cities, duration, start, end, travelers,
            interests, dietary, budget, research, flights, accommodations,
        )
        if not itinerary:
            itinerary = _build_fallback_itinerary(cities, duration, start)

        validation_notes: list[str] = []
        try:
            itinerary, validation_notes = _validate_and_fix_itinerary(
                itinerary, dest, duration,
            )
        except Exception as exc:
            logger.warning("Validator failed: %s", exc)

        _enrich_itinerary_with_routes(itinerary)

        return {
            "itinerary": itinerary,
            "validation_notes": validation_notes,
        }

    @staticmethod
    def _is_likely_country(destination: str) -> bool:
        return _is_likely_country(destination)


# Singleton consumed by main.py via `from agents import planning_agent`
planning_agent = TripPlanner()
