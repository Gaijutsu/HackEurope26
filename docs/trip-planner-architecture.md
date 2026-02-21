# Agentic Trip Planning Software - System Architecture Document

## Executive Summary

This document outlines the comprehensive system architecture for an AI-powered trip planning platform. The architecture follows a **hybrid microservices approach** with domain-driven design principles, leveraging cloud-native technologies for scalability and resilience.

---

## 1. High-Level Architecture Decision

### 1.1 Architecture Pattern: Hybrid Microservices with Modular Monolith Foundation

**Decision: Start with Modular Monolith, Evolve to Microservices**

| Aspect | Decision | Justification |
|--------|----------|---------------|
| **Core Pattern** | Modular Monolith → Microservices | Faster initial development, clear module boundaries for future extraction |
| **Deployment** | Containerized on Kubernetes | Industry standard, excellent orchestration, cloud-agnostic |
| **Compute Model** | Traditional containers + Serverless for AI workloads | Cost optimization for sporadic AI processing |
| **Data Strategy** | Polyglot persistence | Different data needs for different domains |

### 1.2 Why Not Pure Microservices from Day 1?

1. **Team Size**: Small-medium teams benefit from simpler deployment
2. **Development Velocity**: Faster feature delivery with shared codebase
3. **Operational Complexity**: Reduced infrastructure overhead initially
4. **Migration Path**: Clear module boundaries enable gradual extraction

### 1.3 When to Extract Services

- **AI Planning Service**: First candidate when AI workload exceeds 60% of compute
- **Booking Integration Service**: When supporting 5+ booking providers
- **Notification Service**: When notification volume exceeds 100K/day

---

## 2. Technology Stack Recommendations

### 2.1 Frontend Architecture

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Primary Framework** | Next.js 14 (App Router) | SSR for SEO, excellent performance, React ecosystem |
| **State Management** | Zustand + TanStack Query | Lightweight, excellent server state handling |
| **UI Component Library** | shadcn/ui + Tailwind CSS | Customizable, accessible, modern design system |
| **Maps Integration** | Mapbox GL JS | Better pricing than Google Maps, excellent customization |
| **Mobile Strategy** | PWA + React Native (future) | Progressive approach, PWA covers 80% of needs initially |

**Frontend Structure:**
```
/frontend
├── /app                    # Next.js App Router
│   ├── /(auth)            # Auth group (login, register)
│   ├── /(dashboard)       # Main app group
│   │   ├── /trips         # Trip management
│   │   ├── /planning      # AI planning interface
│   │   ├── /flights       # Flight management
│   │   ├── /hotels        # Accommodation management
│   │   └── /itinerary     # Daily itinerary
│   └── /api               # API routes for serverless functions
├── /components            # Shared components
├── /lib                   # Utilities, hooks
└── /types                 # TypeScript definitions
```

### 2.2 Backend Architecture

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Primary Framework** | Node.js + NestJS | Enterprise-grade, TypeScript-first, excellent DI |
| **API Style** | GraphQL (Apollo) + REST | GraphQL for complex queries, REST for simple CRUD |
| **Authentication** | Auth0 / Clerk | Managed auth, social logins, enterprise SSO |
| **Authorization** | CASL (NestJS integration) | Fine-grained permissions, resource-based |
| **Validation** | Zod + class-validator | Runtime type safety, excellent DX |

**Backend Module Structure:**
```
/backend
├── /src
│   ├── /modules
│   │   ├── /users         # User management
│   │   ├── /trips         # Trip CRUD, destination logic
│   │   ├── /planning      # AI planning orchestration
│   │   ├── /bookings      # Flight/hotel/attraction aggregation
│   │   ├── /itinerary     # Daily schedule management
│   │   ├── /preferences   # User preferences & restrictions
│   │   ├── /notifications # Email, push notifications
│   │   └── /integrations  # External API wrappers
│   ├── /common            # Shared utilities, guards, interceptors
│   ├── /config            # Configuration management
│   └── /database          # Migrations, seeds
```

### 2.3 Database Layer - Polyglot Persistence

| Data Type | Database | Justification |
|-----------|----------|---------------|
| **Primary Data** | PostgreSQL 16 | ACID compliance, complex relationships, JSON support |
| **Caching** | Redis 7 | Session store, rate limiting, query caching |
| **Search** | Elasticsearch 8 | Full-text search, geospatial queries for locations |
| **Session/Realtime** | Redis Pub/Sub | Real-time itinerary updates, collaboration |
| **Analytics** | ClickHouse (future) | High-volume event analytics |

