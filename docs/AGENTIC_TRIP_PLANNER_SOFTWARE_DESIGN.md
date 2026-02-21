# Agentic Trip Planning Software - Comprehensive Design Document

## Executive Summary

This document presents a complete software design for an AI-powered trip planning platform that transforms how travelers discover, plan, and book their journeys. The system uses a multi-agent AI architecture to create personalized itineraries while providing direct booking capabilities.

### Key Capabilities
- **AI-Powered Planning**: Intelligent agents research destinations, find flights/hotels, and create optimized itineraries
- **Multi-City Support**: Automatically plans multi-city trips when destination is a country
- **Preference-Aware**: Respects dietary restrictions, accessibility needs, and travel style
- **Booking Integration**: Direct links to flights, accommodations, and attractions
- **Flexible Management**: Drag-drop itinerary editing with delay functionality

### Target Users
- Occasional travelers who want to maximize their trip experience
- Users seeking to avoid tourist traps and find authentic experiences
- Budget-conscious travelers looking for cheap hotels and flights

---

## 1. System Architecture

### 1.1 High-Level Architecture

**Pattern**: Hybrid Microservices with Modular Monolith Foundation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web App    │  │  Mobile PWA  │  │  React Native│  │  Admin Panel │    │
│  │   (Next.js)  │  │   (Future)   │  │   (Future)   │  │   (Next.js)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   CloudFront CDN    │
                          │   + WAF Protection  │
                          └──────────┬──────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
│                          ┌─────────▼─────────┐                               │
│                          │  AWS API Gateway  │                               │
│                          │  + Rate Limiting  │                               │
│                          └─────────┬─────────┘                               │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                         APPLICATION LAYER (EKS)                              │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐   │
│  │                         NestJS API Server                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │   Users    │ │   Trips    │ │  Planning  │ │     Bookings       │  │   │
│  │  │   Module   │ │   Module   │ │   Module   │ │     Module         │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │ Itinerary  │ │Preferences │ │Notification│ │   Integrations     │  │   │
│  │  │   Module   │ │   Module   │ │   Module   │ │     Module         │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                    AI Planning Service (Serverless)                     │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │   LangGraph│ │  OpenAI   │ │  Pinecone  │ │  Prompt Management │  │   │
│  │  │   Agent    │ │   Client   │ │  Vector DB │ │     (LangSmith)    │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                    Background Workers (BullMQ)                          │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │   │
│  │  │  Planning  │ │   Email    │ │   Search   │ │    Analytics       │  │   │
│  │  │   Worker   │ │   Worker   │ │   Indexer  │ │     Worker         │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                            DATA LAYER                                        │
│  ┌──────────────┐  ┌──────────────┐┌──────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL  │  │    Redis     │││Elasticsearch │  │    Pinecone      │  │
│  │   (RDS)      │  │  (ElastiCache)│ │   (OpenSearch)│  │   (Vector DB)    │  │
│  │  Primary DB  │  │Cache/Session │││    Search    │  │   Embeddings     │  │
│  └──────────────┘  └──────────────┘│└──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                        EXTERNAL INTEGRATIONS                                 │
│  ┌──────────────┐  ┌──────────────┐┌──────────────┐  ┌──────────────────┐  │
│  │   Amadeus    │  │  Booking.com │││ GetYourGuide │  │   Mapbox/Maps    │  │
│  │   (Flights)  │  │   (Hotels)   │││ (Attractions)│  │   (Geocoding)    │  │
│  └──────────────┘  └──────────────┘│└──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Skyscanner  │  │   Expedia    │  │    Viator    │  │  OpenWeatherMap  │  │
│  │  (Fallback)  │  │  (Fallback)  │  │  (Fallback)  │  │    (Weather)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Frontend** | Next.js 14 + Tailwind CSS | SSR for SEO, excellent performance, React ecosystem |
| **Backend** | NestJS (Node.js) | Enterprise-grade, TypeScript-first, excellent DI |
| **Database** | PostgreSQL 16 (RDS) | ACID compliance, complex relationships |
| **Cache** | Redis 7 (ElastiCache) | Sessions, query caching, rate limiting |
| **Search** | Elasticsearch 8 | Full-text search, geospatial queries |
| **Queue** | BullMQ (Redis-based) | Excellent Node.js integration, job scheduling |
| **AI/LLM** | OpenAI GPT-4 + LangGraph | Best reasoning, agent orchestration |
| **Vector DB** | Pinecone | Semantic search, RAG context |
| **Auth** | Clerk | Managed auth, social logins |
| **Hosting** | AWS EKS | Managed Kubernetes, auto-scaling |
| **Monitoring** | Datadog | APM, logs, metrics in one platform |

