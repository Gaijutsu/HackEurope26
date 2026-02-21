# AI Agent System for Trip Planning - Quick Reference

## 14 Specialized Agents

### User & Setup Agents
| Agent | Purpose |
|-------|---------|
| **UserProfileManager** | Manages accounts, preferences, dietary restrictions, budget profiles |
| **TripInitializer** | Validates trip params, determines city vs country scope |

### Research Agents
| Agent | Purpose |
|-------|---------|
| **DestinationResearcher** | Gathers destination info, identifies tourist traps, finds hidden gems |
| **CitySelector** | Selects optimal cities for country-level trips, optimizes routes |
| **AttractionCurator** | Curates attractions by interests, filters tourist traps |
| **RestaurantFinder** | Finds dietary-friendly restaurants, verifies restrictions |

### Booking Agents
| Agent | Purpose |
|-------|---------|
| **FlightFinder** | Searches flights, finds deals, provides booking links |
| **AccommodationFinder** | Searches hotels/Airbnb, filters by location/price |

### Planning Agents
| Agent | Purpose |
|-------|---------|
| **ItineraryPlanner** | Master orchestrator - creates day-by-day schedules |
| **BudgetOptimizer** | Finds savings, suggests alternatives, identifies discounts |
| **QualityValidator** | Validates feasibility, checks goal alignment |

### Management Agents
| Agent | Purpose |
|-------|---------|
| **FlightManager** | Tracks reservations, manages changes |
| **AccommodationManager** | Manages hotel bookings, modifications |
| **ItineraryManager** | Handles delays, rescheduling, real-time updates |

---

## Planning Workflow (11 Steps)

```
1. User creates trip → TripInitializer validates
2. Load user profile → UserProfileManager retrieves preferences
3. PARALLEL RESEARCH:
   • DestinationResearcher gathers info
   • FlightFinder searches flights
   • AccommodationFinder searches hotels
4. IF country: CitySelector chooses cities & route
5. AttractionCurator filters & prioritizes attractions
6. RestaurantFinder finds dietary-friendly dining
7. ItineraryPlanner builds day-by-day schedule
8. BudgetOptimizer reduces costs
9. QualityValidator checks feasibility
10. Present to user with booking links
11. Enable management (Flight/Accommodation/Itinerary Managers)
```

---

## Key Optimization Strategies

### Avoiding Tourist Traps
- Review sentiment analysis ("overpriced", "disappointing")
- Local vs tourist ratio detection
- Price-to-value analysis
- Prioritize authentic local experiences

### Finding Cheap Options
- Search ±3 days for flights
- Check alternative airports
- Compare across booking platforms
- Suggest free activities & discount passes
- Public transport over taxis

### Maximizing Attractions
- Geographic clustering (group nearby attractions)
- Visit popular spots early/late
- Timed entry bookings
- Must-see vs optional prioritization

### Dietary Restrictions
- Multi-source verification of dietary claims
- Certification checks (halal, kosher)
- Allergen protocol verification
- Daily dietary coverage guarantee

---

## Multi-City Planning (Country Trips)

```
1. TripInitializer detects country destination
2. CitySelector:
   - Scores cities by interest alignment
   - Calculates optimal route (minimize backtracking)
   - Allocates nights based on attraction density
   - Finds intercity transport options
3. Each city gets parallel planning
4. ItineraryPlanner integrates all cities
```

---

## Agent Dependencies

```
UserProfileManager (foundation)
    ↓
TripInitializer
    ↓
    ├→ DestinationResearcher ─┬→ CitySelector (if country)
    │                         ├→ AttractionCurator
    │                         └→ RestaurantFinder
    ├→ FlightFinder
    └→ AccommodationFinder
              ↓
    ItineraryPlanner (master)
              ↓
    ├→ BudgetOptimizer
    └→ QualityValidator
              ↓
    Final Itinerary
              ↓
    ├→ FlightManager
    ├→ AccommodationManager
    └→ ItineraryManager
```

---

## Required API Integrations

| Category | APIs |
|----------|------|
| Flights | Skyscanner, Kayak, Google Flights |
| Hotels | Booking.com, Airbnb, Hostelworld |
| Attractions | Google Places, TripAdvisor, GetYourGuide |
| Restaurants | Yelp, Foursquare |
| Transport | Rome2Rio, Google Maps |

---

## Communication Protocol

```json
{
  "message_id": "uuid",
  "from_agent": "agent_name",
  "to_agent": "agent_name",
  "message_type": "request|response|notification",
  "payload": {},
  "timestamp": "ISO8601",
  "priority": "high|medium|low"
}
```

---

## Output Format

Final itinerary includes:
- Day-by-day schedule with time allocations
- Booking links (flights, hotels, attractions)
- Interactive maps
- Restaurant recommendations with dietary info
- Cost estimates
- Alternative options
- Quality confidence score
