"""
Unit tests for agents/planning_agent.py

Tests cover:
- Pure helper functions (_is_likely_country, _safe_json_parse, _calc_duration)
- Fallback itinerary builder
- IATA code helpers
- TripPlanner.plan_trip() with mocked Crew
- TripPlanner.plan_trip_stream() with mocked Crew
- _parse_crew_result() with mocked task outputs
"""
import json
import pytest
from unittest.mock import MagicMock, patch

import planning_agent as pa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_TRIP = {
    "destination": "Paris",
    "origin_city": "New York",
    "start_date": "2026-06-01",
    "end_date": "2026-06-08",
    "num_travelers": 2,
    "interests": ["Culture", "Food"],
    "dietary_restrictions": ["vegetarian"],
    "budget_level": "mid",
}

COUNTRY_TRIP = {**SAMPLE_TRIP, "destination": "Japan"}


def _mock_tasks(city_json="[\"Paris\"]", itin_json="[]"):
    """Build five mock Task objects with .output.raw set."""
    def make_task(raw):
        t = MagicMock()
        t.output.raw = raw
        return t

    return [
        make_task("{}"),           # research
        make_task(city_json),      # city
        make_task("{}"),           # flight
        make_task("{}"),           # accommodation
        make_task(itin_json),      # itinerary
    ]


# ---------------------------------------------------------------------------
# _is_likely_country
# ---------------------------------------------------------------------------

class TestIsLikelyCountry:
    def test_known_country_returns_true(self):
        assert pa._is_likely_country("Japan") is True

    def test_city_returns_false(self):
        assert pa._is_likely_country("Paris") is False

    def test_unknown_string_returns_false(self):
        assert pa._is_likely_country("Randomville") is False

    def test_strips_whitespace(self):
        assert pa._is_likely_country("  France  ") is True


# ---------------------------------------------------------------------------
# _safe_json_parse
# ---------------------------------------------------------------------------

class TestSafeJsonParse:
    def test_plain_json_object(self):
        assert pa._safe_json_parse('{"key": "value"}') == {"key": "value"}

    def test_plain_json_array(self):
        assert pa._safe_json_parse('["Paris", "Lyon"]') == ["Paris", "Lyon"]

    def test_strips_json_fence(self):
        text = '```json\n["Tokyo"]\n```'
        assert pa._safe_json_parse(text) == ["Tokyo"]

    def test_strips_plain_fence(self):
        text = '```\n{"a": 1}\n```'
        assert pa._safe_json_parse(text) == {"a": 1}

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            pa._safe_json_parse("not json at all")


# ---------------------------------------------------------------------------
# _calc_duration
# ---------------------------------------------------------------------------

class TestCalcDuration:
    def test_seven_night_trip_is_eight_days(self):
        assert pa._calc_duration("2026-06-01", "2026-06-08") == 8

    def test_same_day_is_one(self):
        assert pa._calc_duration("2026-06-01", "2026-06-01") == 1

    def test_one_night_is_two_days(self):
        assert pa._calc_duration("2026-06-01", "2026-06-02") == 2


# ---------------------------------------------------------------------------
# IATA helpers
# ---------------------------------------------------------------------------

class TestIataHelpers:
    def test_known_city_airport(self):
        assert pa._airport_code("Paris") == "CDG"

    def test_unknown_city_falls_back_to_mock_data(self):
        # Amadeus lookup returns None for unknown cities, falls back to mock
        with patch.object(pa, "_amadeus_location_lookup", return_value=None):
            result = pa._airport_code("Randomville")
        assert isinstance(result, str) and len(result) == 3

    def test_known_city_iata_city_code(self):
        assert pa._city_iata("London") == "LON"

    def test_unknown_city_iata_falls_back(self):
        with patch.object(pa, "_amadeus_location_lookup", return_value=None):
            result = pa._city_iata("Randomville")
        # Falls back to first-3-letters uppercase
        assert result == "RAN"


# ---------------------------------------------------------------------------
# _build_fallback_itinerary
# ---------------------------------------------------------------------------

