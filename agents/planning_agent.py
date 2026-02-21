"""
CrewAI Multi-Agent Trip Planner

Orchestrates a crew of specialized agents that collaborate to plan trips:
  1. DestinationResearcher  - web search + LLM for destination intel
  2. CitySelector           - picks cities for country-level trips
  3. FlightFinder           - uses Amadeus flight search (via FlightAgent)
  4. AccommodationFinder    - uses Amadeus hotel search (via AccomAgent)
  5. ItineraryPlanner       - builds the final day-by-day plan

FlightAgent and AccomAgent are used both as tools within the crew AND
to generate the final structured data returned to the frontend.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool as crewai_tool

TRACING = True
VERBOSE = True

# ---------------------------------------------------------------------------
# Import Amadeus-backed tools from sub-agents.
# Try relative import (when loaded as agents.planning_agent package member),
# fall back to absolute (when loaded directly from sys.path in tests).
# ---------------------------------------------------------------------------
try:
    from .FlightAgent import search_flights as _amadeus_flights_tool
    from .AccomAgent import search_hotels as _amadeus_hotels_tool
except ImportError:
    from FlightAgent import search_flights as _amadeus_flights_tool  # type: ignore
    from AccomAgent import search_hotels as _amadeus_hotels_tool  # type: ignore

_amadeus_flights_fn = _amadeus_flights_tool.func
_amadeus_hotels_fn = _amadeus_hotels_tool.func

# Optional: web search & scraping tools (need TAVILY_API_KEY / SERPER_API_KEY)
_web_search_tools: list = []
try:
    if os.getenv("TAVILY_API_KEY"):
        from crewai_tools import TavilySearchTool
        _web_search_tools.append(TavilySearchTool())
    elif os.getenv("SERPER_API_KEY"):
        from crewai_tools import SerperDevTool
        _web_search_tools.append(SerperDevTool())
except Exception:
    assert False
    pass  # web search unavailable - agents will use LLM knowledge only

try:
    from crewai_tools import ScrapeWebsiteTool
    _scrape_tool = ScrapeWebsiteTool()
except Exception:
    _scrape_tool = None

from mock_data import (
    generate_mock_flights,
    generate_mock_accommodations,
    get_city_info,
    get_airport_for_city,
)

# ---------------------------------------------------------------------------
# IATA code mappings (city name → airport/city code for Amadeus)
# ---------------------------------------------------------------------------

_CITY_TO_AIRPORT: dict[str, str] = {
    "New York": "JFK", "London": "LHR", "Paris": "CDG", "Tokyo": "NRT",
    "Los Angeles": "LAX", "Chicago": "ORD", "Sydney": "SYD", "Dubai": "DXB",
    "Singapore": "SIN", "Bangkok": "BKK", "Barcelona": "BCN", "Rome": "FCO",
    "Amsterdam": "AMS", "Berlin": "BER", "Prague": "PRG", "Istanbul": "IST",
    "San Francisco": "SFO", "Miami": "MIA", "Boston": "BOS", "Kyoto": "KIX",
    "Osaka": "KIX", "Madrid": "MAD", "Lisbon": "LIS", "Vienna": "VIE",
    "Zurich": "ZRH", "Copenhagen": "CPH", "Stockholm": "ARN", "Seoul": "ICN",
}

_CITY_TO_IATA_CITY: dict[str, str] = {
    "New York": "NYC", "London": "LON", "Paris": "PAR", "Tokyo": "TYO",
    "Los Angeles": "LAX", "Chicago": "CHI", "Sydney": "SYD", "Dubai": "DXB",
    "Singapore": "SIN", "Bangkok": "BKK", "Barcelona": "BCN", "Rome": "ROM",
    "Amsterdam": "AMS", "Berlin": "BER", "Prague": "PRG", "Istanbul": "IST",
    "San Francisco": "SFO", "Miami": "MIA", "Boston": "BOS", "Kyoto": "OSA",
    "Osaka": "OSA", "Madrid": "MAD", "Lisbon": "LIS", "Vienna": "VIE",
    "Zurich": "ZRH", "Copenhagen": "CPH", "Stockholm": "STO", "Seoul": "SEL",
}


def _airport_code(city: str) -> str:
    return _CITY_TO_AIRPORT.get(city, get_airport_for_city(city))


def _city_iata(city: str) -> str:
    return _CITY_TO_IATA_CITY.get(city, city[:3].upper())


def _is_mock_flight(f: dict) -> bool:
    """True when a dict looks like mock-data format (has the keys the DB expects)."""
    return "flight_type" in f and "airline" in f and "flight_number" in f


def _is_mock_accom(a: dict) -> bool:
    return "name" in a and "price_per_night" in a and "check_in_date" in a


# Well-known IATA carrier codes → human-readable names (fallback for when
# the Amadeus `dictionaries` block is not available).
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
    hours = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    return hours * 60 + mins


def _normalize_amadeus_flights(raw_offers: list[dict], origin_city: str,
                                dest_city: str) -> list[dict]:
    """Convert Amadeus FlightOffer objects into the DB-compatible schema.

    Each Amadeus offer may contain 1 itinerary (one-way) or 2 (round-trip).
    We flatten each itinerary into a separate DB row.
    """
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

            # Determine flight type from itinerary index
            flight_type = "outbound" if itin_idx == 0 else "return"

            # Build booking URL (generic search fallback)
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
        best_offer = offers[0]  # first offer is typically cheapest

        total_price = float(best_offer.get("price", {}).get("total", 0))
        currency = best_offer.get("price", {}).get("currency", "USD")
        price_per_night = round(total_price / nights, 2)

        # Build address string from hotel info
        name = hotel_info.get("name", f"Hotel in {city}")
        lat = hotel_info.get("latitude")
        lon = hotel_info.get("longitude")

        # Room amenities from description
        room_desc = (best_offer.get("room", {})
                     .get("description", {})
                     .get("text", ""))
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
            "rating": None,  # not available in Hotel Offers Search v3
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
# LLM model helper  (supports OpenAI, Gemini, Claude via LLM_PROVIDER env var)
# ---------------------------------------------------------------------------

_LLM_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-sonnet-4-20250514",
}


def _llm_name() -> str:
    """Return the model string in CrewAI's native `provider/model` format."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    if provider not in _LLM_DEFAULTS:
        provider = "openai"
    model = os.getenv("LLM_MODEL", _LLM_DEFAULTS[provider])
    if provider == "openai":
        return model
    return f"{provider}/{model}"


