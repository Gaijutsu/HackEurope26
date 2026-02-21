from dataclasses import dataclass
from datetime import date

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class PlanningInfo:
    number_travelers: int
    dates: tuple[date, date]
    city: str | list[str]
    vibe: str
    budget: tuple[int, int]
    accom_type: str
    food_requirements: list[str]
    other: str

    def get_cities(self) -> list[str]:
        """Always returns city as a list, regardless of input type."""
        return self.city if isinstance(self.city, list) else [self.city]

    def trip_nights(self) -> int:
        """Number of nights between the start and end dates."""
        start, end = self.dates
        return (end - start).days

    def budget_per_person(self) -> tuple[int, int]:
        """Budget range divided by number of travelers."""
        lo, hi = self.budget
        return (lo // self.number_travelers, hi // self.number_travelers)

    def budget_per_night(self) -> tuple[int, int]:
        """Budget range divided by number of nights."""
        nights = self.trip_nights()
        lo, hi = self.budget
        return (lo // nights, hi // nights) if nights else self.budget
