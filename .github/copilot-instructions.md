# Copilot Instructions — Agentic Trip Planner

## Architecture Overview

Hackathon project: multi-agent trip planner. **CrewAI** (7 agents) → **FastAPI** backend (`:8000`) → **React/Vite** frontend (`:5173`) + legacy **Streamlit** frontend (`:8501`). **SQLite/SQLAlchemy** for persistence. Supports OpenAI, Gemini, Anthropic LLMs via `LLM_PROVIDER`.

**Data flow:** React UI → FastAPI REST API → `agents/planning_agent.TripPlanner` → CrewAI Crew (7 sequential agents) → Amadeus APIs (mock fallback) → SQLite → response to UI.

### Key Components

| Layer | Entry Point | Role |
|---|---|---|
| API | `main.py` | FastAPI app, JWT auth, CRUD, SSE streaming, iCal export |
| Orchestrator | `agents/planning_agent.py` | 7 CrewAI agents, task creation, LLM output parsing (~1100 lines) |
| Sub-agents | `agents/FlightAgent.py`, `agents/AccomAgent.py` | Amadeus API wrappers as `@crewai_tool`s; mock fallback |
| Data models | `database.py` | SQLAlchemy: `User`, `Trip`, `ItineraryItem`, `Flight`, `Accommodation`, `City` |
| Shared DTO | `PlanningInfo.py` | `@dataclass_json` for structured trip params |
| Mock layer | `mock_data.py` | Fake flights/hotels/city data when Amadeus keys absent |
| React frontend | `frontend/` | Vite + React 19, react-router-dom, framer-motion, custom CSS |
| Streamlit frontend | `streamlit_app/app.py` | Legacy: maps (folium), iCal, SSE consumption |
| Pinterest server | `frontend/server.py` | Separate FastAPI app for Pinterest image scraping (mood boards) |

### The 7 CrewAI Agents

DestinationResearcher → CitySelector → LocalExpert → FlightFinder → AccommodationFinder → LocalTravelAdvisor → ItineraryPlanner. Context flows forward; ItineraryPlanner receives all prior outputs.

## Running & Testing

```bash
bash start.sh                              # Backend (:8000) + Streamlit (:8501)
python main.py                             # Backend only
cd frontend && npx vite --port 5173        # React frontend only (proxy /api → :8000)
cd streamlit_app && streamlit run app.py   # Streamlit only
pytest tests/                              # Tests (from project root)
```

**Note:** `start.sh` does NOT start the React frontend. Run it separately. The React frontend proxies `/api` to `:8000` via Vite config, but `frontend/src/api.js` hardcodes `BASE_URL = http://localhost:8000` (bypasses proxy).

### Test conventions
Tests import agents **by bare filename**, not via the `agents` package. `tests/conftest.py` adds both project root and `agents/` to `sys.path`:
```python
import planning_agent as pa       # ✓ correct
import FlightAgent as fa          # ✓ correct
from agents import planning_agent # ✗ wrong
```
Mock CrewAI task outputs by setting `task.output.raw` to JSON strings. Test pure helper functions (`_safe_json_parse`, `_normalize_amadeus_flights`, `_is_likely_country`) directly.

## Critical Patterns

### Amadeus → Mock Fallback
Every external data path: try Amadeus API → on error or missing credentials → `mock_data.py`. The credential check is `_has_credentials = bool(os.getenv("AMADEUS_CLIENT_ID"))`. New external data sources must follow this same pattern.

### Auth — Hackathon Shortcut
Backend generates JWT tokens at login, but **does not validate them on protected routes**. All endpoints trust a `user_id` query parameter directly. The React frontend stores the token in `localStorage["token"]` and sends it via `Authorization: Bearer` header, but the backend ignores it. User identification is purely via `?user_id=` param.

### IATA Code Resolution
City names → IATA codes via `_CITY_TO_AIRPORT` / `_CITY_TO_IATA_CITY` dicts in `planning_agent.py`, fallback to `mock_data.get_airport_for_city()`. CrewAI tools accept city names — agents never deal with IATA codes.

### LLM Output Parsing
Agent outputs are raw LLM text. `_safe_json_parse()` strips markdown ` ```json ` fences before `json.loads()`. Always expect fenced JSON from LLMs. Fallback builders (`_build_fallback_itinerary`, `_fallback_day_plan`) handle parse failures gracefully.

### Country vs City Detection
`_is_likely_country(destination)` checks a hardcoded `COUNTRIES` set. Country → multi-city (2-4 cities via CitySelector). Unrecognized → treated as single city.

### SSE Streaming
`plan_trip_stream()` runs CrewAI crew in a background thread, yields SSE events (`progress`, `complete`, `error`). React frontend reads with `fetch()` + `ReadableStream` (not `EventSource`), parsing `data:` lines manually in `api.js:streamTripPlan()`.

### Itinerary Regeneration
`POST /trips/{trip_id}/regenerate-itinerary` re-runs only the ItineraryPlanner agent using cached `trip.plan_data` JSON + user-selected flights/accommodations. Avoids full 7-agent re-run.

### Flight/Accommodation Selection
`PUT /flights/{id}/select` sets status to `selected` and resets all sibling flights (same trip + type) to `suggested`. Same pattern for accommodations. Status lifecycle: `suggested` → `selected` → `booked`.

## Conventions

- **IDs**: 8-char truncated UUIDs — `str(uuid.uuid4())[:8]` via `database.py:generate_id()`
- **Dates**: `YYYY-MM-DD` strings everywhere (DB, API, agents)
- **Prices**: Include `cost_usd` (numeric) + `cost_local` (formatted with currency symbol)
- **Google Maps URLs**: Every location → `google_maps_url` via `_gmaps_url(place, city)`
- **Booking URLs**: Google Flights/Hotels search URLs as fallback
- **Status fields**: Itinerary items: `planned/completed/skipped/delayed`; flights/accommodations: `suggested/selected/booked`
- **CrewAI tools**: `@crewai_tool("Tool Name")` — test via `.func` attribute
- **LLM config**: `_get_llm_model_string()` returns `"gpt-4o-mini"` (OpenAI) or `"gemini/gemini-2.0-flash"` / `"anthropic/claude-sonnet-4-20250514"` (prefixed for CrewAI)
- **Dual imports in agents**: `try: from .Module import ... except ImportError: from Module import ...` — supports both package and direct invocation
- **React frontend CSS**: Per-component CSS files, BEM-style class names (`plan__header`, `navbar__link`)
- **No DB migrations**: Uses `create_all()` directly; `seed_cities()` inserts 15 popular cities on startup
- **Trip plan_data**: Complete AI output stored as JSON column on Trip; enables regeneration without re-running full crew

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | One required | LLM credentials |
| `LLM_PROVIDER` | No (default: `openai`) | `openai`, `gemini`, or `anthropic` |
| `LLM_MODEL` | No | Override model (defaults: `gpt-4o-mini`, `gemini-2.0-flash`, `claude-sonnet-4-20250514`) |
| `AMADEUS_CLIENT_ID` + `AMADEUS_CLIENT_SECRET` | No | Live flight/hotel data (mock fallback) |
| `TAVILY_API_KEY` / `SERPER_API_KEY` | No | Web search for DestinationResearcher |
| `GOOGLE_MAPS_API_KEY` | No | Distance Matrix API for travel routes between itinerary items (mock fallback) |
| `SECRET_KEY` | No | JWT signing (default: `hackathon-secret-key`) |