# ---------------------------------------------------------------------------
# CrewAI Tools
# Wrap Amadeus-backed tools with city-name → IATA conversion so that
# the LLM can pass plain city names without knowing IATA codes.
# ---------------------------------------------------------------------------

@crewai_tool("Search Flights")
def search_flights_tool(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    num_travelers: int = 1,
) -> str:
    """Search for available flights between two cities using Amadeus (or mock fallback).
    Args:
        origin: Departure city name (e.g. 'New York')
        destination: Arrival city name (e.g. 'Tokyo')
        departure_date: YYYY-MM-DD format
        return_date: YYYY-MM-DD format (empty string for one-way)
        num_travelers: Number of passengers
    Returns:
        JSON string with up to 5 flight options.
    """
    origin_code = _airport_code(origin)
    dest_code = _airport_code(destination)
    results = _amadeus_flights_fn(origin_code, dest_code, departure_date, return_date, num_travelers)
    if results and "error" not in results[0]:
        # Normalise if live Amadeus format
        if not _is_mock_flight(results[0]):
            results = _normalize_amadeus_flights(results, origin, destination)
        return json.dumps(results[:5], default=str)
    # Amadeus failed — fall back to mock data
    results = generate_mock_flights(origin, destination, departure_date, return_date or None, num_travelers)
    return json.dumps(results[:5], default=str)


