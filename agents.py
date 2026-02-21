"""
CrewAI Multi-Agent Trip Planner

Orchestrates a crew of specialized agents that collaborate to plan trips:
  1. DestinationResearcher  - web search + LLM for destination intel
  2. CitySelector           - picks cities for country-level trips
  3. FlightFinder           - wraps mock flight data
  4. AccommodationFinder    - wraps mock accommodation data
  5. ItineraryPlanner       - builds the final day-by-day plan

The agents share context through CrewAI's task dependency system so that
each agent can build on the work of previous agents.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

from crewai import Agent, Crew, Process, Task
from crewai.tasks.task_output import TaskOutput

from mock_data import (
    generate_mock_flights,
    generate_mock_accommodations,
    get_city_info,
)

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


def _fallback_day_plan(city: str, day_number: int) -> list[dict]:
    return [
        {"start_time": "08:30", "duration_minutes": 60, "title": "Breakfast",
         "description": "Start the day at a local cafe", "item_type": "meal",
         "location": f"{city} Cafe", "cost": 15, "notes": ""},
        {"start_time": "10:00", "duration_minutes": 150, "title": f"Explore {city}",
         "description": "Walk around the city center", "item_type": "attraction",
         "location": f"{city} City Center", "cost": 0, "notes": ""},
        {"start_time": "12:30", "duration_minutes": 60, "title": "Lunch",
         "description": "Local restaurant", "item_type": "meal",
         "location": f"{city} Restaurant District", "cost": 25, "notes": ""},
        {"start_time": "14:00", "duration_minutes": 180, "title": f"{city} Main Attraction",
         "description": "Visit the top attraction", "item_type": "attraction",
         "location": f"{city} Main Attraction", "cost": 20, "notes": ""},
        {"start_time": "18:00", "duration_minutes": 90, "title": "Dinner",
         "description": "Evening meal", "item_type": "meal",
         "location": f"{city} Dining Area", "cost": 35, "notes": ""},
    ]


# ---------------------------------------------------------------------------
# LLM model helper
# ---------------------------------------------------------------------------

def _llm_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# CrewAI Agent definitions
# ---------------------------------------------------------------------------

def _build_agents():
    """Create the five specialized agents."""

    destination_researcher = Agent(
        role="Destination Researcher",
        goal="Research travel destinations thoroughly and provide practical information for trip planning",
        backstory=(
            "You are a seasoned travel researcher with extensive knowledge of destinations worldwide. "
            "You excel at uncovering practical travel information including top attractions, local food, "
            "transport tips, and budget considerations. You always provide structured, actionable information."
        ),
        llm=_llm_name(),
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )

    city_selector = Agent(
        role="City Selection Specialist",
        goal="Select the optimal cities to visit within a country for multi-city trips",
        backstory=(
            "You are a travel routing expert who knows which cities pair well together and how to "
            "create logical, efficient multi-city itineraries. You consider travel distances, "
            "city highlights, and traveler interests to select the best route."
        ),
        llm=_llm_name(),
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )

    flight_finder = Agent(
        role="Flight Search Specialist",
        goal="Find the best flight options for the trip",
        backstory=(
            "You are a flight search expert who finds the best air travel options. "
            "You analyze available flights and present clear options for travelers."
        ),
        llm=_llm_name(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )

    accommodation_finder = Agent(
        role="Accommodation Search Specialist",
        goal="Find the best places to stay for each city in the trip",
        backstory=(
            "You are an accommodation expert who matches travelers with the perfect "
            "places to stay based on budget, location, and amenities."
        ),
        llm=_llm_name(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )

    itinerary_planner = Agent(
        role="Itinerary Planner",
        goal="Create a detailed day-by-day itinerary using all gathered information",
        backstory=(
            "You are an expert itinerary designer who creates cohesive, realistic day-by-day "
            "travel plans. You synthesize destination research, city information, and traveler "
            "preferences to build plans with proper timing, varied activities, and meals. "
            "You always ensure plans are practical and enjoyable."
        ),
        llm=_llm_name(),
        verbose=False,
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
# CrewAI Task builders (parameterized per trip)
# ---------------------------------------------------------------------------

def _build_tasks(
    trip_data: Dict[str, Any],
    agents: tuple,
    on_progress: Optional[callable] = None,
) -> list[Task]:
    """
    Build the five sequential tasks for a trip, wiring context dependencies
    so agents can collaborate.
    """
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

    # Callbacks that fire when each task finishes
    def _make_callback(agent_name: str, done_msg: str):
        def cb(output: TaskOutput):
            if on_progress:
                on_progress({
                    "type": "progress",
                    "agent": agent_name,
                    "status": "done",
                    "message": done_msg,
                })
        return cb

    # --- Task 1: Destination Research ---
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

    # --- Task 2: City Selection ---
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
        callback=_make_callback("CitySelector",
                                f"Cities selected for {dest}"),
    )

    # --- Task 3: Flight Search ---
    flight_task = Task(
        description=f"""Find flights for a trip to the destination cities.

