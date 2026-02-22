# Agentic Trip Planner - CrewAI Multi-Agent Edition

A multi-agent trip planning system built with **CrewAI** for a hackathon. Five specialised AI agents collaborate to research destinations, find flights and accommodations, and build day-by-day itineraries.

## Features

- **CrewAI Multi-Agent Orchestration** - 5 agents that share context and collaborate
- **Multi-Provider LLM Support** - OpenAI, Google Gemini, and Anthropic Claude
- **Real-Time Progress Streaming** - SSE endpoint shows each agent's progress live
- **Tool-Equipped Agents** - web search (Tavily/Serper), flight search, accommodation search, city info
- **Multi-City Planning** - automatically plans multi-city routes for country-level destinations
- **Preference-Aware** - respects dietary restrictions, interests, and budget level
- **Mock Data APIs** - flights and accommodations work without external API keys

## Agent Architecture

| Agent                     | Role                                   | Tools                                   |
| ------------------------- | -------------------------------------- | --------------------------------------- |
| **DestinationResearcher** | Web research on destinations           | TavilySearch, ScrapeWebsite, CityInfo   |
| **CitySelector**          | Picks optimal cities for country trips | TavilySearch, CityInfo                  |
| **FlightFinder**          | Searches for flight options            | SearchFlights (Skyscanner-like mock)    |
| **AccommodationFinder**   | Finds places to stay                   | SearchAccommodations (Airbnb-like mock) |
| **ItineraryPlanner**      | Builds the day-by-day plan             | CityInfo, TavilySearch                  |

Agents pass context through CrewAI's task dependency system - the ItineraryPlanner receives output from all four previous agents to create a cohesive plan.

## Tech Stack

| Component       | Technology                              |
| --------------- | --------------------------------------- |
| Agent Framework | CrewAI                                  |
| LLM Providers   | OpenAI, Google Gemini, Anthropic Claude |
| Backend         | FastAPI + SSE streaming                 |
| Frontend        | Streamlit                               |
| Database        | SQLite + SQLAlchemy                     |
| Web Search      | Tavily or Serper (optional)             |

## Quick Start

### 1. Clone and create a virtual environment

```bash
cd HackEurope26
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your LLM provider

Copy the example env file and set your API key:

```bash
cp .env.example .env
```

Then edit `.env` and set **one** of these depending on your provider:

| Provider             | Env Vars to Set                                    |
| -------------------- | -------------------------------------------------- |
| **OpenAI** (default) | `OPENAI_API_KEY=sk-...`                            |
| **Google Gemini**    | `LLM_PROVIDER=gemini` + `GEMINI_API_KEY=...`       |
| **Anthropic Claude** | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=...` |

Default models per provider:

- OpenAI: `gpt-4o-mini`
- Gemini: `gemini-2.0-flash`
- Claude: `claude-sonnet-4-20250514`

Override with `LLM_MODEL=your-model-name` if needed.

### 3. Start everything

**Option A - One command:**

```bash
bash start.sh
```

**Option B - Manual (two terminals):**

Terminal 1 (backend):

```bash
source .venv/bin/activate
python main.py
# API at http://localhost:8000
```

Terminal 2 (frontend):

```bash
source .venv/bin/activate
cd streamlit_app
streamlit run app.py
# UI at http://localhost:8501
```

### 4. Use the app

1. Open http://localhost:8501
2. Register with any email/password
3. Create a trip (try "Japan" for multi-city or "Tokyo" for single-city)
4. Click "Start Planning" and watch the agents work in real-time

## Running with Mock Data Only

**Yes, the system works fully with mock data and requires NO external API keys beyond an LLM key.** Here's what happens:

| Component          | With API Key               | Without API Key                          |
| ------------------ | -------------------------- | ---------------------------------------- |
| **LLM** (required) | Full agent reasoning       | Won't start without at least one LLM key |
| **Flights**        | Mock data always           | Mock data always                         |
| **Accommodations** | Mock data always           | Mock data always                         |
| **City Info**      | Built-in database          | Built-in database                        |
| **Web Search**     | Live Tavily/Serper results | Agents use LLM knowledge only            |

**Minimum to run:** Just one LLM API key (`OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY`).

The flight search, accommodation search, and city info tools all use local mock data generators - no Skyscanner/Airbnb/Google Maps keys needed.

## Optional: Web Search

For better destination research, set a web search key:

```bash
# Tavily (preferred, free tier available)
TAVILY_API_KEY=tvly-...

# OR Serper (alternative)
SERPER_API_KEY=...
```