@crewai_tool("Search Accommodations")
def search_accommodations_tool(
    city: str,
    check_in_date: str,
    check_out_date: str,
    num_guests: int = 1,
) -> str:
    """Search for hotels in a city using Amadeus (or mock fallback).
    Args:
        city: City name (e.g. 'Paris')
        check_in_date: YYYY-MM-DD format
        check_out_date: YYYY-MM-DD format
        num_guests: Number of guests
    Returns:
        JSON string with up to 5 accommodation options.
    """
    city_code = _city_iata(city)
    results = _amadeus_hotels_fn(city_code, check_in_date, check_out_date, num_guests, "hotel")
    if results and "error" not in results[0]:
        # Normalise if live Amadeus format
        if not _is_mock_accom(results[0]):
            results = _normalize_amadeus_hotels(results, city, check_in_date, check_out_date)
        return json.dumps(results[:5], default=str)
    results = generate_mock_accommodations(city, check_in_date, check_out_date, num_guests)
    return json.dumps(results[:5], default=str)


@crewai_tool("Get City Information")
def get_city_info_tool(city_name: str) -> str:
    """Get information about a city: attractions, food, transport.
    Args:
        city_name: Name of the city (e.g. 'Tokyo')
    Returns:
        JSON string with city info.
    """
    return json.dumps(get_city_info(city_name), default=str)


# ---------------------------------------------------------------------------
# CrewAI Agent definitions
# ---------------------------------------------------------------------------

def _build_agents():
    """Create the five specialized agents with appropriate tools."""

    researcher_tools = list(_web_search_tools)
    if _scrape_tool:
        researcher_tools.append(_scrape_tool)
    researcher_tools.append(get_city_info_tool)

    destination_researcher = Agent(
        role="Destination Researcher",
        goal="Research travel destinations thoroughly and provide practical information for trip planning",
        backstory=(
            "You are a seasoned travel researcher with extensive knowledge of destinations worldwide. "
            "You excel at uncovering practical travel information including top attractions, local food, "
            "transport tips, and budget considerations. You always provide structured, actionable information."
        ),
        tools=researcher_tools,
        llm=_llm_name(),
        verbose=VERBOSE,
        allow_delegation=False,
        max_iter=8,
    )

    selector_tools = list(_web_search_tools)
    selector_tools.append(get_city_info_tool)

    city_selector = Agent(
        role="City Selection Specialist",
        goal="Select the optimal cities to visit within a country for multi-city trips",
        backstory=(
            "You are a travel routing expert who knows which cities pair well together and how to "
            "create logical, efficient multi-city itineraries. You consider travel distances, "
            "city highlights, and traveler interests to select the best route."
        ),
        tools=selector_tools,
        llm=_llm_name(),
        verbose=VERBOSE,
        allow_delegation=False,
        max_iter=5,
    )

    flight_finder = Agent(
        role="Flight Search Specialist",
        goal="Find the best flight options using the Amadeus-powered flight search tool",
        backstory=(
            "You are a flight search expert who uses the Search Flights tool to find optimal air "
            "travel options via the Amadeus GDS. Always use the tool with city names — IATA code "
            "conversion is handled automatically. Never make up flight data."
        ),
        tools=[search_flights_tool],
        llm=_llm_name(),
        verbose=VERBOSE,
        allow_delegation=False,
        max_iter=5,
    )

    accommodation_finder = Agent(
        role="Accommodation Search Specialist",
        goal="Find the best places to stay for each city using the Amadeus-powered hotel search tool",
        backstory=(
            "You are an accommodation expert who uses the Search Accommodations tool to find hotels "
            "via the Amadeus GDS. Always use the tool with city names — IATA conversion is automatic. "
            "Never make up accommodation data."
        ),
        tools=[search_accommodations_tool],
        llm=_llm_name(),
        verbose=VERBOSE,
        allow_delegation=False,
        max_iter=5,
    )

    planner_tools = [get_city_info_tool]
    planner_tools.extend(_web_search_tools)

    itinerary_planner = Agent(
        role="Itinerary Planner",
        goal=(
            "Create a detailed day-by-day itinerary with SPECIFIC named places for every "
            "activity and meal, structured as DAILY ROUTES through the city. Each day should "
            "follow either a LOOP (hotel → area A → area B → hotel) or a LINEAR path "
            "(hotel → A → B → C, then transit back). Use the neighbourhood connectivity "
            "data to plan routes through 2-4 ADJACENT areas per day. Never say 'find a "
            "local restaurant' — always name the exact place. Include a Google Maps link "
            "for every location."
        ),
        backstory=(
            "You are an expert itinerary designer, local food critic, and city route "
            "planner who creates daily walking routes through cities. You think of each "
            "day as a GEOGRAPHIC ROUTE — not a random list of places. You use the "
            "'neighbourhood_travel' data to understand which areas are adjacent and how "
            "long it takes to travel between them. You use the 'suggested_routes' as "
            "templates and customise them based on traveler interests.\n\n"
            "Your route philosophy:\n"
            "- LOOP ROUTE: Start near hotel → walk outward through 2-3 adjacent areas "
            "→ circle back to hotel area. Great for days with evening dinner plans near "
            "the hotel.\n"
            "- LINEAR ROUTE: Start near hotel → travel in one direction through 3-4 "
            "areas → end at a transit hub and take train/bus/rideshare back. Great for "
            "covering more ground.\n\n"
            "You pick meals at restaurants IN the area you're exploring at that time of "
            "day. You ALWAYS recommend places by name (e.g. 'Ichiran Ramen Shibuya', "
            "'Le Bouillon Chartier'). You never use generic phrases. You include a "
            "Google Maps URL for every location. You understand local currencies and "
            "always show prices in the local currency with a USD equivalent."
        ),
        tools=planner_tools,
        llm=_llm_name(),
        verbose=VERBOSE,
        allow_delegation=False,
        max_iter=10,
    )

    return (
        destination_researcher,
        city_selector,
        flight_finder,
        accommodation_finder,
        itinerary_planner,
    )


