# Copilot Instructions — Agentic Trip Planner

## Architecture Overview

This is a **hackathon project**: a multi-agent trip planner using **CrewAI** for AI orchestration, **FastAPI** for the backend API, **Streamlit** for the frontend, and **SQLite/SQLAlchemy** for persistence. The system supports OpenAI, Gemini, and Anthropic LLMs via `LLM_PROVIDER` env var.

**Data flow:** Streamlit UI → FastAPI REST API (`:8000`) → `planning_agent.TripPlanner` → CrewAI Crew (5 agents in sequential process) → Amadeus APIs (with mock fallback) → results persisted to SQLite → returned to UI.

### Key Components

| Layer | Entry Point | Role |
|---|---|---|
| API | `main.py` | FastAPI app, auth (JWT), CRUD, SSE streaming (`/trips/{id}/plan/stream`) |
| Orchestrator | `agents/planning_agent.py` | Builds 5 CrewAI agents, tasks, parses results. **This is the most complex file (~1100 lines)** |
| Sub-agents | `agents/FlightAgent.py`, `agents/AccomAgent.py` | Amadeus API wrappers exposed as `@crewai_tool`s; fall back to mock data when no credentials |
| Data models | `database.py` | SQLAlchemy models: `User`, `Trip`, `ItineraryItem`, `Flight`, `Accommodation`, `City` |
| Shared DTO | `PlanningInfo.py` | `@dataclass_json` used by sub-agents for structured trip params |
| Mock layer | `mock_data.py` | Generates fake flights/hotels/city info when Amadeus keys are absent |
| Frontend | `streamlit_app/app.py` | Multi-page Streamlit app with maps (folium), iCal export, SSE consumption |

## Running & Testing

```bash
# Full stack (both backend + frontend):
bash start.sh

# Backend only:
python main.py                    # serves on :8000

# Frontend only:
cd streamlit_app && streamlit run app.py   # serves on :8501

# Tests (from project root):
pytest tests/
```

Tests import agents **directly by filename** (not via the `agents` package). See `tests/conftest.py` — it adds both project root and `agents/` to `sys.path`. When writing tests, import like `import planning_agent as pa` and `import FlightAgent as fa`, not `from agents import ...`.

## Critical Patterns

### Amadeus → Mock Fallback
Every external data path (flights, hotels) follows the same pattern: try Amadeus API → if error or no credentials → fall back to `mock_data.py` generators. The check is `_has_credentials = bool(os.getenv("AMADEUS_CLIENT_ID"))`. When adding new external data sources, follow this same fallback pattern.

### IATA Code Resolution
City names are converted to IATA codes via `_CITY_TO_AIRPORT` / `_CITY_TO_IATA_CITY` dicts in `planning_agent.py`, falling back to `mock_data.get_airport_for_city()`. CrewAI tools accept **city names** (e.g. "Paris") and handle IATA conversion internally — agents never need to know IATA codes.

### Amadeus Response Normalization
Raw Amadeus API responses (FlightOffer, HotelOffers) are converted to the DB-compatible schema via `_normalize_amadeus_flights()` and `_normalize_amadeus_hotels()` in `planning_agent.py`. Mock data is already in DB-compatible format. Detection uses `_is_mock_flight()` / `_is_mock_accom()`.

### Country vs City Detection
`_is_likely_country(destination)` checks against a hardcoded `COUNTRIES` set. Country-level trips trigger multi-city selection (2-4 cities); city-level trips skip the CitySelector agent. When a country isn't recognized, the trip is treated as a single city.

### LLM Output Parsing
Agent outputs are raw LLM text. `_safe_json_parse()` strips markdown fences before `json.loads()`. Always expect LLM outputs to be wrapped in ```json fences. Fallback data (`_build_fallback_itinerary`, `_fallback_day_plan`) is used when parsing fails.

### SSE Streaming
`plan_trip_stream()` runs the CrewAI crew in a background thread and yields SSE events. Progress callbacks fire when each agent completes. The frontend consumes these via `requests` streaming in `streamlit_app/app.py`.

## Conventions

- **IDs**: 8-char truncated UUIDs (`str(uuid.uuid4())[:8]`) — see `database.py:generate_id()`
- **Dates**: Strings in `YYYY-MM-DD` format throughout (DB, API, agents)
- **Prices**: Always include both `cost_usd` (numeric) and `cost_local` (formatted string with currency symbol) in itinerary items
- **Google Maps URLs**: Every itinerary location must have a `google_maps_url` field built via `_gmaps_url(place, city)`
- **Booking URLs**: Flights/hotels include `booking_url` — Google Flights/Hotels search links as fallback
- **Status fields**: Itinerary items use `planned/completed/skipped/delayed`; flights and accommodations use `suggested/selected/booked`
- **CrewAI tools**: Decorated with `@crewai_tool("Tool Name")` — the string name is what agents see. Tool functions use `.func` attribute for direct testing

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | One required | LLM provider credentials |
| `LLM_PROVIDER` | No (default: `openai`) | `openai`, `gemini`, or `anthropic` |
| `LLM_MODEL` | No | Override default model per provider |
| `AMADEUS_CLIENT_ID` + `AMADEUS_CLIENT_SECRET` | No | Live flight/hotel data (falls back to mock) |
| `TAVILY_API_KEY` / `SERPER_API_KEY` | No | Web search for DestinationResearcher agent |
| `SECRET_KEY` | No | JWT signing key (defaults to `hackathon-secret-key`) |