### 1.3 External API Integrations

| Service | Primary | Fallbacks |
|---------|---------|-----------|
| **Flights** | Amadeus API | Skyscanner, Kiwi |
| **Hotels** | Booking.com | Expedia, Agoda |
| **Attractions** | GetYourGuide | Viator, Tiqets |
| **Maps** | Mapbox | Google Maps |
| **Weather** | OpenWeatherMap | WeatherAPI |

---

## 2. AI Agent System Design

### 2.1 Agent Roles (14 Specialized Agents)

| Category | Agent | Purpose |
|----------|-------|---------|
| **User & Setup** | UserProfileManager | Manage user accounts, preferences, and historical travel data |
| | TripInitializer | Validate trip parameters and determine planning scope |
| **Research** | DestinationResearcher | Gather comprehensive destination information |
| | CitySelector | Select optimal cities for country-level trips |
| | AttractionCurator | Curate attractions based on user interests |
| | RestaurantFinder | Find dining options matching dietary restrictions |
| **Booking** | FlightFinder | Find and recommend optimal flight options |
| | AccommodationFinder | Find and recommend accommodations |
| **Planning** | ItineraryPlanner | Create optimized day-by-day itineraries (Master Orchestrator) |
| | BudgetOptimizer | Optimize trip for cost-effectiveness |
| | QualityValidator | Validate itinerary quality and suggest improvements |
| **Management** | FlightManager | Manage flight bookings and changes |
| | AccommodationManager | Manage accommodation bookings |
| | ItineraryManager | Handle real-time itinerary modifications and delays |

### 2.2 Agent Orchestration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                                 │
│  (Trip Creation Form, Management Dashboard, Itinerary Viewer)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                  │
│                    (Master Trip Planning Coordinator)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐         ┌───────────────────┐         ┌───────────────────┐
│  USER AGENTS  │         │  RESEARCH AGENTS  │         │  BOOKING AGENTS   │
├───────────────┤         ├───────────────────┤         ├───────────────────┤
│UserProfileMgr │         │DestinationResearch│         │  FlightFinder     │
│TripInitializer│         │   CitySelector    │         │AccommodationFinder│
│               │         │ AttractionCurator │         │                   │
│               │         │ RestaurantFinder  │         │                   │
└───────────────┘         └───────────────────┘         └───────────────────┘
                                      │                             │
                                      ▼                             ▼
                    ┌───────────────────────────────────────────────────────┐
                    │              PLANNING & OPTIMIZATION AGENTS            │
                    ├───────────────────────────────────────────────────────┤
                    │  ItineraryPlanner (Master) → BudgetOptimizer          │
                    │         ↓                                               │
                    │  QualityValidator (Final Check)                       │
                    └───────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────────────────────────┐
                    │              MANAGEMENT AGENTS                         │
                    ├───────────────────────────────────────────────────────┤
                    │  FlightManager, AccommodationManager, ItineraryManager│
                    └───────────────────────────────────────────────────────┘