class TestBuildFallbackItinerary:
    def test_correct_number_of_days(self):
        itin = pa._build_fallback_itinerary(["Paris"], 5, "2026-06-01")
        assert len(itin) == 5

    def test_days_are_numbered_sequentially(self):
        itin = pa._build_fallback_itinerary(["Paris"], 3, "2026-06-01")
        assert [d["day_number"] for d in itin] == [1, 2, 3]

    def test_multi_city_spreads_days(self):
        itin = pa._build_fallback_itinerary(["Paris", "Lyon"], 4, "2026-06-01")
        cities = [d["city"] for d in itin]
        assert "Paris" in cities and "Lyon" in cities

    def test_each_day_has_items(self):
        itin = pa._build_fallback_itinerary(["Tokyo"], 2, "2026-06-01")
        for day in itin:
            assert len(day["items"]) > 0

    def test_items_have_required_fields(self):
        itin = pa._build_fallback_itinerary(["Tokyo"], 1, "2026-06-01")
        for item in itin[0]["items"]:
            assert "start_time" in item
            assert "title" in item
            assert "status" in item
            assert item["status"] == "planned"


# ---------------------------------------------------------------------------
# _parse_crew_result
# ---------------------------------------------------------------------------

class TestParseCrewResult:
    def test_returns_required_keys(self):
        tasks = _mock_tasks()
        with patch.object(pa, "_amadeus_flights_fn", return_value=[{"error": "no creds"}]), \
             patch.object(pa, "_amadeus_hotels_fn", return_value=[{"error": "no creds"}]), \
             patch("planning_agent.generate_mock_flights", return_value=[{"flight_type": "outbound", "airline": "Air", "flight_number": "AA1"}]), \
             patch("planning_agent.generate_mock_accommodations", return_value=[{"name": "Hotel", "price_per_night": 100, "check_in_date": "2026-06-01"}]):
            result = pa._parse_crew_result(tasks, SAMPLE_TRIP)

        assert "cities" in result
        assert "flights" in result
        assert "accommodations" in result
        assert "itinerary" in result
        assert "planning_summary" in result
        assert "is_country_level" in result

    def test_uses_fallback_itinerary_when_llm_output_empty(self):
        tasks = _mock_tasks(itin_json="[]")
        with patch.object(pa, "_amadeus_flights_fn", return_value=[{"error": "x"}]), \
             patch.object(pa, "_amadeus_hotels_fn", return_value=[{"error": "x"}]), \
             patch("planning_agent.generate_mock_flights", return_value=[]), \
             patch("planning_agent.generate_mock_accommodations", return_value=[]):
            result = pa._parse_crew_result(tasks, SAMPLE_TRIP)

        assert len(result["itinerary"]) > 0

    def test_city_parse_failure_falls_back_to_default_for_country(self):
        tasks = _mock_tasks(city_json="INVALID JSON")
        with patch.object(pa, "_amadeus_flights_fn", return_value=[{"error": "x"}]), \
             patch.object(pa, "_amadeus_hotels_fn", return_value=[{"error": "x"}]), \
             patch("planning_agent.generate_mock_flights", return_value=[]), \
             patch("planning_agent.generate_mock_accommodations", return_value=[]):
            result = pa._parse_crew_result(tasks, COUNTRY_TRIP)

        # Should fall back to Japan's default city list
        assert result["cities"] == ["Tokyo", "Kyoto", "Osaka"]

    def test_uses_amadeus_flights_when_mock_format_returned(self):
        mock_flights = [{"flight_type": "outbound", "airline": "Air France",
                         "flight_number": "AF001", "from_airport": "JFK",
                         "to_airport": "CDG", "departure_datetime": "2026-06-01T10:00",
                         "arrival_datetime": "2026-06-01T22:00", "duration_minutes": 480,
                         "price": 600, "currency": "USD", "booking_url": "http://example.com",
                         "status": "suggested"}]
        tasks = _mock_tasks()
        with patch.object(pa, "_amadeus_flights_fn", return_value=mock_flights), \
             patch.object(pa, "_amadeus_hotels_fn", return_value=[{"error": "x"}]), \
             patch("planning_agent.generate_mock_accommodations", return_value=[]):
            result = pa._parse_crew_result(tasks, SAMPLE_TRIP)

        assert result["flights"] == mock_flights