# ---------------------------------------------------------------------------
# CrewAI Task builders
# ---------------------------------------------------------------------------

def _build_tasks(
    trip_data: Dict[str, Any],
    agents: tuple,
    on_progress: Optional[callable] = None,
) -> list[Task]:
    (
        researcher_agent,
        selector_agent,
        flight_agent,
        accommodation_agent,
        planner_agent,
    ) = agents

    dest = trip_data["destination"]
    start = trip_data["start_date"]
    end = trip_data["end_date"]
    travelers = trip_data.get("num_travelers", 1)
    interests = ", ".join(trip_data.get("interests", [])) or "general sightseeing"
    dietary = ", ".join(trip_data.get("dietary_restrictions", [])) or "none"
    budget = trip_data.get("budget_level", "mid")
    duration = _calc_duration(start, end)
    is_country = _is_likely_country(dest)

    def _make_callback(agent_name: str, done_msg: str):
        def cb(output: Any):
            if on_progress:
                on_progress({
                    "type": "progress",
                    "agent": agent_name,
                    "status": "done",
                    "message": done_msg,
                })
        return cb

    research_task = Task(
        description=f"""Research the travel destination **{dest}** for a {duration}-day trip.

Traveler interests: {interests}
Budget level: {budget}

Provide a comprehensive JSON object with:
{{
  "overview": "2-3 sentence overview of the destination",
  "best_areas": ["area1", "area2"],
  "top_attractions": ["attraction1", "attraction2", "..."],
  "local_food": ["dish1", "dish2", "..."],
  "transport_tips": "how to get around",
  "safety_notes": "brief safety info",
  "budget_tips": "money-saving tips"
}}

Return ONLY valid JSON, no markdown fences or extra text.""",
        expected_output="A JSON object containing destination overview, best areas, top attractions, local food, transport tips, safety notes, and budget tips.",
        agent=researcher_agent,
        callback=_make_callback("DestinationResearcher", f"Research on {dest} complete"),
    )

    if is_country:
        city_description = f"""Based on the destination research provided in context, select the best cities
to visit in **{dest}** for a {duration}-day trip.

Interests: {interests}
Budget: {budget}

Rules:
- Select 2-4 cities (minimum 2 days each)
- Order them in a logical route (minimize backtracking)
- Include the most popular city

Return ONLY a valid JSON array: ["City1", "City2", "City3"]"""
    else:
        city_description = f"""The destination is **{dest}** which is a single city, not a country.
Return a JSON array with just this city: ["{dest}"]"""

    city_task = Task(
        description=city_description,
        expected_output="A JSON array of city names to visit.",
        agent=selector_agent,
        context=[research_task],
        callback=_make_callback("CitySelector", f"Cities selected for {dest}"),
    )

    flight_task = Task(
        description=f"""Find flights for this trip using the Search Flights tool.

Trip details:
- Departure date: {start}
- Return date: {end}
- Number of travelers: {travelers}
- Origin: New York

Using the cities selected in the context, call the Search Flights tool with:
  origin="New York", destination=<first city from context>,
  departure_date="{start}", return_date="{end}", num_travelers={travelers}

IMPORTANT: Your output MUST be a valid JSON object:
{{
  "origin": "New York",
  "destination_city": "<first city from context>",
  "departure_date": "{start}",
  "return_date": "{end}",
  "num_travelers": {travelers}
}}

Return ONLY valid JSON.""",
        expected_output="A JSON object with flight search parameters used.",
        agent=flight_agent,
        context=[city_task],
        callback=_make_callback("FlightFinder", "Flight search complete"),
    )

    accommodation_task = Task(
        description=f"""Find accommodations for each city using the Search Accommodations tool.

Trip dates: {start} to {end}
Number of guests: {travelers}
Budget level: {budget}

For each city from context, call Search Accommodations with:
  city=<city name>, check_in_date="{start}", check_out_date="{end}", num_guests={travelers}

IMPORTANT: After calling the tool, pick the BEST option for the budget level and include
the hotel details in your output. Your output MUST be a valid JSON object:
{{
  "accommodations": [
    {{
      "city": "<city name>",
      "hotel_name": "<name of chosen hotel>",
      "address": "<hotel address or neighbourhood>",
      "price_per_night": <number>,
      "neighbourhood": "<district/area the hotel is in>"
    }}
  ]
}}

Return ONLY valid JSON.""",
        expected_output="A JSON object with accommodation details including hotel name, address, and neighbourhood for each city.",
        agent=accommodation_agent,
        context=[city_task, research_task],
        callback=_make_callback("AccommodationFinder", "Accommodation search complete"),
    )

    itinerary_task = Task(
        description=f"""Create a {duration}-day itinerary for {dest} ({start} to {end}).

Context from previous agents: destination research (including neighbourhood layout with
attractions grouped by district, TRAVEL TIMES between areas, and SUGGESTED ROUTES),
selected cities, flights, and accommodations (including hotel name and neighbourhood).

Travelers: {travelers} | Interests: {interests} | Diet: {dietary} | Budget: {budget}

PLANNING APPROACH — ROUTE-BASED DAILY PLANNING:
1. Use the Get City Information tool for each city. The result includes:
   - "neighbourhoods": areas with attractions and food
   - "neighbourhood_travel": travel times between each pair of areas
   - "suggested_routes": pre-built loop and linear route templates
   - "transit_hubs": stations for getting back to the hotel

2. Note the HOTEL NAME and NEIGHBOURHOOD from the accommodation context.

3. For each day, design a ROUTE — not a random list. Choose one of two patterns:

   **LOOP ROUTE** (hotel → A → B → C → hotel):
   - Best for half-days or when dinner should be near the hotel
   - Pick 2-3 ADJACENT areas that connect back to the hotel area
   - Use the "neighbourhood_travel" data to confirm they connect
   - Morning: explore area A (near hotel), lunch in area A
   - Afternoon: walk to area B, explore, walk to area C
   - Evening: return to hotel area for dinner

   **LINEAR ROUTE** (hotel → A → B → C → transit back):
   - Best for full days exploring further-out areas
   - Pick 3-4 areas in a LINE moving away from the hotel
   - End at or near a "transit_hub" for easy return
   - Morning: explore first area, lunch there or in next area
   - Afternoon: continue along the line
   - Evening: dinner in the final area, then transit/rideshare back

4. Vary the routes across days so different parts of the city are covered.
   Refer to "suggested_routes" for inspiration but customise based on interests.

5. Between activities, the next stop MUST be reachable by walking or a short
   transit hop (check "neighbourhood_travel" times). NEVER jump to a
   non-adjacent area mid-route.

CRITICAL RULES:
1. **ROUTE-BASED DAILY PLANS** — This is the MOST IMPORTANT rule. Each day must follow
   a geographic ROUTE (loop or linear) through 2-4 CONNECTED areas. Use the
   "neighbourhood_travel" data to verify adjacency. Consecutive stops must be
   in the SAME area or an ADJACENT area (connected in neighbourhood_travel).
2. **Breakfast near the hotel** — always within walking distance of accommodation.
3. **Lunch and dinner IN the area you're exploring** — pick restaurants from the
   neighbourhood you're visiting at that time of day.
4. **End-of-day return** — For loop routes, dinner near hotel. For linear routes,
   end near a transit hub and note which line/bus/rideshare to take back.
5. **Name every restaurant/cafe/food stall specifically** — NEVER say "find a local
   restaurant". Always give the real name (e.g. "Ichiran Ramen Shibuya").
6. **Google Maps link for EVERY location** — format: https://www.google.com/maps/search/PLACE+NAME+CITY
7. **Prices in local currency + USD** — e.g. "cost_local": "¥1500", "cost_usd": 10.
   Use realistic local prices.
8. Each day: 5-7 items including breakfast, lunch, dinner (all named specifically).
9. Day 1 = arrival, last day = departure. Distribute cities evenly.
10. **Add a "route_type" field** to each day: "loop" or "linear", and a
    "areas_visited" field listing the neighbourhoods in route order.

Return a JSON array:
[
  {{
    "day_number": 1,
    "date": "YYYY-MM-DD",
    "city": "CityName",
    "route_type": "loop",
    "areas_visited": ["Neighbourhood A", "Neighbourhood B", "Neighbourhood A"],
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

Return ONLY valid JSON.""",
        expected_output="A JSON array of day objects with specific named locations, Google Maps URLs, and local currency prices.",
        agent=planner_agent,
        context=[research_task, city_task, flight_task, accommodation_task],
        callback=_make_callback("ItineraryPlanner", "Itinerary planning complete"),
    )

    return [research_task, city_task, flight_task, accommodation_task, itinerary_task]