```

### 2.3 Planning Workflow (13 Steps)

```
PHASE 1: TRIP INITIALIZATION
├── Step 1: User creates trip
│   └── Agent: TripInitializer → Output: Trip record, planning scope
├── Step 2: Load user profile
│   └── Agent: UserProfileManager → Output: Preferences, restrictions
│
PHASE 2: RESEARCH & DISCOVERY (Parallel)
├── Step 3: Destination research
│   └── Agent: DestinationResearcher → Output: Destination knowledge base
├── Step 4: Flight search
│   └── Agent: FlightFinder → Output: Flight options
├── Step 5: Accommodation search
│   └── Agent: AccommodationFinder → Output: Hotel options
│
PHASE 3: MULTI-CITY PLANNING (Conditional)
├── Step 6: City selection (IF country destination)
│   └── Agent: CitySelector → Output: City itinerary with logistics
│
PHASE 4: CONTENT CURATION
├── Step 7: Attraction curation
│   └── Agent: AttractionCurator → Output: Curated attraction list
├── Step 8: Restaurant discovery
│   └── Agent: RestaurantFinder → Output: Restaurant recommendations
│
PHASE 5: ITINERARY CONSTRUCTION
├── Step 9: Master itinerary planning
│   └── Agent: ItineraryPlanner → Output: Day-by-day itinerary
├── Step 10: Budget optimization
│   └── Agent: BudgetOptimizer → Output: Optimized itinerary with savings
├── Step 11: Quality validation
│   └── Agent: QualityValidator → Output: Validated itinerary with score
│
PHASE 6: DELIVERY & MANAGEMENT
├── Step 12: Present to user
│   └── Format: Interactive itinerary with maps, booking links
└── Step 13: Management setup
    └── Agents: FlightManager, AccommodationManager, ItineraryManager
```

### 2.4 Optimization Strategies

#### Avoiding Tourist Traps
- **Sentiment Analysis**: Analyze reviews for keywords like "overpriced", "crowded", "disappointing"
- **Local vs Tourist Ratio**: Prioritize places locals frequent
- **Price-to-Value Analysis**: Compare entry fees to experience quality

#### Finding Cheap Options
- Search multiple date combinations (±3 days)
- Check alternative nearby airports
- Compare across platforms (Booking, Airbnb, Hostelworld)
- Suggest free activities, discount passes, public transport

#### Maximizing Attractions
- **Geographic Clustering**: Group nearby attractions
- **Smart Scheduling**: Visit popular attractions early/late
- **Time Optimization**: Book timed entry, skip-the-line tickets

#### Respecting Dietary Restrictions
- Filter restaurants with dietary tags
- Verify through multiple sources
- Cross-reference menu photos
- Check for certification (halal, kosher)

---

## 3. Database Schema

### 3.1 Core Entities (27 Tables)

#### User Management
- `users` - Account management with OAuth support
- `user_sessions` - Authentication tokens

#### Destination Management
- `countries` - Destination countries with geospatial data
- `cities` - Cities with IATA codes for flight search
- `city_areas` - Neighborhoods for accommodation recommendations

#### Trip Management
- `trips` - Central trip entity with AI planning status
- `trip_destinations` - Multi-city trip support

#### Categories & Interests
- `categories` - Hierarchical interest categories (Pinterest-ready)
- `trip_categories` - User-selected interests per trip

#### Preferences & Restrictions
- `dietary_restrictions` - Pre-populated dietary needs
- `accessibility_needs` - Pre-populated accessibility requirements
- `trip_preferences` - Trip-specific preferences (JSONB for flexibility)

#### Itinerary Management
- `itineraries` - AI-generated trip plans with versioning
- `itinerary_days` - Daily breakdown
- `itinerary_items` - Individual activities with **delay functionality**

#### Attractions
- `attractions` - Points of interest with external API caching
- `attraction_reviews` - Cached external reviews

#### Booking Management
- `flights` - Flight options and bookings
- `flight_search_cache` - Performance caching
- `accommodations` - Hotel/lodging with booking status
- `accommodation_search_cache` - Performance caching
- `booking_links` - Polymorphic booking URLs

#### AI & System
- `ai_planning_jobs` - Background job tracking with retry logic
- `ai_feedback` - Continuous improvement data
- `notifications` - User notifications
- `user_activities` - Analytics logging (partitioned)
- `external_api_logs` - API call audit trail (partitioned)

### 3.2 Key Design Features

| Feature | Implementation |
|---------|----------------|
| **Multi-city trips** | `trip_destinations` table with visit_order |
| **Delay functionality** | `itinerary_items.delayed_to_day_id` field |
| **Pinterest integration** | `categories.pinterest_board_id` + `trip_categories.pinterest_pins` |
| **Dietary/Accessibility** | Reference tables + `trip_preferences` arrays |
| **AI confidence scoring** | `itinerary_items.ai_confidence_score` |
| **External API caching** | `external_data` JSONB + `external_data_cached_at` |
| **Full-text search** | PostgreSQL tsvector on cities, attractions |
| **Geospatial queries** | PostGIS geography types |
| **Row Level Security** | RLS policies for user data isolation |

---

## 4. API Design

### 4.1 API Endpoints Overview (60+ Endpoints)

#### Authentication (7 endpoints)
- `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
- `POST /auth/forgot-password`, `/auth/reset-password`
- `GET /auth/oauth/{provider}`