Without these, the DestinationResearcher agent still works - it just relies on the LLM's training data instead of live search results.

## API Endpoints

| Endpoint                                 | Method | Description                       |
| ---------------------------------------- | ------ | --------------------------------- |
| `/auth/register`                         | POST   | Create account                    |
| `/auth/login`                            | POST   | Login                             |
| `/trips`                                 | GET    | List trips                        |
| `/trips`                                 | POST   | Create trip                       |
| `/trips/{id}/plan`                       | POST   | Run planning (sync)               |
| `/trips/{id}/plan/stream`                | GET    | Run planning (SSE stream)         |
| `/trips/{id}/plan/status`                | GET    | Check planning status             |
| `/trips/{id}/itinerary`                  | GET    | Get day-by-day itinerary          |
| `/trips/{id}/flights`                    | GET    | Get flight options                |
| `/trips/{id}/accommodations`             | GET    | Get accommodation options         |
| `/trips/{id}/itinerary/items/{id}/delay` | PUT    | Delay item to another day         |
| `/search/cities`                         | GET    | Search city database              |
| `/health`                                | GET    | Health check (shows LLM provider) |

## Project Structure

```
HackEurope26/
├── agents.py              # CrewAI agents, tools, tasks, and crew orchestration
├── main.py                # FastAPI backend with SSE streaming
├── database.py            # SQLAlchemy models (User, Trip, Flight, etc.)
├── mock_data.py           # Mock flight/accommodation/city data generators
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── start.sh               # One-command launcher
├── streamlit_app/
│   └── app.py             # Streamlit frontend
└── docs/                  # Design documentation
```

## Demo Tips

- **"Japan"** triggers multi-city planning (Tokyo, Kyoto, Osaka)
- **"Paris"** triggers single-city planning
- Watch the SSE stream to see agents hand off context to each other
- The `/health` endpoint shows which LLM provider is active

## Limitations

- Flight and accommodation data is mock (simulated APIs)
- No real booking integration
- SQLite database (not production-ready)
- Session-based auth (simplified for hackathon)

## Stripe Integration (Trip Credits)

Users have **trip credits** — each credit allows planning one AI-powered trip. Credits are displayed in the navbar/banner on every page and can be purchased via Stripe Checkout.

### Credit Packages

| Package | Price | Per Credit |
|---------|-------|------------|
| 1 credit | $1.99 | $1.99 |
| 5 credits | $7.99 | $1.60 |
| 10 credits | $11.99 | $1.20 |

New users start with **3 free credits**.

### Setup (~15 min)

1. **Create a Stripe account** at [dashboard.stripe.com](https://dashboard.stripe.com) — you'll be in test mode by default.

2. **Copy your test secret key** from **Developers → API keys** (starts with `sk_test_...`) and add to `.env`:

   ```bash
   STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxx
   FRONTEND_URL=http://localhost:5173
   ```

3. **Set up local webhook forwarding** with the [Stripe CLI](https://docs.stripe.com/stripe-cli):

   ```bash
   # Install (Linux)
   curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
   echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee /etc/apt/sources.list.d/stripe.list
   sudo apt update && sudo apt install stripe

   # macOS: brew install stripe/stripe-cli/stripe

   # Login & forward
   stripe login
   stripe listen --forward-to localhost:8000/credits/webhook
   ```

   Copy the webhook signing secret (`whsec_...`) and add to `.env`:

   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxx
   ```

4. **Test a purchase** — use Stripe's test card `4242 4242 4242 4242` with any future expiry and any CVC.

### Without Stripe Keys

If `STRIPE_SECRET_KEY` is not set, the checkout endpoint **grants credits directly** as a hackathon fallback — no real payment is needed to demo the full flow.

### Secret Cheat Codes

On the landing page destination input:
- Type **`AddCredits`** and submit → adds 5 credits (must be logged in)
- Type **`RemoveCredits`** and submit → removes 5 credits (capped at 0)

### Credit-Related API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/credits` | GET | Get current credit balance |
| `/credits/adjust` | POST | Add/remove credits (secret codes) |
| `/credits/checkout` | POST | Create Stripe Checkout session |
| `/credits/webhook` | POST | Stripe webhook handler |
| `/credits/success` | GET | Verify completed checkout |

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `STRIPE_SECRET_KEY` | No | Stripe secret key (fallback: free credits) |
| `STRIPE_WEBHOOK_SECRET` | No | Webhook signature verification |
| `FRONTEND_URL` | No | Redirect after checkout (default: `http://localhost:5173`) |