Trip details:
- Departure date: {start}
- Return date: {end}
- Number of travelers: {travelers}
- Origin: New York

Using the cities selected in the context, search for flights to the first city.

IMPORTANT: Your output MUST be a valid JSON object with this structure:
{{
  "origin": "New York",
  "destination_city": "<first city from context>",
  "departure_date": "{start}",
  "return_date": "{end}",
  "num_travelers": {travelers}
}}

Return ONLY valid JSON.""",
        expected_output="A JSON object with flight search parameters.",
        agent=flight_agent,
        context=[city_task],
        callback=_make_callback("FlightFinder", "Flight search complete"),
    )

    # --- Task 4: Accommodation Search ---
    accommodation_task = Task(
        description=f"""Find accommodations for each city in the trip.

Trip dates: {start} to {end}
Number of guests: {travelers}
Budget level: {budget}

Using the cities from context, search for accommodations in each city.

IMPORTANT: Your output MUST be a valid JSON object with this structure:
{{
  "cities": ["<cities from context>"],
  "check_in": "{start}",
  "check_out": "{end}",
  "num_guests": {travelers},
  "budget_level": "{budget}"
}}

Return ONLY valid JSON.""",
        expected_output="A JSON object with accommodation search parameters for each city.",
        agent=accommodation_agent,
        context=[city_task, research_task],
        callback=_make_callback("AccommodationFinder", "Accommodation search complete"),
    )

    # --- Task 5: Itinerary Planning ---
    itinerary_task = Task(
        description=f"""Create a detailed day-by-day itinerary for a {duration}-day trip.

Using ALL the context from previous tasks (destination research, selected cities,
flights, and accommodations), create a complete itinerary.

Trip details:
- Destination: {dest}
- Dates: {start} to {end} ({duration} days)
- Interests: {interests}
- Dietary restrictions: {dietary}
- Budget: {budget}
- Number of travelers: {travelers}

For each day, create 5-7 activities. Return a JSON array where each element is:
{{
  "day_number": 1,
  "date": "YYYY-MM-DD",
  "city": "CityName",
  "items": [
    {{
      "start_time": "09:00",
      "duration_minutes": 120,
      "title": "Activity name",
      "description": "Brief description",
      "item_type": "attraction|meal|transport|free_time",
      "location": "Specific place",
      "cost": 25,
      "notes": "Optional notes"
    }}
  ]
}}

Rules:
- Include breakfast, lunch, and dinner each day
- Respect dietary restrictions
- Day 1 should include arrival activities
- Last day should include departure activities
- Use realistic timing
- Distribute cities evenly across days

Return ONLY valid JSON array.""",
        expected_output="A JSON array of day objects, each containing day_number, date, city, and items array.",
        agent=planner_agent,
        context=[research_task, city_task, flight_task, accommodation_task],
        callback=_make_callback("ItineraryPlanner", "Itinerary planning complete"),
    )

    return [research_task, city_task, flight_task, accommodation_task, itinerary_task]


# ---------------------------------------------------------------------------
# Result parser - extract structured data from crew output
# ---------------------------------------------------------------------------

def _parse_crew_result(
    tasks: list[Task],
    trip_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    After the crew finishes, parse each task's output to build the
    structured plan dict that the rest of the app expects.
    """
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

    # --- Generate flights from mock data ---
    origin = "New York"
    flights = generate_mock_flights(
        origin, cities[0], start, end, travelers,
    )

    # --- Generate accommodations from mock data ---
    accommodations: list[dict] = []
    for city in cities:
        city_accs = generate_mock_accommodations(city, start, end, travelers)
        accommodations.extend(city_accs[:3])

    # --- Parse itinerary ---
    itinerary: list[dict] = []
    try:
        itin_raw = itinerary_task.output.raw if itinerary_task.output else "[]"
        parsed_itin = _safe_json_parse(itin_raw)
        if isinstance(parsed_itin, list) and len(parsed_itin) > 0:
            itinerary = parsed_itin
            # Ensure all items have required fields
            for day in itinerary:
                for i, item in enumerate(day.get("items", [])):
                    item.setdefault("id", f"day{day.get('day_number', 0)}_item{i}")
                    item.setdefault("status", "planned")
                    item.setdefault("delayed_to_day", None)
                    item.setdefault("is_ai_suggested", 1)
    except Exception:
        pass

    # Fallback: build itinerary from scratch if parsing failed
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
    """Build a basic itinerary when the LLM output cannot be parsed."""
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
# Public API consumed by FastAPI
# ---------------------------------------------------------------------------