#### User Management (6 endpoints)
- Profile: `GET/PUT /users/me`
- Preferences: `GET/PUT /users/me/preferences`
- Security: `PUT /users/me/password`, `DELETE /users/me/account`

#### Trip CRUD (6 endpoints)
- `GET/POST /trips` (list/create)
- `GET/PUT/DELETE /trips/{tripId}` (detail/update/delete)
- `POST /trips/{tripId}/duplicate`

#### Planning Workflow (4 endpoints)
- `POST /trips/{tripId}/planning` - Start AI planning
- `GET /trips/{tripId}/planning` - Get status
- `POST /trips/{tripId}/planning/cancel` - Cancel
- `POST /trips/{tripId}/planning/regenerate` - Regenerate

#### City Management (5 endpoints)
- `GET/POST /trips/{tripId}/cities`
- `PUT/DELETE /trips/{tripId}/cities/{cityId}`
- `PUT /trips/{tripId}/cities/reorder`

#### Flight Management (7 endpoints)
- `GET/POST /trips/{tripId}/flights`
- `GET/PUT/DELETE /trips/{tripId}/flights/{flightId}`
- `POST /trips/{tripId}/flights/{flightId}/select`
- `POST /trips/{tripId}/flights/{flightId}/book`

#### Accommodation Management (7 endpoints)
- `GET/POST /trips/{tripId}/accommodations`
- `GET/PUT/DELETE /trips/{tripId}/accommodations/{id}`
- `POST /trips/{tripId}/accommodations/{id}/select`
- `POST /trips/{tripId}/accommodations/{id}/book`

#### Itinerary Management (10 endpoints)
- `GET/PUT /trips/{tripId}/itinerary` (full)
- `GET/PUT /trips/{tripId}/itinerary/days/{date}` (day)
- `POST /trips/{tripId}/itinerary/items` (add)
- `PUT/DELETE /trips/{tripId}/itinerary/items/{itemId}`
- **Key Feature:** `POST /trips/{tripId}/itinerary/items/{itemId}/delay` - Delay item to another day
- `POST /trips/{tripId}/itinerary/items/{itemId}/complete`
- `PUT /trips/{tripId}/itinerary/reorder`
- `POST /trips/{tripId}/itinerary/optimize` - AI optimization

#### External Search (7 endpoints)
- `GET/POST /search/flights`
- `GET/POST /search/hotels`
- `GET/POST /search/attractions`
- `GET /search/autocomplete`

#### Pinterest Integration (4 endpoints)
- `POST /users/me/pinterest/connect`
- `GET /users/me/pinterest/boards`
- `GET /users/me/pinterest/interests`
- `POST /trips/{tripId}/pinterest/import`

#### Real-time (WebSocket/SSE)
- WebSocket: `wss://api.tripplanner.com/v1/ws/connect`
- SSE: `https://api.tripplanner.com/v1/sse/subscribe`

---

## 5. User Experience Design

### 5.1 User Journey Map

```
PHASE 1: DISCOVERY → ONBOARDING → FIRST TRIP SETUP
[Landing Page] → [Sign Up/Login] → [Welcome Tour] → [Dashboard]

PHASE 2: TRIP CREATION WIZARD (5 Steps)
Step 1: Destination → Step 2: Dates → Step 3: Trip Type → Step 4: Interests → Step 5: Preferences

PHASE 3: AI PLANNING → REVIEW & EDIT → BOOKING
[Processing] → [Itinerary View] → [Edit Mode] → [Booking Links]

PHASE 4: TRIP MANAGEMENT
PRE-TRIP: [Itinerary] ↔ [Flights] ↔ [Hotels]
DURING TRIP: [Mobile View]
POST-TRIP: [Review]
```

### 5.2 Key Pages