**PostgreSQL Schema Highlights:**
```sql
-- Core entities with relationships
users (id, email, profile, preferences_json, created_at)
trips (id, user_id, name, destination_type, destination_id, start_date, end_date, status)
cities (id, name, country_code, coordinates, popularity_score)
itinerary_days (id, trip_id, day_number, date, notes)
itinerary_items (id, day_id, type, title, start_time, end_time, booking_ref, metadata_json)
preferences (id, user_id, category, key, value) -- dietary, accessibility, interests
```

### 2.4 Message Queue & Async Processing

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Primary Queue** | BullMQ (Redis-based) | Excellent Node.js integration, job scheduling |
| **Event Bus** | Apache Kafka (future scale) | Event sourcing, cross-service communication |
| **Background Jobs** | BullMQ Workers | AI planning, email notifications, data sync |

**Queue Architecture:**
```
Queues:
├── planning-queue        # AI trip planning requests
├── booking-sync-queue    # Sync booking data from providers
├── notification-queue    # Email, push notifications
├── search-index-queue    # Elasticsearch indexing
└── analytics-queue       # Event tracking
```

### 2.5 AI/LLM Integration Architecture

| Component | Technology | Justification |
|-----------|------------|---------------|
| **LLM Provider** | OpenAI GPT-4 / Claude 3.5 | Best reasoning for complex planning |
| **Fallback LLM** | Azure OpenAI | Enterprise compliance, rate limit buffer |
| **Embedding Model** | OpenAI text-embedding-3-large | RAG for destination knowledge |
| **Vector Database** | Pinecone / Weaviate | Semantic search for attractions, restaurants |
| **LLM Framework** | LangChain / LangGraph | Agent orchestration, tool calling |
| **Prompt Management** | LangSmith / Helicone | Versioning, observability, A/B testing |

**AI Planning Agent Architecture:**
```
Planning Agent Flow:
1. Input Parser → Extract destination, dates, preferences
2. Context Gatherer → Fetch destination data from vector DB
3. Constraint Analyzer → Apply dietary, accessibility, budget constraints
4. Itinerary Generator → LLM generates day-by-day plan
5. Booking Link Enricher → Attach real booking URLs
6. Validator → Check feasibility, opening hours
7. Output Formatter → Structured response
```

### 2.6 External API Integrations

| Service Type | Primary Provider | Fallback Provider |
|--------------|------------------|-------------------|
| **Flights** | Amadeus API | Skyscanner API, Kiwi API |
| **Hotels** | Booking.com API | Expedia API, Agoda API |
| **Attractions** | GetYourGuide API | Viator API, Tiqets API |
| **Geocoding** | Mapbox Geocoding | Google Geocoding |
| **Places Data** | Google Places API | Foursquare API |
| **Weather** | OpenWeatherMap | WeatherAPI |
| **Currency** | ExchangeRate-API | Open Exchange Rates |

**Integration Pattern - API Gateway + Circuit Breaker:**
```typescript
// Circuit breaker pattern for external APIs
@Injectable()
class FlightService {
  constructor(
    private amadeusClient: AmadeusClient,
    private skyscannerClient: SkyscannerClient,
    private circuitBreaker: CircuitBreakerService
  ) {}

  async searchFlights(query: FlightQuery): Promise<Flight[]> {
    return this.circuitBreaker.execute(
      'amadeus-flights',
      () => this.amadeusClient.search(query),
      () => this.skyscannerClient.search(query) // fallback
    );
  }
}
```

### 2.7 Deployment Infrastructure

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Cloud Provider** | AWS (primary) / GCP (DR) | Broadest service offering, enterprise adoption |
| **Container Orchestration** | Amazon EKS | Managed Kubernetes, excellent ecosystem |
| **CI/CD** | GitHub Actions → ArgoCD | GitOps deployment, excellent visibility |
| **Infrastructure as Code** | Terraform + Pulumi | Terraform for infra, Pulumi for app resources |
| **Monitoring** | Datadog / Grafana Stack | APM, logs, metrics in one platform |
| **Error Tracking** | Sentry | Best-in-class error tracking |
| **CDN** | CloudFront + Cloudflare | Global edge caching, DDoS protection |

**Deployment Environments:**
```
Development → Staging → Production
     ↓            ↓           ↓
  EKS Dev     EKS Staging   EKS Prod
  (1 node)    (2 nodes)     (3+ AZs, auto-scaling)
```

---

## 3. System Component Diagram

