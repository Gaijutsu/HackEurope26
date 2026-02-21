"""
Unit tests for agents/FlightAgent.py

Tool functions are tested via their .func attribute to bypass the crewai
StructuredTool wrapper and test the underlying logic directly.
"""
import pytest
from unittest.mock import MagicMock, patch

import FlightAgent as fa

# Unwrap the crewai @tool decorator to get the raw callable
search_flights_fn = fa.search_flights.func


class TestSearchFlightsMockFallback:
    """When AMADEUS_CLIENT_ID is not set, tools should fall back to mock data."""

    def test_returns_mock_data(self):
        with patch("FlightAgent._has_credentials", False), \
             patch("FlightAgent.generate_mock_flights", return_value=[{"id": "m1"}]) as mock_gen:
            result = search_flights_fn("LHR", "CDG", "2026-06-01", "2026-06-08", 2)
            assert result == [{"id": "m1"}]
            mock_gen.assert_called_once_with(
                "LHR", "CDG", "2026-06-01",
                return_date="2026-06-08",
                num_travelers=2,
            )

    def test_empty_return_date_passed_as_none(self):
        with patch("FlightAgent._has_credentials", False), \
             patch("FlightAgent.generate_mock_flights", return_value=[]) as mock_gen:
            search_flights_fn("LHR", "CDG", "2026-06-01", "", 1)
            mock_gen.assert_called_once_with(
                "LHR", "CDG", "2026-06-01",
                return_date=None,
                num_travelers=1,
            )


class TestSearchFlightsAmadeus:
    """When credentials are present, tools should call the Amadeus API."""

    def test_calls_amadeus_with_correct_params(self):
        mock_resp = MagicMock()
        mock_resp.data = [{"type": "flight-offer"}]

        with patch("FlightAgent._has_credentials", True), \
             patch.object(fa._amadeus.shopping.flight_offers_search, "get", return_value=mock_resp) as mock_get:
            result = search_flights_fn("LHR", "CDG", "2026-06-01", "2026-06-08", 2)

            mock_get.assert_called_once_with(
                originLocationCode="LHR",
                destinationLocationCode="CDG",
                departureDate="2026-06-01",
                returnDate="2026-06-08",
                adults=2,
                currencyCode="USD",
                max=10,
            )
            assert result == [{"type": "flight-offer"}]

    def test_omits_return_date_for_one_way(self):
        mock_resp = MagicMock()
        mock_resp.data = []

        with patch("FlightAgent._has_credentials", True), \
             patch.object(fa._amadeus.shopping.flight_offers_search, "get", return_value=mock_resp) as mock_get:
            search_flights_fn("LHR", "CDG", "2026-06-01", "", 1)
            assert "returnDate" not in mock_get.call_args.kwargs

    def test_returns_error_dict_on_response_error(self):
        from amadeus import ResponseError

        with patch("FlightAgent._has_credentials", True), \
             patch.object(
                 fa._amadeus.shopping.flight_offers_search, "get",
                 side_effect=ResponseError(MagicMock())
             ):
            result = search_flights_fn("BAD", "CDG", "2026-06-01", "", 1)
            assert len(result) == 1
            assert "error" in result[0]


class TestBuildGoal:
    def test_no_sustainability_for_normal_vibe(self, info):
        goal = fa._build_goal(info)
        assert "sustain" not in goal.lower()
        assert "emission" not in goal.lower()

    def test_includes_sustainability_for_eco_vibe(self, eco_info):
        goal = fa._build_goal(eco_info)
        assert "sustain" in goal.lower() or "emission" in goal.lower()

    def test_picks_up_sustainability_keyword_in_other(self):
        from datetime import date
        from PlanningInfo import PlanningInfo
        info = PlanningInfo(
            number_travelers=1,
            dates=(date(2026, 6, 1), date(2026, 6, 5)),
            city="Rome",
            vibe="food",
            budget=(500, 1000),
            accom_type="hotel",
            food_requirements=[],
            other="prefer carbon neutral airlines",
        )
        goal = fa._build_goal(info)
        assert "sustain" in goal.lower() or "emission" in goal.lower()


class TestRun:
    def test_kickoff_called_and_result_returned(self, info):
        with patch("FlightAgent.Crew") as MockCrew:
            MockCrew.return_value.kickoff.return_value = "ranked flights"
            result = fa.run(info, "LHR")
            assert result == "ranked flights"
            MockCrew.return_value.kickoff.assert_called_once()

    def test_task_description_contains_origin_and_destination(self, info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("FlightAgent.Crew", side_effect=capture):
            fa.run(info, "LHR")

        desc = captured["task"].description
        assert "LHR" in desc
        assert "Paris" in desc

    def test_task_description_includes_sustainability_for_eco_vibe(self, eco_info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("FlightAgent.Crew", side_effect=capture):
            fa.run(eco_info, "LHR")

        assert "sustain" in captured["task"].description.lower()

    def test_task_description_excludes_sustainability_for_normal_vibe(self, info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("FlightAgent.Crew", side_effect=capture):
            fa.run(info, "LHR")

        assert "sustain" not in captured["task"].description.lower()

    def test_task_description_shows_multi_city(self, multi_city_info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("FlightAgent.Crew", side_effect=capture):
            fa.run(multi_city_info, "JFK")

        desc = captured["task"].description
        assert "London" in desc
        assert "Amsterdam" in desc