| Page | Key Features |
|------|--------------|
| **Landing Page** | Hero CTA, social proof, feature grid, testimonials |
| **Signup/Login** | Social auth, progressive profiling, onboarding |
| **Dashboard** | Trip cards, quick actions, recommendations, empty state |
| **Trip Creation Wizard** | 5-step flow (Destination → Dates → Travelers → Interests → Preferences) |
| **AI Planning State** | Progress animation, fun facts, ETA, cancel option |
| **Itinerary View** | Day selector, activity cards, map panel, weather, budget |
| **Flight Management** | Booked flights, AI recommendations, price tracking |
| **Accommodation** | List/map views, booking status, amenities filter |
| **Settings/Preferences** | Profile, travel defaults, notifications, connected accounts |

### 5.3 Drag & Drop Itinerary Management

**Features:**
- Reordering within same day (auto time-adjust)
- Moving to different days (conflict detection)
- Context menu with delay options
- Delayed items panel for rescheduling

**AI vs User Content Indicators:**
- ⭐ AI-generated content
- 👤 User-added content
- ⭐↔️👤 AI-modified based on user feedback

### 5.4 Responsive Design

- **Mobile (<640px)**: Single column, bottom nav, touch-optimized
- **Tablet (640-1024px)**: 2-column layouts, adapted navigation
- **Desktop (1024-1440px)**: Full layouts, sidebar navigation
- **Wide (>1440px)**: Enhanced layouts, more information density

---

## 6. Implementation Roadmap

### Phase 1: MVP (Months 1-3)
- [ ] Core user management (Clerk integration)
- [ ] Basic trip CRUD
- [ ] Simple AI planning (single destination)
- [ ] PostgreSQL + Redis setup
- [ ] Amadeus + Booking.com integration
- [ ] Basic itinerary management

### Phase 2: Enhanced Features (Months 4-6)
- [ ] Multi-city trip planning
- [ ] Preference/restriction system
- [ ] Flight management page
- [ ] Hotel management page
- [ ] Attraction integration (GetYourGuide)
- [ ] Elasticsearch for search

### Phase 3: Scale & Optimize (Months 7-9)
- [ ] Advanced AI agent (LangGraph)
- [ ] Vector database for RAG
- [ ] Background job system
- [ ] Notification system
- [ ] Performance optimization
- [ ] Mobile PWA

### Phase 4: Enterprise & Advanced (Months 10-12)
- [ ] Team collaboration
- [ ] Advanced analytics
- [ ] White-label options
- [ ] React Native app
- [ ] Internationalization

---

## 7. Key Features Summary

### User Goals Addressed

| User Goal | Feature Implementation |
|-----------|----------------------|
| **Maximize time spent well** | AI-optimized daily schedules, geographic clustering, smart scheduling |
| **See more attractions** | Efficient routing, skip-the-line recommendations, time estimates |
| **Avoid tourist traps** | Sentiment analysis, local vs tourist ratio detection, authentic recommendations |
| **Find cheap hotels and flights** | Multi-platform search, price alerts, budget optimization, discount passes |

### Core Differentiators
1. **True Multi-Agent AI**: 14 specialized agents working together
2. **Country-Level Planning**: Automatically plans multi-city trips
3. **Preference-Aware**: Deep understanding of dietary, accessibility, and style preferences
4. **Integrated Booking**: Direct links to book everything in one place
5. **Flexible Management**: Easy drag-drop editing with intelligent delay handling

---

## Appendix: Generated Files

| File | Description |
|------|-------------|
| `/mnt/okcomputer/output/trip-planner-architecture.md` | Complete architecture document |
| `/mnt/okcomputer/output/agent_system_design.md` | Detailed agent system design |
| `/mnt/okcomputer/output/trip_planner_schema.sql` | PostgreSQL DDL with all tables |
| `/mnt/okcomputer/output/trip_planner_api_specification.yaml` | OpenAPI 3.0.3 specification |
| `/mnt/okcomputer/output/ux_specification_agentic_trip_planner.md` | Complete UX specification |
| `/mnt/okcomputer/output/external_api_integration_patterns.md` | External API integration patterns |
| `/mnt/okcomputer/output/websocket_sse_specification.md` | Real-time updates specification |
| `/mnt/okcomputer/output/database_design_documentation.md` | Database design documentation |

---

*Document Version: 1.0*
*System: Agentic Trip Planning Software*
*Architecture: Multi-Agent AI with Microservices Foundation*