### 3.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web App    │  │  Mobile PWA  │  │  React Native│  │  Admin Panel │    │
│  │   (Next.js)  │  │   (Future)   │  │   (Future)   │  │   (Next.js)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   CloudFront CDN    │
                          │   + WAF Protection  │
                          └──────────┬──────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
├────────────────────────────────────┼─────────────────────────────────────────┤
│                          ┌─────────▼─────────┐                               │
│                          │  AWS API Gateway  │                               │
│                          │  + Rate Limiting  │                               │
│                          └─────────┬─────────┘                               │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                         APPLICATION LAYER (EKS)                              │
├────────────────────────────────────┼─────────────────────────────────────────┤
│                                    │                                         │
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
│  │  │   LangGraph │ │  OpenAI   │ │  Pinecone  │ │  Prompt Management │  │   │
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
├────────────────────────────────────┼─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐│┌──────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL  │  │    Redis     │││Elasticsearch │  │    Pinecone      │  │
│  │   (RDS)      │  │  (ElastiCache)│ │   (OpenSearch)│  │   (Vector DB)    │  │
│  │  Primary DB  │  │Cache/Session │││    Search    │  │   Embeddings     │  │
│  └──────────────┘  └──────────────┘│└──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                        EXTERNAL INTEGRATIONS                                 │
├────────────────────────────────────┼─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐│┌──────────────┐  ┌──────────────────┐  │
│  │   Amadeus    │  │  Booking.com │││ GetYourGuide │  │   Mapbox/Maps    │  │
│  │   (Flights)  │  │   (Hotels)   │││ (Attractions)│  │   (Geocoding)    │  │
│  └──────────────┘  └──────────────┘│└──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Skyscanner  │  │   Expedia    │  │    Viator    │  │  OpenWeatherMap  │  │
│  │  (Fallback)  │  │  (Fallback)  │  │  (Fallback)  │  │    (Weather)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow Diagrams

#### Trip Creation Flow
```
User → Create Trip Form
  │
  ▼
[Frontend] Validate inputs → POST /api/trips
  │
  ▼
[API Gateway] Auth check → Rate limit
  │
  ▼
[Trip Module] Create trip record (PostgreSQL)
  │
  ├─→ Store destination preferences
  ├─→ Initialize trip status: 'draft'
  └─→ Trigger: planning-requested event
  │
  ▼
[Message Queue] planning-queue
  │
  ▼
[Planning Worker] Process planning request
  │
  ├─→ Fetch destination context (Pinecone)
  ├─→ Call LLM with structured prompt
  ├─→ Parse and validate response
  ├─→ Enrich with booking links (external APIs)
  └─→ Store generated itinerary
  │
  ▼
[Notification] Send completion email
  │
  ▼
User receives notification → Views AI-generated trip plan
```

#### Flight Search Flow
```
User → Flight Management Page → Search flights
  │
  ▼
[Frontend] POST /api/bookings/flights/search
  │
  ▼
[Booking Module] Validate request
  │
  ├─→ Check cache (Redis) for recent results
  │   └─→ Cache hit: Return cached results
  │
  └─→ Cache miss: Call flight APIs
      │
      ├─→ [Circuit Breaker] Call Amadeus
      │   └─→ Success: Parse and normalize
      │   └─→ Failure: Fallback to Skyscanner
      │
      ├─→ Aggregate results from multiple sources
      ├─→ Apply user preferences (airlines, stops)
      ├─→ Cache results (Redis, 15 min TTL)
      └─→ Return to frontend
```

---

## 4. External Service Integration Points

### 4.1 Flight APIs

| Provider | API | Use Case | Rate Limits |
|----------|-----|----------|-------------|
| **Amadeus** | Self-Service API | Primary flight search | 2,000 req/month free, then paid |
| **Skyscanner** | Partner API | Fallback, price comparison | Requires partnership |
| **Kiwi** | Tequila API | Budget flights, multi-city | 1,000 req/day free |

**Integration Architecture:**
```typescript
interface FlightSearchProvider {
  search(query: FlightQuery): Promise<Flight[]>;
  getBookingUrl(flight: Flight): string;
}

class FlightAggregatorService {
  async searchAllProviders(query: FlightQuery): Promise<AggregatedFlights> {
    const providers = [this.amadeus, this.skyscanner, this.kiwi];
    const results = await Promise.allSettled(
      providers.map(p => p.search(query))
    );
    return this.mergeAndRank(results);
  }
}
```

### 4.2 Hotel APIs

