import os

from amadeus import Client, ResponseError
from crewai import Agent, Crew, Task
from crewai.tools import tool

from mock_data import generate_mock_accommodations
from PlanningInfo import PlanningInfo

_amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID", ""),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET", ""),
)

_has_credentials = bool(os.getenv("AMADEUS_CLIENT_ID"))


@tool("Search Amadeus Hotels")
def search_hotels(
    city_code: str, check_in: str, check_out: str, adults: int, accom_type: str
) -> list:
    """Search for hotels via the Amadeus Hotel Search API.
    city_code must be an IATA city code (e.g. LON, PAR, NYC).
    Dates must be YYYY-MM-DD format.
    accom_type filters results (e.g. HOTEL, APARTMENT, HOSTEL).
    """
    if not _has_credentials:
        return generate_mock_accommodations(city_code, check_in, check_out, num_guests=adults)
    try:
        # Step 1: get hotel IDs in the city
        hotels_resp = _amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code,
            hotelSource="ALL",
        )
        hotel_ids = [h["hotelId"] for h in hotels_resp.data[:20]]  # cap at 20

        # Step 2: fetch live offers for those hotels
        offers_resp = _amadeus.shopping.hotel_offers_search.get(
            hotelIds=hotel_ids,
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=adults,
            currencyCode="USD",
        )
        return offers_resp.data
    except ResponseError as e:
        return [{"error": str(e)}]


accom_agent = Agent(
    role="Accommodation Search Specialist",
    goal=(
        "Find the best hotel and accommodation options via Amadeus, "
        "matching the traveler's vibe, budget, and requirements."
    ),
    backstory=(
        "A seasoned hospitality expert who uses the Amadeus GDS to compare hotels "
        "and surface the best value stays for any travel style."
    ),
    tools=[search_hotels],
    verbose=True,
)


def run(info: PlanningInfo, city: str) -> str:
    start, end = info.dates
    lo_night, hi_night = info.budget_per_night()

    task = Task(
        description=(
            f"Find accommodation in {city}.\n"
            f"Check-in: {start}  |  Check-out: {end}  |  Nights: {info.trip_nights()}\n"
            f"Guests: {info.number_travelers}\n"
            f"Preferred type: {info.accom_type}\n"
            f"Budget per night: ${lo_night}–${hi_night}\n"
            f"Food requirements: {', '.join(info.food_requirements) or 'none'}\n"
            f"Vibe: {info.vibe}\n"
            "Use the IATA city code when calling the search tool (e.g. LON for London). "
            "For each accommodation option you find, you must construct a practical booking search URL "
            "(e.g., a Google Hotels or Booking.com search link) using the hotel's exact name, city, and dates. "
            "Rank by value and flag options that best match the preferences."
        ),
        expected_output=(
            "A ranked list of accommodation options, each with: name, type, address, "
            "price per night, total price, rating, key amenities, and a short note on "
            "why it suits the traveler's preferences."
            "AND a direct, clickable URL to search/book this specific hotel (e.g., a Google Hotels link)."
        ),
        agent=accom_agent,
    )

    return Crew(agents=[accom_agent], tasks=[task]).kickoff()
