# Challenge Points & Pitch Focus

> **Team project:** Agentic Trip Planner — a multi-agent AI system that plans, adapts, and books entire trips end-to-end.

---

## 1 · Best Stripe Integration — €3,000

### What the judges want

> "Projects that truly reimagine financial tools that simplify day-to-day life."
> They want **meaningful** integration — not just a payment button.

### Our points

| # | Feature | What it does |
|---|---------|-------------|
| 1 | **Trip credit economy** | 3 tier credit packages ($1.99 / $7.99 / $11.99) via Stripe Checkout. Users buy credits to unlock AI planning runs. |
| 2 | **Flight booking via Stripe** | "Book" on any flight → Stripe Checkout session created with real flight details (airline, route, date) as product data. Stripe handles payment, we handle fulfilment through Amadeus. |
| 3 | **Hotel booking via Stripe** | Same Checkout flow for accommodations — hotel name, city, dates, total price all passed to Stripe product data. |
| 4 | **Unified webhook handler** | Single `POST /credits/webhook` endpoint routes `checkout.session.completed` by `metadata.item_type` → flight booking, hotel booking, or credit grant. |
| 5 | **Booking verification on redirect** | Frontend reads `?booked=<id>&session_id=<sid>` on return, calls `/booking/verify` which retrieves the Stripe session, checks `payment_status == "paid"`, and marks the item booked with idempotency. |
| 6 | **Status lifecycle** | Items progress through `suggested → selected → booked`. Stripe payment is the `selected → booked` transition — real money gates real status change. |
| 7 | **Budget tracker integrates booked costs** | `/trips/{id}/budget` separates booked (paid via Stripe) vs. planned costs. The UI progress bar shows green for money actually spent. |
| 8 | **Graceful degradation** | If `STRIPE_SECRET_KEY` is unset, everything still works — items just get marked booked directly. No Stripe, no crash. |
| 9 | **Credit gating** | `POST /plan` deducts 1 credit before starting agents. Returns HTTP 402 if balance too low — monetisation gates the expensive AI call. |

### Demo script (Stripe)

1. **Open the app** → show the landing page and dashboard
2. **Buy credits** → click "Buy Credits", select a package, complete Stripe Checkout in test mode → credits appear in the navbar
3. **Plan a trip** → show that 1 credit is deducted when planning starts
4. **Book a flight** → click "Book" on a flight → Stripe Checkout opens with the actual flight details → complete payment → redirected back with "✅ Flight booked!" banner, status changes to "✓ Booked"
5. **Book a hotel** → same flow for accommodations
6. **Show budget tracker** → point out that the budget bar now shows the booked costs in green vs. planned costs in yellow — real spend tracked from Stripe
7. **Show the webhook** → briefly show the backend log receiving the Stripe webhook and routing it by `item_type`

### Pitch angle

> "We didn't just add a payment button — Stripe is the **backbone of our booking economy**. Credits gate AI planning, Checkout handles real flight & hotel purchases, webhooks close the loop, and the budget tracker distinguishes paid vs. planned spend. Every Stripe payment changes real application state — from `selected` to `booked` — and the whole system degrades gracefully without Stripe keys. It's a **full commerce lifecycle** inside a trip planner."

---

## 2 · Best Adaptable Agent — Gift Bags

### What the judges want

> "An AI agent that adapts intelligently and reconsiders its approach when new information demands it."
> They cite incident.io's belief: *"the ability to revise your understanding of the problem is more valuable than the ability to commit to a first guess."*

### Our points

