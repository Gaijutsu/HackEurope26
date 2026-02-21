# Agentic Trip Planner - Hackathon Simplified Design

## Simplified Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                        │
│  - Trip Creation Wizard                                      │
│  - Itinerary Viewer                                          │
│  - Flight/Hotel Management                                   │
│  - Drag-drop interface (simplified)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Agents    │  │   Models    │  │   External APIs     │  │
│  │  (Python)   │  │  (SQLite)   │  │  (OpenAI + Mocks)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack (Simplified)

| Component | Hackathon Choice | Production Equivalent |
|-----------|------------------|----------------------|
| Frontend | Streamlit | Next.js + React |
| Backend | FastAPI | NestJS |
| Database | SQLite | PostgreSQL |
| Cache | In-memory dict | Redis |
| AI/LLM | OpenAI direct | LangGraph + OpenAI |
| Queue | Direct calls | BullMQ |
| Auth | Session-based | Clerk/Auth0 |

## Agent Implementation (Simplified)

Instead of 14 separate agents with complex orchestration, we'll use:

1. **PlanningAgent** - Single agent that handles the entire planning workflow
   - Uses structured OpenAI prompts
   - Sequential execution (no complex orchestration)
   - Direct function calls

2. **Mock External APIs**
   - Flight data: Mock with realistic data
   - Hotel data: Mock with realistic data
   - Attractions: Use OpenAI knowledge + caching

## Database Schema (Simplified - 8 tables)

```sql
-- Core tables only
users (id, email, name, preferences_json)
trips (id, user_id, destination, start_date, end_date, status, plan_json)
cities (id, name, country, iata_code)
itinerary_items (id, trip_id, day_number, title, description, start_time, duration, item_type, status, delayed_to_day)
flights (id, trip_id, flight_type, airline, flight_number, from_airport, to_airport, departure, arrival, price, booking_url, status)
accommodations (id, trip_id, name, address, check_in, check_out, price, booking_url, status)
```

## API Endpoints (Simplified - 15 endpoints)

```
POST   /auth/register
POST   /auth/login

GET    /trips
POST   /trips
GET    /trips/{id}
DELETE /trips/{id}

POST   /trips/{id}/plan        # Start AI planning
GET    /trips/{id}/plan/status  # Get planning status

GET    /trips/{id}/itinerary
PUT    /trips/{id}/itinerary/items/{item_id}/delay

GET    /trips/{id}/flights
POST   /trips/{id}/flights/{flight_id}/book

GET    /trips/{id}/accommodations
POST   /trips/{id}/accommodations/{acc_id}/book

GET    /search/cities?q={query}
```

## UI Flow (Streamlit Pages)

```
app.py                    # Main entry, navigation
pages/
├── 01_login.py          # Authentication
├── 02_dashboard.py      # Trip list
├── 03_create_trip.py    # Trip creation wizard
├── 04_planning.py       # AI planning progress
├── 05_itinerary.py      # Day-by-day itinerary
├── 06_flights.py        # Flight management
└── 07_accommodations.py # Hotel management
```

## Key Simplifications

1. **Single Planning Agent**: One agent does destination research, city selection, flight/hotel search, and itinerary creation
2. **Mock External Data**: Flights and hotels are mocked with realistic data (no actual API integrations)
3. **No Message Queue**: Planning happens synchronously (with progress updates via polling)
4. **SQLite**: Single file database, no setup
5. **Streamlit**: Rapid UI development, no React/JavaScript
6. **In-Memory Cache**: Simple dict for caching
7. **Session Auth**: Simple session-based auth (no JWT)

## Planning Agent Prompt Structure

```python
SYSTEM_PROMPT = """You are an expert travel planner. Create a detailed itinerary based on:
- Destination: {destination}
- Dates: {start_date} to {end_date}
- Travelers: {num_travelers}
- Interests: {interests}
- Dietary restrictions: {dietary}
- Budget: {budget}

Output JSON with:
- cities: list of cities to visit (if country)
- flights: list of flight options
- accommodations: list of hotels
- itinerary: day-by-day schedule with attractions, meals, activities
"""
```

## Estimated Implementation Time

| Component | Time |
|-----------|------|
| Database models + setup | 1 hour |
| FastAPI backend + agents | 4 hours |
| Streamlit UI | 4 hours |
| Integration + testing | 3 hours |
| Polish + demo prep | 2 hours |
| **Total** | **~14 hours** |

## Files to Create

```
/hackathon_trip_planner/
├── main.py                 # FastAPI app
├── database.py             # SQLite models
├── agents.py               # Planning agent
├── mock_data.py            # Mock flights/hotels
├── requirements.txt
└── streamlit_app/
    ├── app.py              # Main entry
    ├── auth.py             # Auth helpers
    └── pages/
        ├── 01_login.py
        ├── 02_dashboard.py
        ├── 03_create_trip.py
        ├── 04_planning.py
        ├── 05_itinerary.py
        ├── 06_flights.py
        └── 07_accommodations.py
```
