# Agentic Trip Planner - Hackathon Version 🚀

A simplified, fully-functional prototype of the Agentic Trip Planning Software built for a 24-hour hackathon.

## Features ✨

- **AI-Powered Planning**: Single agent handles destination research, city selection, flight/hotel search, and itinerary creation
- **Multi-City Support**: Automatically plans multi-city trips when destination is a country
- **Preference-Aware**: Respects dietary restrictions and travel style
- **Booking Integration**: Mock flight and hotel data with booking links
- **Flexible Management**: Delay itinerary items to another day
- **Simple UI**: Streamlit-based interface for rapid development

## Tech Stack 🛠️

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | SQLite |
| AI/LLM | OpenAI GPT-4o-mini |
| External APIs | Mock data (flights, hotels) |

## Quick Start 🚀

### 1. Install Dependencies

```bash
cd trip_planner_hackathon
pip install -r requirements.txt
```

### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

### 3. Start the Backend

```bash
python main.py
```

The API will start on `http://localhost:8000`

### 4. Start the Frontend (New Terminal)

```bash
cd streamlit_app
streamlit run app.py
```

The UI will open in your browser at `http://localhost:8501`

## Usage 📖

1. **Register/Login**: Create an account or login
2. **Create Trip**: Click "New Trip" and fill in the wizard:
   - Destination (city or country)
   - Travel dates
   - Number of travelers
   - Interests
   - Dietary restrictions
   - Budget level
3. **AI Planning**: The AI agent will:
   - Research your destination
   - Select cities (if country)
   - Find flights and hotels (mock data)
   - Create a day-by-day itinerary
4. **View Itinerary**: Browse your personalized schedule
5. **Manage Bookings**: View flights and accommodations with booking links
6. **Delay Items**: Move itinerary items to different days

## API Endpoints 📡

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Login |
| `/trips` | GET | List user's trips |
| `/trips` | POST | Create new trip |
| `/trips/{id}/plan` | POST | Start AI planning |
| `/trips/{id}/itinerary` | GET | Get day-by-day itinerary |
| `/trips/{id}/itinerary/items/{id}/delay` | PUT | Delay item to another day |
| `/trips/{id}/flights` | GET | Get flight options |
| `/trips/{id}/accommodations` | GET | Get hotel options |

## Architecture 🏗️

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                        │
│  - Trip Creation Wizard                                      │
│  - Itinerary Viewer                                          │
│  - Flight/Hotel Management                                   │
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

## Simplified Agent Architecture 🤖

Instead of 14 separate agents, we use a single **PlanningAgent** that:

1. Determines if destination is city or country
2. Selects cities (if country) using AI
3. Generates mock flights and hotels
4. Creates day-by-day itinerary using OpenAI

This reduces complexity while maintaining the core functionality.

## Database Schema 🗄️

Simplified to 8 core tables:
- `users` - User accounts
- `trips` - Trip details and planning status
- `itinerary_items` - Day-by-day activities
- `flights` - Flight options
- `accommodations` - Hotel options
- `cities` - City data for search

## Demo Tips 🎯

1. **Quick Demo Flow**:
   - Register with any email/password
   - Create a trip to "Japan" (country-level planning)
   - Watch AI select Tokyo, Kyoto, Osaka
   - View generated itinerary with flights and hotels

2. **Key Features to Show**:
   - AI city selection for countries
   - Day-by-day itinerary with times
   - Delay functionality
   - Booking links

3. **Test Destinations**:
   - "Tokyo" (city)
   - "Japan" (country - multi-city)
   - "Paris" (city)
   - "France" (country - multi-city)

## Limitations ⚠️

This is a hackathon prototype with intentional simplifications:

- **Mock External APIs**: Flights and hotels are simulated
- **No Real Booking**: Links go to airline/hotel websites
- **Simplified Auth**: Session-based (no JWT refresh)
- **No Caching**: Direct database queries
- **No Message Queue**: Synchronous planning
- **SQLite**: Single-file database (not production-ready)

## Future Enhancements 🔮

To make this production-ready:

1. Replace mock data with real APIs (Amadeus, Booking.com)
2. Add Redis caching
3. Implement message queue for async planning
4. Migrate to PostgreSQL
5. Add comprehensive error handling
6. Implement proper JWT auth with refresh tokens
7. Add WebSocket for real-time planning updates
8. Expand to 14 specialized agents with LangGraph

## Files Structure 📁

```
trip_planner_hackathon/
├── main.py                 # FastAPI backend
├── database.py             # SQLite models
├── agents.py               # Planning agent
├── mock_data.py            # Mock flights/hotels
├── requirements.txt
├── README.md
└── streamlit_app/
    └── app.py              # Streamlit frontend
```

## Hackathon Judging Criteria 🏆

This prototype demonstrates:

- ✅ **Working AI Agent**: Single agent creates complete trip plans
- ✅ **Multi-City Planning**: Automatically plans multi-city trips
- ✅ **Preference Awareness**: Respects dietary restrictions
- ✅ **Full User Flow**: From signup to itinerary management
- ✅ **Delay Functionality**: Move items between days
- ✅ **Booking Integration**: Links to book flights/hotels
- ✅ **Clean UI**: Intuitive Streamlit interface
- ✅ **Working Demo**: Fully functional in 24 hours

## Credits 👥

Built with ❤️ for a 24-hour hackathon using:
- FastAPI for the backend
- Streamlit for the frontend
- OpenAI for AI planning
- SQLite for data storage

## License 📄

MIT License - Hackathon Project