| # | Feature | How it adapts |
|---|---------|--------------|
| 1 | **Chat-based itinerary modification** | User says "it's raining" or "my flight was cancelled" → a CrewAI agent rewrites affected days while preserving unaffected ones. Multi-turn context from last 10 messages. |
| 2 | **Travel preference detection** | The chat agent extracts transport constraints from natural language: rain → avoid walking, metro strike → only walk. Stored as `travel_prefs` and applied to all route calculations. |
| 3 | **Weather disruption alerts + auto-adapt** | `/disruptions` fetches real Open-Meteo forecast for the trip dates. Heavy rain, strong wind, extreme heat/cold generate alerts. Each alert has an `auto_prompt` — one click sends it to the chat agent to adapt the plan. |
| 4 | **Route recalculation on preference change** | After any chat modification, `RouteAgent.compute_routes_for_day()` recalculates all walking/transit recommendations respecting the new avoid/prefer constraints. |
| 5 | **PlanValidator — self-reflection agent** | A 6th agent runs after initial planning and reviews the itinerary for geographic coherence (no zig-zagging), timing feasibility (not too many items), cost realism (no $200 breakfasts), meal coverage, and activity density. It fixes issues automatically and reports what it changed. |
| 6 | **Itinerary regeneration from changed selections** | User swaps their selected flight or hotel → "Regenerate itinerary" re-runs only the ItineraryPlanner agent with cached context + the new selection. Adapts the plan to the new hotel location or arrival time without re-running all 7 agents. |
| 7 | **Chat history persistence** | All user/assistant messages stored in DB. On reopen, full conversation loads. The agent sees prior context — it remembers "you said it was raining yesterday" and builds on that. |
| 8 | **Suggested disruption prompts** | Chat UI offers pre-built buttons: "It's raining", "Trains are cancelled today", "My return flight was cancelled" — one tap triggers adaptation. |
| 9 | **Item delay/complete lifecycle** | Users mark items as done or delay them to another day. The chat agent sees current item statuses and adapts around them. |
| 10 | **Auto-select best options** | After initial planning, the system automatically selects the cheapest flight per type and highest-rated hotel per city — a smart first guess that the user (or disruptions) can override. |

### Demo script (Adaptable Agent)

1. **Plan a trip to Paris** → show the 7-agent pipeline running (including PlanValidator at the end)
2. **Show the itinerary** → point out it's a well-structured plan with named restaurants, Google Maps links, and a "selected" hotel
3. **Weather alert appears** → "🌧️ Heavy rain forecast (28mm) on Day 2" with an "Auto-adapt" button
4. **Click Auto-adapt** → the chat agent rewrites Day 2: swaps the morning park visit for the Louvre, moves the outdoor café to an indoor bistro, adds a note about bringing an umbrella
5. **Type "trains are cancelled today"** → agent detects transport constraint, recalculates all routes to walking-only, updates the travel info badges between items
6. **Show the preference banner** → "Routes adjusted — avoiding transit 🚇" appears at the top
7. **Switch hotel selection** → pick a different hotel in Montmartre instead of Le Marais → click "Regenerate itinerary" → plan adapts to the new hotel neighbourhood
8. **Open chat again** → show it remembers the rain conversation and the transport constraint

### Pitch angle

> "Our agent doesn't just plan once — it **continuously adapts**. Weather changes? It fetches real forecasts and replans around rain. Trains cancelled? It detects the constraint from natural language and recalculates every route. User picks a different hotel? It regenerates the itinerary around the new neighbourhood — without re-running the entire pipeline. And the PlanValidator agent acts as a **built-in critic**: it catches geographic zig-zagging, unrealistic costs, and missing meals — then fixes them before the user ever sees the plan. This is an agent that treats its first answer as a **draft, not a verdict**."

---

## 3 · Best Use of Claude — $10,000

### What the judges want

> "Build a project that leverages Claude's API for reasoning, analysis, or automation."
> They highlight: 200K context window, tool use, multimodal understanding, complex agentic workflows.

### Our points

| # | Feature | How it uses Claude |
|---|---------|-------------------|
| 1 | **7 CrewAI agents all powered by Claude** | Set `LLM_PROVIDER=anthropic` → all agents (DestinationResearcher, CitySelector, FlightFinder, AccommodationFinder, ItineraryPlanner, PlanValidator, chat modifier) use `claude-sonnet-4-20250514`. Claude does ALL the reasoning. |
| 2 | **Complex geographic reasoning** | The ItineraryPlanner prompt instructs Claude to cluster activities by neighbourhood, plan meals near sights, avoid zig-zagging. Claude's reasoning handles spatial optimisation that simpler models struggle with. |
| 3 | **PlanValidator — self-reflection** | Claude-powered self-reflection agent that reviews its own team's output for coherence, timing, and cost realism. Claude critiquing Claude — demonstrating its meta-reasoning capability. |
| 4 | **Chat-based plan modification** | Claude agent reasons about disruptions ("it's raining" → which items are outdoors? → what are good indoor alternatives nearby?) and rewrites affected days while preserving context. |
| 5 | **Travel Guide crew with Tavily tool use** | Two Claude agents collaborate: TravelResearcher uses Tavily web search to find real local info (visa requirements, transit apps, tipping culture, SIM cards), then GuideWriter synthesises it into a comprehensive Markdown guide. **Tool use + long-form synthesis.** |
| 6 | **Claude vision for mood boards** | `_generate_vibe_anthropic()` sends upvoted/downvoted mood board images directly to Claude's vision API. Claude interprets visual aesthetics and produces a trip-vibe sentence — **multimodal understanding** in action. |
| 7 | **Tavily + ScrapeWebsite tool use** | DestinationResearcher and TravelResearcher agents use Claude with `TavilySearchTool` and `ScrapeWebsiteTool` — Claude decides when to search, what queries to run, and how to synthesise results. Full **agentic tool use** loop. |
| 8 | **200K context for travel guide** | The guide generation crew receives the full trip plan (itinerary, flights, hotels) + web research results — easily 50K+ tokens of context that Claude handles naturally. |
| 9 | **Structured JSON output** | Claude returns complex nested JSON (itineraries with days → items → locations, Google Maps URLs, local currency costs) reliably extracted through markdown-fence-stripping parser. |
| 10 | **Health endpoint proves Claude is active** | `GET /health` returns `{ "llm": "anthropic/claude-sonnet-4-20250514", "llm_provider": "anthropic" }` — instant proof during demo. |

