import sys
import os
import pytest
from datetime import date

# Project root — needed for PlanningInfo, mock_data, etc.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# agents/ subdir — imported directly so FlightAgent, AccomAgent, planning_agent
# can be imported by name in tests without going through the package.
_agents_dir = os.path.join(_root, "agents")
for _p in (_root, _agents_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PlanningInfo import PlanningInfo


@pytest.fixture
def info():
    return PlanningInfo(
        number_travelers=2,
        dates=(date(2026, 6, 1), date(2026, 6, 8)),
        city="Paris",
        vibe="culture, food",
        budget=(2000, 4000),
        accom_type="hotel",
        food_requirements=["vegetarian"],
        other="",
    )


@pytest.fixture
def eco_info():
    """PlanningInfo with sustainability keywords in vibe."""
    return PlanningInfo(
        number_travelers=2,
        dates=(date(2026, 6, 1), date(2026, 6, 8)),
        city="Paris",
        vibe="eco sustainable travel",
        budget=(2000, 4000),
        accom_type="hotel",
        food_requirements=[],
        other="",
    )


@pytest.fixture
def multi_city_info():
    return PlanningInfo(
        number_travelers=3,
        dates=(date(2026, 7, 10), date(2026, 7, 20)),
        city=["London", "Amsterdam"],
        vibe="nightlife, art",
        budget=(3000, 6000),
        accom_type="hostel",
        food_requirements=[],
        other="",
    )