# ---------------------------------------------------------------------------
# Result parser
# ---------------------------------------------------------------------------

def _parse_crew_result(
    tasks: list[Task],
    trip_data: Dict[str, Any],
) -> Dict[str, Any]:
    dest = trip_data["destination"]
    start = trip_data["start_date"]
    end = trip_data["end_date"]
    travelers = trip_data.get("num_travelers", 1)
    duration = _calc_duration(start, end)
    is_country = _is_likely_country(dest)

    research_task, city_task, flight_task, accommodation_task, itinerary_task = tasks

    # --- Parse cities ---
    cities = [dest]
    try:
        city_raw = city_task.output.raw if city_task.output else "[]"
        parsed_cities = _safe_json_parse(city_raw)
        if isinstance(parsed_cities, list) and len(parsed_cities) > 0:
            cities = [str(c) for c in parsed_cities[:4]]
    except Exception:
        if is_country:
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
            cities = defaults.get(dest, [f"{dest} City"])

    # --- Flights via Amadeus (falls back to mock when no credentials) ---
    origin = "New York"
    origin_code = _airport_code(origin)
    dest_code = _airport_code(cities[0])
    raw_flights = _amadeus_flights_fn(origin_code, dest_code, start, end, travelers)
    if not raw_flights or (isinstance(raw_flights, list) and raw_flights and "error" in raw_flights[0]):
        flights = generate_mock_flights(origin, cities[0], start, end, travelers)
    elif _is_mock_flight(raw_flights[0]):
        # Already in DB-compatible format (mock data or pre-normalised)
        flights = raw_flights
    else:
        # Live Amadeus format → normalise to DB schema
        flights = _normalize_amadeus_flights(raw_flights, origin, cities[0])
        if not flights:
            flights = generate_mock_flights(origin, cities[0], start, end, travelers)

    # --- Accommodations via Amadeus (falls back to mock when no credentials) ---
    accommodations: list[dict] = []
    for city in cities:
        city_code = _city_iata(city)
        raw_hotels = _amadeus_hotels_fn(city_code, start, end, travelers, "hotel")
        if not raw_hotels or (isinstance(raw_hotels, list) and raw_hotels and "error" in raw_hotels[0]):
            hotels = generate_mock_accommodations(city, start, end, travelers)[:3]
        elif _is_mock_accom(raw_hotels[0]):
            hotels = raw_hotels[:3]
        else:
            # Live Amadeus format → normalise to DB schema
            hotels = _normalize_amadeus_hotels(raw_hotels, city, start, end)[:3]
            if not hotels:
                hotels = generate_mock_accommodations(city, start, end, travelers)[:3]
        accommodations.extend(hotels[:3])

    # --- Parse itinerary ---
    itinerary: list[dict] = []
    try:
        itin_raw = itinerary_task.output.raw if itinerary_task.output else "[]"
        parsed_itin = _safe_json_parse(itin_raw)
        if isinstance(parsed_itin, list) and len(parsed_itin) > 0:
            itinerary = parsed_itin
            for day in itinerary:
                city_name = day.get("city", dest)
                for i, item in enumerate(day.get("items", [])):
                    item.setdefault("id", f"day{day.get('day_number', 0)}_item{i}")
                    item.setdefault("status", "planned")
                    item.setdefault("delayed_to_day", None)
                    item.setdefault("is_ai_suggested", 1)

                    # Normalise cost fields
                    if "cost_usd" not in item:
                        raw_cost = item.pop("cost", 0)
                        item["cost_usd"] = raw_cost if isinstance(raw_cost, (int, float)) else 0
                    item.setdefault("cost_local", f"${item['cost_usd']}")
                    item.setdefault("currency", "USD")
                    # Keep legacy 'cost' key pointing to USD for DB compat
                    item["cost"] = item["cost_usd"]

                    # Ensure Google Maps link
                    if not item.get("google_maps_url"):
                        loc = item.get("location", item.get("title", city_name))
                        item["google_maps_url"] = _gmaps_url(loc, city_name)
    except Exception:
        pass

    if not itinerary:
        itinerary = _build_fallback_itinerary(cities, duration, start)

    summary = f"Planned {duration} days across {', '.join(cities)}"

    return {
        "cities": cities,
        "flights": flights,
        "accommodations": accommodations,
        "itinerary": itinerary,
        "is_country_level": is_country,
        "planning_summary": summary,
    }