### Demo script (Claude)

1. **Show `/health`** → the response shows `llm_provider: "anthropic"` and the Claude model name
2. **Plan a trip to Japan** → show the SSE stream with 7 agents running — all powered by Claude
3. **Point out the DestinationResearcher** → Claude is searching the web via Tavily for real-time info about Japan, then synthesising it into a research report
4. **Show the itinerary quality** → named restaurants in the right neighbourhoods, realistic local prices (¥1500 ramen, not $200), Google Maps links — Claude's geographic reasoning at work
5. **Show the PlanValidator** → "3 checks performed" — Claude critiquing its own team's output
6. **Generate a travel guide** → two Claude agents collaborate: one searches for visa requirements, Suica card info, tipping norms in Japan; the other writes a beautiful guide. Point out the specific app names (Navitime, Suica, PayPay) that came from web search.
7. **Show mood board → vibe** → upload images, show Claude vision interpreting them: "serene bamboo temples with lantern-lit streets and traditional tea houses"
8. **Modify via chat** → "There's a typhoon warning for day 3" → Claude reasons about which items are outdoors, finds indoor alternatives, preserves the rest
9. **Show multi-turn context** → send a follow-up "actually, can you also add a sake tasting?" — Claude remembers the typhoon context and places it at an indoor venue

### Pitch angle

> "Claude isn't a bolt-on — it's the **entire brain** of our system. Seven specialised agents all run on Claude, collaborating in a CrewAI pipeline. The ItineraryPlanner does **complex geographic reasoning** — clustering activities by neighbourhood and planning meals near sights. The PlanValidator demonstrates **self-reflection** — Claude critiquing Claude's own output. The Travel Guide crew shows **tool use** — Claude searching the web with Tavily, then synthesising results into a 3000-word guide. The vibe generator shows **multimodal understanding** — Claude interpreting mood board images. And the chat agent shows **adaptive reasoning** — understanding 'it's raining' means swap outdoor items for indoor ones nearby. We use Claude's 200K context, tool use, vision, and reasoning — not just as a text generator, but as a **complete decision-making engine** that plans, validates, adapts, and explains."

---

## Cross-Challenge Features (mention in all pitches)

| Feature | Stripe ✓ | Adapt ✓ | Claude ✓ |
|---------|:---:|:---:|:---:|
| Budget tracker (booked vs. planned spend) | ✅ | ✅ | — |
| SSE streaming (real-time agent progress) | — | ✅ | ✅ |
| Flight/hotel selection → booking pipeline | ✅ | ✅ | — |
| Google Maps route enrichment | — | ✅ | ✅ |
| Pinterest mood boards + vibe | — | — | ✅ |
| Multi-provider fallback (OpenAI ↔ Claude) | — | — | ✅ |
| Auto-select best options after planning | — | ✅ | ✅ |

---

## General Demo Tips

- **Start with the happy path**: Plan → View → Book. Judges need to understand the product before seeing the clever bits.
- **Use Japan or Paris**: Complex enough to show geographic reasoning, familiar enough that judges can verify quality.
- **Keep Stripe in test mode**: Use `4242 4242 4242 4242` for instant success.
- **Pre-plan one trip**: Have a completed trip ready so you don't wait 2-3 min for agents. Demo the planning SSE stream on a second trip.
- **Show the `/health` endpoint**: Quick proof of Claude being active if challenged.
- **Name-drop the tech stack**: "CrewAI for multi-agent orchestration, Tavily for web search, Open-Meteo for weather, Amadeus for flights, Stripe for payments, Claude for reasoning."
- **Have the chat ready**: Pre-type "It's raining on day 2" in the chat to show adaptation quickly.
- **Adaptation is the star**: The auto-adapt button on weather alerts is the most visually impressive feature — use it.