# ---------------------------------------------------------------------------
# TripPlanner.plan_trip
# ---------------------------------------------------------------------------

class TestTripPlannerPlanTrip:
    def test_returns_plan_dict(self):
        mock_plan = {
            "cities": ["Paris"],
            "flights": [],
            "accommodations": [],
            "itinerary": [],
            "is_country_level": False,
            "planning_summary": "Planned 8 days across Paris",
        }
        with patch("planning_agent._build_agents", return_value=(MagicMock(),) * 5), \
             patch("planning_agent._build_tasks", return_value=[MagicMock()] * 5), \
             patch("planning_agent.Crew") as MockCrew, \
             patch("planning_agent._parse_crew_result", return_value=mock_plan):
            MockCrew.return_value.kickoff.return_value = None
            result = pa.TripPlanner.plan_trip(SAMPLE_TRIP)

        assert result == mock_plan

    def test_crew_kickoff_is_called(self):
        with patch("planning_agent._build_agents", return_value=(MagicMock(),) * 5), \
             patch("planning_agent._build_tasks", return_value=[MagicMock()] * 5), \
             patch("planning_agent.Crew") as MockCrew, \
             patch("planning_agent._parse_crew_result", return_value={}):
            pa.TripPlanner.plan_trip(SAMPLE_TRIP)
            # 3-phase execution: phase1 + phase2_flight + phase2_accom + phase3 = at least 3 Crew()
            assert MockCrew.return_value.kickoff.call_count >= 3

    def test_is_likely_country_static_method(self):
        assert pa.TripPlanner._is_likely_country("Japan") is True
        assert pa.TripPlanner._is_likely_country("Paris") is False


# ---------------------------------------------------------------------------
# TripPlanner.plan_trip_stream
# ---------------------------------------------------------------------------

class TestTripPlannerStream:
    def _collect(self, trip_data=None):
        """Run plan_trip_stream and collect all yielded events."""
        events = []
        for e in pa.TripPlanner.plan_trip_stream(trip_data or SAMPLE_TRIP):
            events.append(e)
            if e.get("type") in ("complete", "error"):
                break
        return events

    def test_yields_complete_event(self):
        mock_plan = {"cities": ["Paris"], "flights": [], "accommodations": [],
                     "itinerary": [],
                     "is_country_level": False, "planning_summary": ""}

        with patch("planning_agent._build_agents", return_value=(MagicMock(),) * 5), \
             patch("planning_agent._build_tasks", return_value=[MagicMock()] * 5), \
             patch("planning_agent.Crew") as MockCrew, \
             patch("planning_agent._parse_crew_result", return_value=mock_plan):
            MockCrew.return_value.kickoff.return_value = None
            events = self._collect()

        types = [e["type"] for e in events]
        assert "complete" in types

    def test_complete_event_contains_plan(self):
        mock_plan = {"cities": ["Paris"], "flights": [], "accommodations": [],
                     "itinerary": [],
                     "is_country_level": False, "planning_summary": "done"}

        with patch("planning_agent._build_agents", return_value=(MagicMock(),) * 5), \
             patch("planning_agent._build_tasks", return_value=[MagicMock()] * 5), \
             patch("planning_agent.Crew") as MockCrew, \
             patch("planning_agent._parse_crew_result", return_value=mock_plan):
            MockCrew.return_value.kickoff.return_value = None
            events = self._collect()

        complete = next(e for e in events if e["type"] == "complete")
        assert complete["plan"] == mock_plan

    def test_yields_error_event_on_crew_exception(self):
        with patch("planning_agent._build_agents", return_value=(MagicMock(),) * 5), \
             patch("planning_agent._build_tasks", return_value=[MagicMock()] * 5), \
             patch("planning_agent.Crew") as MockCrew:
            MockCrew.return_value.kickoff.side_effect = RuntimeError("LLM exploded")
            events = self._collect()

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM exploded" in error_events[0]["message"]
