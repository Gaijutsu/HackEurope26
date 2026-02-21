import os

from amadeus import Client, ResponseError
from crewai import Agent, Crew, Task
from crewai.tools import tool

from mock_data import generate_mock_flights
from PlanningInfo import PlanningInfo

_amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID", ""),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET", ""),
)

_has_credentials = bool(os.getenv("AMADEUS_CLIENT_ID"))


@tool("Search Amadeus Flights")
def search_flights(
    origin: str, destination: str, departure_date: str, return_date: str, adults: int
) -> list:
    """Search for flights via the Amadeus Flight Offers Search API.
    origin and destination must be IATA airport codes (e.g. LHR, JFK).
    Dates must be YYYY-MM-DD format. Pass an empty string for return_date on one-way trips.
    """
    if not _has_credentials:
        return generate_mock_flights(
            origin, destination, departure_date,
            return_date=return_date or None,
            num_travelers=adults,
        )
    try:
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "USD",
            "max": 10,
        }
        if return_date:
            params["returnDate"] = return_date
        return _amadeus.shopping.flight_offers_search.get(**params).data
    except ResponseError as e:
        return [{"error": str(e)}]


def _build_goal(info: PlanningInfo) -> str:
    base = "Find the best available flights for the trip, balancing price and convenience."
    sustainability_keywords = {"sustainable", "eco", "green", "carbon", "environment"}
    if sustainability_keywords & set(info.vibe.lower().split() + info.other.lower().split()):
        base += " Prioritise low-emission routing and flag sustainability options."
    return base


def run(info: PlanningInfo, origin: str) -> str:
    start, end = info.dates
    destinations = ", ".join(info.get_cities())
    lo, hi = info.budget

    sustainability_keywords = {"sustainable", "eco", "green", "carbon", "environment"}
    wants_sustainability = bool(
        sustainability_keywords & set(info.vibe.lower().split() + info.other.lower().split())
    )

    flight_agent = Agent(
        role="Flight Search Specialist",
        goal=_build_goal(info),
        backstory=(
            "An expert travel agent with years of experience hunting down optimal flights "
            "using the Amadeus GDS. Known for surfacing the best value fares."
        ),
        tools=[search_flights],
        verbose=True,
    )

    task = Task(
        description=(
            f"Find flights from {origin} to {destinations}.\n"
            f"Departure: {start}  |  Return: {end}\n"
            f"Travelers: {info.number_travelers}\n"
            f"Total budget: ${lo}–${hi}\n"
            f"Trip vibe / preferences: {info.vibe}\n"
            + ("Prioritise sustainable, low-emission options.\n" if wants_sustainability else "")
            + "Use IATA airport codes when calling the search tool. "
            "Rank results by value (price vs. quality)."
        ),
        expected_output=(
            "A ranked list of flight options, each with: airline, flight number, "
            "departure/arrival times, price per person, and total price."
            + (" Include a sustainability note for each option." if wants_sustainability else "")
        ),
        agent=flight_agent,
    )

    return Crew(agents=[flight_agent], tasks=[task]).kickoff()