| Provider | API | Use Case | Key Features |
|----------|-----|----------|--------------|
| **Booking.com** | Affiliate API | Primary hotel search | Largest inventory, good commissions |
| **Expedia** | EPS API | Fallback, package deals | Strong in North America |
| **Agoda** | Affiliate API | Asia-Pacific focus | Competitive Asia rates |

### 4.3 Attraction APIs

| Provider | API | Use Case | Key Features |
|----------|-----|----------|--------------|
| **GetYourGuide** | Partner API | Primary attractions | Skip-the-line tickets, reviews |
| **Viator** | Affiliate API | Fallback, tours | Strong tour operator network |
| **Tiqets** | API | Museums, cultural | Excellent museum coverage |

### 4.4 Integration Resilience Patterns

```typescript
// Circuit Breaker Configuration
const circuitBreakerConfig = {
  failureThreshold: 5,      // Open after 5 failures
  resetTimeout: 60000,      // Try again after 1 minute
  halfOpenRequests: 3,      // Test with 3 requests when half-open
};

// Retry Configuration
const retryConfig = {
  attempts: 3,
  backoff: 'exponential',
  initialDelay: 1000,
};

// Cache Strategy
const cacheStrategy = {
  ttl: 900,                 // 15 minutes for flight prices
  staleWhileRevalidate: 60, // Serve stale for 1 min while refreshing
};
```

---

## 5. Scalability Considerations

### 5.1 Horizontal Scaling Strategy

| Component | Scaling Approach | Trigger |
|-----------|------------------|---------|
| **API Servers** | HPA based on CPU/memory | CPU > 70%, Latency > 500ms |
| **AI Workers** | Queue-based scaling | Queue depth > 100 |
| **Database** | Read replicas + Connection pooling | Read load > 80% |
| **Cache** | Redis Cluster | Memory > 70% |
| **Search** | Elasticsearch nodes | Query latency > 200ms |

### 5.2 Database Scaling Roadmap

**Phase 1 (0-10K users):** Single RDS instance (db.t3.medium)
**Phase 2 (10K-100K users):** Read replica + PgBouncer connection pooling
**Phase 3 (100K-1M users):** Aurora PostgreSQL with auto-scaling
**Phase 4 (1M+ users):** Sharding by user_id, separate analytics DB

### 5.3 Caching Strategy

| Cache Layer | Technology | TTL | Use Case |
|-------------|------------|-----|----------|
| **CDN** | CloudFront | 1 hour | Static assets, API responses |
| **Application** | Redis | 15 min | Flight prices, hotel availability |
| **Session** | Redis | 24 hours | User sessions, auth tokens |
| **Database** | PostgreSQL | Varies | Query result cache |

### 5.4 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time** | P95 < 200ms | Datadog APM |
| **AI Planning Time** | < 30 seconds | LangSmith tracing |
| **Page Load Time** | < 2 seconds | Lighthouse |
| **Search Results** | < 1 second | Custom metrics |
| **Availability** | 99.9% | Datadog SLO |

### 5.5 Cost Optimization

| Strategy | Implementation | Expected Savings |
|----------|----------------|------------------|
| **Spot Instances** | 70% of worker nodes | 40-60% compute |
| **Reserved Capacity** | RDS 1-year commitment | 30-40% database |
| **CDN Caching** | Aggressive cache policies | 50-70% bandwidth |
| **AI Batching** | Batch LLM requests | 20-30% AI costs |
| **Smart Fallbacks** | Use cheaper APIs first | 15-25% API costs |

---

## 6. Security Architecture

### 6.1 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────┐
│                     AUTH FLOW                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User → Login/Register                                      │
│    │                                                        │
│    ▼                                                        │
│  [Clerk/Auth0] Verify credentials                           │
│    │                                                        │
│    ├─→ Issue JWT (access + refresh tokens)                  │
│    │                                                        │
│    ▼                                                        │
│  [Frontend] Store tokens (httpOnly cookies)                 │
│    │                                                        │
│    ▼                                                        │
│  [API Requests] Include JWT in Authorization header         │
│    │                                                        │
│    ▼                                                        │
│  [API Gateway] Validate JWT → Extract claims                │
│    │                                                        │
│    ▼                                                        │
│  [CASL] Check resource permissions                          │
│    │                                                        │
│    ▼                                                        │
│  [Database] Enforce RLS (Row Level Security)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Data Protection

| Layer | Protection | Implementation |
|-------|------------|----------------|
| **Transit** | TLS 1.3 | AWS ACM certificates |
| **At Rest** | AES-256 | RDS encryption, S3 SSE-KMS |
| **PII** | Tokenization | Hash sensitive fields |
| **API Keys** | Secrets Manager | AWS Secrets Manager rotation |

