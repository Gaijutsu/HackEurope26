"""
Unit tests for agents/AccomAgent.py

Tool functions are tested via their .func attribute to bypass the crewai
StructuredTool wrapper and test the underlying logic directly.
"""
import pytest
from unittest.mock import MagicMock, call, patch

import AccomAgent as aa

# Unwrap the crewai @tool decorator to get the raw callable
search_hotels_fn = aa.search_hotels.func


class TestSearchHotelsMockFallback:
    """When AMADEUS_CLIENT_ID is not set, tools should fall back to mock data."""

    def test_returns_mock_data(self):
        with patch("AccomAgent._has_credentials", False), \
             patch("AccomAgent.generate_mock_accommodations", return_value=[{"id": "h1"}]) as mock_gen:
            result = search_hotels_fn("PAR", "2026-06-01", "2026-06-08", 2, "hotel")
            assert result == [{"id": "h1"}]
            mock_gen.assert_called_once_with("PAR", "2026-06-01", "2026-06-08", num_guests=2)


class TestSearchHotelsAmadeus:
    """When credentials are present, tools should perform the two-step Amadeus call."""

    def _make_amadeus_mocks(self, hotel_ids, offers):
        hotels_resp = MagicMock()
        hotels_resp.data = [{"hotelId": hid} for hid in hotel_ids]

        offers_resp = MagicMock()
        offers_resp.data = offers

        return hotels_resp, offers_resp

    def test_fetches_hotel_ids_then_offers(self):
        hotel_ids = ["HLPAR001", "HLPAR002"]
        offers = [{"hotel": {"hotelId": "HLPAR001"}, "offers": []}]
        hotels_resp, offers_resp = self._make_amadeus_mocks(hotel_ids, offers)

        with patch("AccomAgent._has_credentials", True), \
             patch.object(aa._amadeus.reference_data.locations.hotels.by_city, "get", return_value=hotels_resp) as mock_list, \
             patch.object(aa._amadeus.shopping.hotel_offers_search, "get", return_value=offers_resp) as mock_offers:

            result = search_hotels_fn("PAR", "2026-06-01", "2026-06-08", 2, "hotel")

            mock_list.assert_called_once_with(cityCode="PAR", hotelSource="ALL")
            mock_offers.assert_called_once_with(
                hotelIds=hotel_ids,
                checkInDate="2026-06-01",
                checkOutDate="2026-06-08",
                adults=2,
                currencyCode="USD",
            )
            assert result == offers

    def test_caps_hotel_ids_at_20(self):
        many_ids = [f"HLPAR{i:03d}" for i in range(30)]
        hotels_resp, offers_resp = self._make_amadeus_mocks(many_ids, [])

        with patch("AccomAgent._has_credentials", True), \
             patch.object(aa._amadeus.reference_data.locations.hotels.by_city, "get", return_value=hotels_resp), \
             patch.object(aa._amadeus.shopping.hotel_offers_search, "get", return_value=offers_resp) as mock_offers:

            search_hotels_fn("PAR", "2026-06-01", "2026-06-08", 2, "hotel")
            sent_ids = mock_offers.call_args.kwargs["hotelIds"]
            assert len(sent_ids) == 20

    def test_returns_error_dict_on_response_error(self):
        from amadeus import ResponseError

        with patch("AccomAgent._has_credentials", True), \
             patch.object(
                 aa._amadeus.reference_data.locations.hotels.by_city, "get",
                 side_effect=ResponseError(MagicMock())
             ):
            result = search_hotels_fn("BAD", "2026-06-01", "2026-06-08", 2, "hotel")
            assert len(result) == 1
            assert "error" in result[0]


class TestRun:
    def test_kickoff_called_and_result_returned(self, info):
        with patch("AccomAgent.Crew") as MockCrew:
            MockCrew.return_value.kickoff.return_value = "ranked hotels"
            result = aa.run(info, "PAR")
            assert result == "ranked hotels"
            MockCrew.return_value.kickoff.assert_called_once()

    def test_task_description_contains_city_and_dates(self, info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("AccomAgent.Crew", side_effect=capture):
            aa.run(info, "PAR")

        desc = captured["task"].description
        assert "PAR" in desc
        assert "2026-06-01" in desc
        assert "2026-06-08" in desc

    def test_task_description_contains_food_requirements(self, info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("AccomAgent.Crew", side_effect=capture):
            aa.run(info, "PAR")

        assert "vegetarian" in captured["task"].description

    def test_task_description_shows_budget_per_night(self, info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("AccomAgent.Crew", side_effect=capture):
            aa.run(info, "PAR")

        lo, hi = info.budget_per_night()
        desc = captured["task"].description
        assert str(lo) in desc
        assert str(hi) in desc

    def test_task_description_shows_no_food_requirements(self, eco_info):
        captured = {}

        def capture(agents, tasks):
            captured["task"] = tasks[0]
            m = MagicMock()
            m.kickoff.return_value = ""
            return m

        with patch("AccomAgent.Crew", side_effect=capture):
            aa.run(eco_info, "LON")

        assert "none" in captured["task"].description