def _build_fallback_itinerary(
    cities: list[str], duration: int, start_date: str
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
    """High-level wrapper around the CrewAI planning crew."""

    @staticmethod
    def plan_trip(trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full planning crew synchronously and return the result."""
        agents = _build_agents()
        tasks = _build_tasks(trip_data, agents)

        crew = Crew(
            agents=list(agents),
            tasks=tasks,
            process=Process.sequential,
            verbose=VERBOSE,
            tracing=TRACING,
            memory=True,  # enables memory
            cache=True,    # enables tool result caching
        )
        crew.kickoff()
        return _parse_crew_result(tasks, trip_data)

    @staticmethod
    def plan_trip_stream(trip_data: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields SSE progress events as the crew executes."""
        progress_events: list[dict] = []

        agent_order = [
            "DestinationResearcher",
            "CitySelector",
            "FlightFinder",
            "AccommodationFinder",
            "ItineraryPlanner",
        ]

        agent_start_messages = {
            "DestinationResearcher": f"Researching {trip_data['destination']}...",
            "CitySelector": f"Selecting cities in {trip_data['destination']}...",
            "FlightFinder": "Searching for flights via Amadeus...",
            "AccommodationFinder": "Finding accommodations via Amadeus...",
            "ItineraryPlanner": "Building your day-by-day itinerary...",
        }

        def on_progress(event: dict):
            progress_events.append(event)

        agents = _build_agents()
        tasks = _build_tasks(trip_data, agents, on_progress=on_progress)

        crew = Crew(
            agents=list(agents),
            tasks=tasks,
            process=Process.sequential,
            verbose=VERBOSE,
            tracing=TRACING,
            memory=True,
            cache=True,
        )

        import threading
        import time

        result_holder: dict = {"done": False, "error": None}

        def run_crew():
            try:
                crew.kickoff()
                result_holder["done"] = True
            except Exception as exc:
                result_holder["error"] = exc
                result_holder["done"] = True

        thread = threading.Thread(target=run_crew, daemon=True)
        thread.start()

        yielded_agents: set = set()
        started_agents: set = set()

        while not result_holder["done"]:
            while progress_events:
                event = progress_events.pop(0)
                agent_name = event.get("agent", "")
                if agent_name not in started_agents:
                    started_agents.add(agent_name)
                    yield {
                        "type": "progress",
                        "agent": agent_name,
                        "status": "running",
                        "message": agent_start_messages.get(agent_name, f"{agent_name} working..."),
                    }
                yielded_agents.add(agent_name)
                yield event

            for agent_name in agent_order:
                if agent_name not in started_agents and agent_name not in yielded_agents:
                    idx = agent_order.index(agent_name)
                    all_prev_done = all(a in yielded_agents for a in agent_order[:idx])
                    if all_prev_done or idx == 0:
                        started_agents.add(agent_name)
                        yield {
                            "type": "progress",
                            "agent": agent_name,
                            "status": "running",
                            "message": agent_start_messages.get(agent_name, f"{agent_name} working..."),
                        }
                    break

            time.sleep(0.5)

        while progress_events:
            event = progress_events.pop(0)
            agent_name = event.get("agent", "")
            if agent_name not in started_agents:
                started_agents.add(agent_name)
                yield {
                    "type": "progress",
                    "agent": agent_name,
                    "status": "running",
                    "message": agent_start_messages.get(agent_name, f"{agent_name} working..."),
                }
            yield event

        if result_holder.get("error"):
            yield {
                "type": "error",
                "agent": "Orchestrator",
                "status": "error",
                "message": str(result_holder["error"]),
            }
            return

        plan_data = _parse_crew_result(tasks, trip_data)

        yield {
            "type": "complete",
            "agent": "Orchestrator",
            "status": "complete",
            "message": "Trip planning complete!",
            "plan": plan_data,
        }

    @staticmethod
    def _is_likely_country(destination: str) -> bool:
        return _is_likely_country(destination)


# Singleton consumed by main.py via `from agents import planning_agent`
planning_agent = TripPlanner()