---

## 7. Monitoring & Observability

### 7.1 Observability Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **Metrics** | Datadog / Prometheus | System health, business metrics |
| **Logs** | Datadog / Loki | Centralized logging, search |
| **Traces** | Datadog APM / Jaeger | Distributed tracing |
| **Errors** | Sentry | Error tracking, alerting |
| **Uptime** | Pingdom / Datadog Synthetics | External monitoring |
| **LLM Observability** | LangSmith | Prompt tracking, cost analysis |

### 7.2 Key Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                      DASHBOARD                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │  Active     │ │  Trips      │ │  AI Plans   │ │  Avg Plan  │ │
│  │  Users      │ │  Created    │ │  Generated  │ │  Time      │ │
│  │  1,234      │ │  567        │ │  890        │ │  18s       │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  API Response Times (P50, P95, P99)                         ││
│  │  ████████████████████████████████████████                   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────┐ ┌────────────────────────────────┐│
│  │  External API Health     │ │  AI Token Usage & Costs        ││
│  │  ✅ Amadeus              │ │  Today: $124.50                ││
│  │  ✅ Booking.com          │ │  This Month: $3,456.78         ││
│  │  ⚠️  GetYourGuide        │ │  Avg per plan: $0.42           ││
│  └──────────────────────────┘ └────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Development & Deployment Workflow

### 8.1 CI/CD Pipeline

```
Developer Push → GitHub Actions
       │
       ├─→ Lint & Type Check
       ├─→ Unit Tests
       ├─→ Integration Tests
       ├─→ Build Docker Image
       ├─→ Push to ECR
       │
       ▼
  ArgoCD (GitOps)
       │
       ├─→ Detect image update
       ├─→ Run Helm template
       ├─→ Deploy to Staging
       ├─→ Smoke Tests
       │
       ▼
  Manual Approval → Deploy to Production
       │
       ▼
  Post-Deploy: Run migrations, verify health
```

### 8.2 Environment Configuration

| Environment | Purpose | Infrastructure |
|-------------|---------|----------------|
| **Local** | Development | Docker Compose |
| **Dev** | Feature testing | EKS (1 node) |
| **Staging** | Pre-production | EKS (2 nodes) |
| **Prod** | Live traffic | EKS (3+ AZs, auto-scale) |

---

## 9. Implementation Roadmap

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

## 10. Summary of Technology Choices

| Category | Primary Choice | Alternatives Considered |
|----------|----------------|------------------------|
| **Frontend** | Next.js 14 | Remix, Nuxt |
| **Backend** | NestJS + Node.js | FastAPI, Spring Boot |
| **Database** | PostgreSQL 16 | MySQL, CockroachDB |
| **Cache** | Redis 7 | Memcached, Valkey |
| **Search** | Elasticsearch | Algolia, Meilisearch |
| **Queue** | BullMQ | RabbitMQ, SQS |
| **AI/LLM** | OpenAI + LangChain | Anthropic, Llama |
| **Vector DB** | Pinecone | Weaviate, Chroma |
| **Auth** | Clerk | Auth0, Firebase Auth |
| **Hosting** | AWS EKS | GCP GKE, Azure AKS |
| **CI/CD** | GitHub + ArgoCD | GitLab CI, Jenkins |
| **Monitoring** | Datadog | New Relic, Grafana |

---

## Appendix: API Design Overview

### GraphQL Schema (Core Types)

```graphql
type Trip {
  id: ID!
  name: String!
  destination: Destination!
  startDate: Date!
  endDate: Date!
  status: TripStatus!
  preferences: [Preference!]!
  itinerary: [ItineraryDay!]!
  bookings: [Booking!]!
}

type ItineraryDay {
  id: ID!
  dayNumber: Int!
  date: Date!
  items: [ItineraryItem!]!
}

type ItineraryItem {
  id: ID!
  type: ItemType!
  title: String!
  startTime: DateTime
  endTime: DateTime
  location: Location
  booking: Booking
  notes: String
}

type Booking {
  id: ID!
  type: BookingType!
  provider: String!
  bookingUrl: String!
  price: Money
  status: BookingStatus!
}

enum ItemType {
  FLIGHT
  HOTEL
  ATTRACTION
  RESTAURANT
  ACTIVITY
  TRANSPORT
  FREE_TIME
}
```

---

*Document Version: 1.0*
*Last Updated: 2024*
*Author: System Architecture Team*