class TripPlanner:
    """
    High-level wrapper around the CrewAI planning crew.
    Supports both synchronous (plan_trip) and streaming (plan_trip_stream).
    """

    @staticmethod
    def plan_trip(trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full planning crew synchronously and return the result."""
        agents = _build_agents()
        tasks = _build_tasks(trip_data, agents)

        crew = Crew(
            agents=list(agents),
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
        )

        crew.kickoff()

        return _parse_crew_result(tasks, trip_data)

    @staticmethod
    def plan_trip_stream(trip_data: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """
        Generator that yields progress events as the crew executes.
        Each yield is a dict with agent progress info.
        The final yield has type="complete" and includes the full plan.
        """
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
            "FlightFinder": "Searching for flights...",
            "AccommodationFinder": "Finding accommodations...",
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
            verbose=False,
        )

        # Yield start events for each agent, then run the crew,
        # and yield completion events as they come in.
        # Since CrewAI runs sequentially, we track task completion
        # via callbacks and yield progress between tasks.

        # We need to run the crew in a way that lets us yield.
        # CrewAI doesn't natively support generator-style streaming,
        # so we run it in a thread and poll for progress events.

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

        yielded_agents = set()
        started_agents = set()

        while not result_holder["done"]:
            # Check for new progress events from callbacks
            while progress_events:
                event = progress_events.pop(0)
                agent_name = event.get("agent", "")

                # If this agent hasn't been started yet, yield a "running" event
                if agent_name not in started_agents:
                    started_agents.add(agent_name)
                    yield {
                        "type": "progress",
                        "agent": agent_name,
                        "status": "running",
                        "message": agent_start_messages.get(
                            agent_name, f"{agent_name} working..."
                        ),
                    }

                # Yield the done event
                yielded_agents.add(agent_name)
                yield event

            # Guess which agent is currently running based on what's completed
            for agent_name in agent_order:
                if agent_name not in started_agents and agent_name not in yielded_agents:
                    # Check if all previous agents are done
                    idx = agent_order.index(agent_name)
                    all_prev_done = all(
                        a in yielded_agents for a in agent_order[:idx]
                    )
                    if all_prev_done or idx == 0:
                        started_agents.add(agent_name)
                        yield {
                            "type": "progress",
                            "agent": agent_name,
                            "status": "running",
                            "message": agent_start_messages.get(
                                agent_name, f"{agent_name} working..."
                            ),
                        }
                    break

            time.sleep(0.5)

        # Drain remaining progress events
        while progress_events:
            event = progress_events.pop(0)
            agent_name = event.get("agent", "")
            if agent_name not in started_agents:
                started_agents.add(agent_name)
                yield {
                    "type": "progress",
                    "agent": agent_name,
                    "status": "running",
                    "message": agent_start_messages.get(
                        agent_name, f"{agent_name} working..."
                    ),
                }
            yield event

        # Check for errors
        if result_holder.get("error"):
            yield {
                "type": "error",
                "agent": "Orchestrator",
                "status": "error",
                "message": str(result_holder["error"]),
            }
            return

        # Parse final result
        plan_data = _parse_crew_result(tasks, trip_data)

        # Yield final complete event
        yield {
            "type": "complete",
            "agent": "Orchestrator",
            "status": "complete",
            "message": "Trip planning complete!",
            "plan": plan_data,
        }

    @staticmethod
    def _is_likely_country(destination: str) -> bool:
        """Backward-compatible static helper."""
        return _is_likely_country(destination)


# Backward-compatible singleton
planning_agent = TripPlanner()
