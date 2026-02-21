# Agentic Trip Planner - Database Design Documentation

## Executive Summary

This document describes the comprehensive database schema for an Agentic Trip Planning Software. The design prioritizes:
- **Data integrity** through proper normalization
- **Query performance** via strategic indexing
- **Scalability** through partitioning and caching strategies
- **Flexibility** using JSONB for dynamic data
- **AI integration** with dedicated tables for planning jobs and feedback

---

## Entity Relationship Diagram (Conceptual)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENTITIES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    users     │◄──────┤    trips     │◄──────┤  itineraries │
└──────────────┘       └──────────────┘       └──────────────┘
                              │                       │
                              ▼                       ▼
                       ┌──────────────┐       ┌──────────────┐
                       │trip_destinat-│       │itinerary_days│
                       │   ions       │       └──────────────┘
                       └──────────────┘              │
                              │                       ▼
                              ▼               ┌──────────────┐
                       ┌──────────────┐       │itinerary_    │
                       │   cities     │       │   items      │
                       └──────────────┘       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  countries   │
                       └──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           BOOKING ENTITIES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   flights    │       │accommodations│       │booking_links │
└──────────────┘       └──────────────┘       └──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        ATTRACTION ENTITIES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  attractions │◄──────┤  categories  │       │ city_areas   │
└──────────────┘       └──────────────┘       └──────────────┘
        │
        ▼
┌──────────────┐
│attraction_   │
│  reviews     │
└──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      PREFERENCE ENTITIES                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐   ┌────────────────────┐   ┌──────────────────┐
│dietary_restrict- │   │  trip_preferences  │   │accessibility_    │
│     ions         │   │                    │   │     needs        │
└──────────────────┘   └────────────────────┘   └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI & CACHE ENTITIES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐   ┌────────────────────┐   ┌──────────────────┐
│ ai_planning_jobs │   │ flight_search_cache│   │accommodation_    │
│                  │   │                    │   │  search_cache    │
└──────────────────┘   └────────────────────┘   └──────────────────┘

┌──────────────────┐   ┌────────────────────┐   ┌──────────────────┐
│   ai_feedback    │   │ external_api_logs  │   │  notifications   │
└──────────────────┘   └────────────────────┘   └──────────────────┘
```

---

## Detailed Entity Descriptions

### 1. User Management

#### `users` Table
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Argon2id hashed password |
| first_name | VARCHAR(100) | NOT NULL | User's first name |
| last_name | VARCHAR(100) | NOT NULL | User's last name |
| phone | VARCHAR(20) | | Contact phone number |
| avatar_url | TEXT | | Profile picture URL |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| is_email_verified | BOOLEAN | DEFAULT FALSE | Email verification status |
| oauth_provider | VARCHAR(50) | | 'google', 'pinterest', 'apple' |
| oauth_provider_id | VARCHAR(255) | | External OAuth ID |
| preferences | JSONB | DEFAULT '{}' | Flexible user preferences |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Account creation time |

**Design Decisions:**
- OAuth support built-in for Pinterest integration
- JSONB preferences allow flexible preference storage without schema changes
- Security fields (failed_login_attempts, locked_until) for brute force protection

#### `user_sessions` Table
Manages authentication tokens and session tracking.

---

### 2. Destination Management

#### `countries` Table
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| iso_code | CHAR(2) | UNIQUE, NOT NULL | ISO 3166-1 alpha-2 code |
| name | VARCHAR(100) | NOT NULL | Country name |
| location | GEOGRAPHY(POINT) | | Capital/centroid coordinates |
| bounds | GEOGRAPHY(POLYGON) | | Country boundaries |
| currency_code | CHAR(3) | | Primary currency |
| timezone | VARCHAR(50) | | Primary timezone |
| popularity_score | DECIMAL(3,2) | | Tourism popularity (0-1) |
| avg_daily_cost_* | INTEGER | | Budget indicators per travel style |

**Design Decisions:**
- PostGIS geography types for geospatial queries (find nearby destinations)
- Budget indicators for AI trip cost estimation
- External IDs for Google Places/TripAdvisor integration

#### `cities` Table
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| country_id | UUID | FK → countries | Parent country |
| name | VARCHAR(100) | NOT NULL | City name |
| name_local | VARCHAR(100) | | Local language name |
| aliases | VARCHAR(100)[] | | Alternative names |
| location | GEOGRAPHY(POINT) | NOT NULL | City coordinates |
| city_type | VARCHAR(20) | | 'capital', 'major_city', 'city', 'town' |
| population | INTEGER | | City population |
| popularity_score | DECIMAL(3,2) | | Tourism popularity |
| iata_code | CHAR(3) | | Airport code for flight search |
| search_vector | TSVECTOR | | Full-text search index |

**Design Decisions:**
- Full-text search with weighted fields (name = high weight, description = medium)
- Trigram index for fuzzy search ("Paree" matches "Paris")
- IATA code for direct flight API integration

#### `city_areas` Table
Neighborhoods/districts within cities for accommodation recommendations.

---

### 3. Trip Management

#### `trips` Table (Central Entity)
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique trip identifier |
| user_id | UUID | FK → users | Trip owner |
| title | VARCHAR(200) | NOT NULL | Trip name |
| trip_status | VARCHAR(20) | | 'planning', 'booked', 'in_progress', 'completed' |
| primary_destination_type | VARCHAR(10) | NOT NULL | 'city' or 'country' |
| primary_city_id | UUID | FK → cities | If city trip |
| primary_country_id | UUID | FK → countries | If country trip |
| start_date | DATE | NOT NULL | Trip start |
| end_date | DATE | NOT NULL | Trip end |
| duration_days | INTEGER | GENERATED | Calculated trip length |
| num_travelers | INTEGER | NOT NULL | Number of people |
| budget_total_max | INTEGER | | Total budget limit |
| planning_status | VARCHAR(20) | | AI planning status |
| ai_planning_job_id | UUID | | Reference to AI job |
| trip_purpose | VARCHAR(50) | | 'leisure', 'business', 'adventure', etc. |
| travel_pace | VARCHAR(20) | | 'relaxed', 'moderate', 'fast' |
| is_public | BOOLEAN | DEFAULT FALSE | Share trip publicly |
| share_token | VARCHAR(64) | UNIQUE | Token for sharing |
| total_estimated_cost | DECIMAL(10,2) | | Denormalized total cost |

**Design Decisions:**
- Polymorphic destination (city OR country) with CHECK constraint validation
- Denormalized cost fields for quick trip summary queries
- Share token for easy trip sharing without authentication
- AI planning job reference for tracking generation status

#### `trip_destinations` Table
For multi-city/country trips, stores each destination with visit order.

| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Parent trip |
| destination_type | VARCHAR(10) | 'city' or 'country' |
| visit_order | INTEGER | Sequence of visits |
| arrival_date | DATE | When arriving |
| departure_date | DATE | When leaving |
| nights | INTEGER | Length of stay |
| is_primary_destination | BOOLEAN | Main destination flag |

---

### 4. Categories and Interests

#### `categories` Table (Hierarchical)
| Field | Type | Description |
|-------|------|-------------|
| name | VARCHAR(50) | Unique category key |
| display_name | VARCHAR(100) | Human-readable name |
| parent_category_id | UUID | Self-reference for hierarchy |
| level | INTEGER | Depth in hierarchy (1 = root) |
| pinterest_board_id | VARCHAR(100) | Pinterest integration |
| pinterest_keyword | VARCHAR(100) | Search keyword |

**Hierarchy Example:**
```
Culture & History (Level 1)
├── Museums (Level 2)
├── Historical Sites (Level 2)
└── Architecture (Level 2)
```

#### `trip_categories` Table
Links trips to selected categories with priority.

| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Parent trip |
| category_id | UUID | Selected category |
| priority | INTEGER | 1-10 importance rating |
| pinterest_pins | JSONB | Cached Pinterest data |

---

### 5. Preferences and Restrictions

#### `dietary_restrictions` Table (Reference Data)
Pre-populated with common restrictions:
- vegetarian, vegan, halal, kosher
- gluten_free, dairy_free, nut_free
- pescatarian, keto

#### `accessibility_needs` Table (Reference Data)
Pre-populated with:
- wheelchair, mobility_limited
- visual_impairment, hearing_impairment
- stroller_friendly

#### `trip_preferences` Table
Stores trip-specific preferences as JSONB for flexibility.

| Field | Type | Description |
|-------|------|-------------|
| dietary_restriction_ids | UUID[] | Selected dietary needs |
| accessibility_need_ids | UUID[] | Selected accessibility needs |
| custom_restrictions | TEXT | Free-form restrictions |
| accommodation_types | VARCHAR(20)[] | Preferred lodging types |
| accommodation_amenities | VARCHAR(50)[] | Must-have amenities |
| preferred_activity_times | VARCHAR(20)[] | 'morning', 'afternoon', 'evening' |
| avoid_crowds | BOOLEAN | Prefer less crowded times |
| prefer_offbeat | BOOLEAN | Avoid tourist traps |
| additional_preferences | JSONB | Extensible preferences |

---

### 6. Itinerary Management

#### `itineraries` Table
| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Parent trip |
| version | INTEGER | AI may generate multiple options |
| is_selected | BOOLEAN | User's chosen itinerary |
| generated_by | VARCHAR(50) | 'ai', 'manual', 'hybrid' |
| ai_model_version | VARCHAR(50) | AI model used |
| total_activities | INTEGER | Denormalized count |
| total_estimated_cost | DECIMAL(10,2) | Denormalized cost |

#### `itinerary_days` Table
Each day of the itinerary.

| Field | Type | Description |
|-------|------|-------------|
| itinerary_id | UUID | Parent itinerary |
| day_number | INTEGER | Day sequence |
| date | DATE | Calendar date |
| city_id | UUID | Location for the day |
| title | VARCHAR(200) | Day theme/title |
| total_activities | INTEGER | Denormalized count |

#### `itinerary_items` Table (Core Activity Entity)
| Field | Type | Description |
|-------|------|-------------|
| itinerary_day_id | UUID | Parent day |
| item_order | INTEGER | Sequence within day |
| start_time | TIME | Activity start |
| end_time | TIME | Activity end |
| duration_minutes | INTEGER | Length of activity |
| item_type | VARCHAR(30) | 'attraction', 'meal', 'transport', etc. |
| attraction_id | UUID | Link to attraction (if applicable) |
| title | VARCHAR(200) | Activity name |
| description | TEXT | Details |
| booking_required | BOOLEAN | Needs advance booking |
| booking_status | VARCHAR(20) | 'none', 'pending', 'booked' |
| booking_url | TEXT | Direct booking link |
| cost_per_person | DECIMAL(10,2) | Estimated cost |
| status | VARCHAR(20) | 'planned', 'completed', 'skipped', 'delayed' |
| delayed_to_day_id | UUID | For delay functionality |
| ai_recommendation_reason | TEXT | Why AI suggested this |
| ai_confidence_score | DECIMAL(3,2) | AI confidence (0-1) |
| user_rating | INTEGER | Post-visit rating |
| external_ids | JSONB | {google_places_id, tripadvisor_id} |

**Key Feature: Delay Functionality**
The `delayed_to_day_id` field enables the "delay to another day" feature:
- When user delays an item, update `status = 'delayed'` and set `delayed_to_day_id`
- Create new item in target day with same details
- Original item preserved for history

---

### 7. Attractions and Activities

#### `attractions` Table
| Field | Type | Description |
|-------|------|-------------|
| city_id | UUID | Location |
| name | VARCHAR(200) | Attraction name |
| name_local | VARCHAR(200) | Local name |
| attraction_type | VARCHAR(50) | 'museum', 'landmark', 'park', etc. |
| category_ids | UUID[] | Linked categories |
| address | TEXT | Full address |
| location | GEOGRAPHY(POINT) | Precise coordinates |
| opening_hours | JSONB | {"monday": {"open": "09:00", "close": "17:00"}} |
| typical_visit_duration | INTEGER | Minutes |
| crowdedness_level | VARCHAR(20) | 'low', 'moderate', 'high' |
| pricing_type | VARCHAR(20) | 'free', 'paid', 'donation' |
| price_adult | DECIMAL(10,2) | Adult ticket price |
| avg_rating | DECIMAL(2,1) | Average user rating |
| review_count | INTEGER | Number of reviews |
| accessibility_features | JSONB | {wheelchair_accessible: true, ...} |
| tags | VARCHAR(50)[] | For AI matching |
| google_places_id | VARCHAR(255) | Google Places API ID |
| tripadvisor_id | VARCHAR(255) | TripAdvisor ID |
| getyourguide_id | VARCHAR(100) | GYG booking ID |
| viator_id | VARCHAR(100) | Viator booking ID |
| image_urls | TEXT[] | Photo gallery |
| search_vector | TSVECTOR | Full-text search |
| external_data | JSONB | Cached API response |
| external_data_cached_at | TIMESTAMPTZ | Cache timestamp |
| is_verified | BOOLEAN | Verified by admin |

**Design Decisions:**
- Multiple external IDs for different booking platforms
- JSONB opening_hours for complex schedules (holidays, seasonal)
- Cached external data reduces API calls
- Full-text search on name, description, and tags

#### `attraction_reviews` Table
Cached reviews from external sources.

| Field | Type | Description |
|-------|------|-------------|
| attraction_id | UUID | Parent attraction |
| source | VARCHAR(50) | 'google', 'tripadvisor' |
| external_review_id | VARCHAR(255) | Source review ID |
| author_name | VARCHAR(100) | Reviewer name |
| rating | INTEGER | 1-5 stars |
| review_text | TEXT | Review content |
| review_date | DATE | When reviewed |
| cached_at | TIMESTAMPTZ | Cache timestamp |

---

### 8. Flight Management

#### `flights` Table
| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Parent trip |
| flight_type | VARCHAR(20) | 'outbound', 'return', 'domestic' |
| departure_airport_code | CHAR(3) | IATA departure code |
| arrival_airport_code | CHAR(3) | IATA arrival code |
| departure_datetime | TIMESTAMPTZ | Departure time |
| arrival_datetime | TIMESTAMPTZ | Arrival time |
| duration_minutes | INTEGER | Flight duration |
| airline_code | CHAR(2) | IATA airline code |
| flight_number | VARCHAR(20) | Flight identifier |
| cabin_class | VARCHAR(20) | 'economy', 'business', 'first' |
| price_per_person | DECIMAL(10,2) | Cost per traveler |
| total_price | DECIMAL(10,2) | Total cost |
| booking_status | VARCHAR(20) | 'suggested', 'considering', 'booked' |
| booking_reference | VARCHAR(50) | Confirmation number |
| booking_platform | VARCHAR(50) | Where booked |
| booking_url | TEXT | Direct booking link |
| external_flight_id | VARCHAR(255) | API identifier |
| external_data | JSONB | Cached API response |

#### `flight_search_cache` Table
| Field | Type | Description |
|-------|------|-------------|
| search_hash | VARCHAR(64) | Hash of search params |
| origin_airport | CHAR(3) | From airport |
| destination_airport | CHAR(3) | To airport |
| departure_date | DATE | Travel date |
| return_date | DATE | Return date (if round-trip) |
| passengers | INTEGER | Number of travelers |
| results | JSONB | Cached search results |
| cached_at | TIMESTAMPTZ | When cached |
| expires_at | TIMESTAMPTZ | Cache expiration |
| hit_count | INTEGER | Usage counter |

**Caching Strategy:**
- Cache key = hash(origin + destination + dates + passengers + class)
- TTL = 1 hour (flight prices change frequently)
- Hit tracking for cache effectiveness analysis

---

### 9. Accommodation Management

#### `accommodations` Table
| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Parent trip |
| city_id | UUID | Location |
| property_name | VARCHAR(200) | Hotel/property name |
| property_type | VARCHAR(30) | 'hotel', 'hostel', 'apartment', etc. |
| address | TEXT | Full address |
| location | GEOGRAPHY(POINT) | Coordinates |
| check_in_date | DATE | Arrival |
| check_out_date | DATE | Departure |
| nights | INTEGER | GENERATED (checkout - checkin) |
| room_type | VARCHAR(100) | Room category |
| num_rooms | INTEGER | Rooms booked |
| num_guests | INTEGER | Guests |
| amenities | JSONB | ['wifi', 'pool', 'gym'] |
| price_per_night | DECIMAL(10,2) | Nightly rate |
| total_price | DECIMAL(10,2) | Total cost |
| star_rating | DECIMAL(2,1) | Hotel stars |
| guest_rating | DECIMAL(2,1) | User rating |
| booking_status | VARCHAR(20) | 'suggested', 'booked', etc. |
| booking_platform | VARCHAR(50) | 'booking.com', 'airbnb' |
| booking_url | TEXT | Direct booking link |
| free_cancellation_until | DATE | Cancellation deadline |
| external_property_id | VARCHAR(255) | API identifier |
| image_urls | TEXT[] | Property photos |

#### `accommodation_search_cache` Table
Similar structure to flight search cache with hotel-specific parameters.

---

### 10. Booking Links

#### `booking_links` Table (Polymorphic)
Generic table for attraction/activity booking links.

| Field | Type | Description |
|-------|------|-------------|
| linkable_type | VARCHAR(30) | 'attraction', 'trip', 'itinerary_item' |
| linkable_id | UUID | Parent entity ID |
| provider | VARCHAR(50) | 'getyourguide', 'viator', 'klook' |
| booking_url | TEXT | Direct link |
| deeplink_url | TEXT | Mobile app link |
| price_from | DECIMAL(10,2) | Starting price |
| affiliate_code | VARCHAR(100) | Tracking code |
| cached_at | TIMESTAMPTZ | When cached |
| expires_at | TIMESTAMPTZ | Cache expiration |

---

### 11. AI Planning and Background Jobs

#### `ai_planning_jobs` Table
| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Trip being planned |
| status | VARCHAR(20) | 'queued', 'processing', 'completed', 'failed' |
| worker_id | VARCHAR(100) | Processing worker |
| started_at | TIMESTAMPTZ | When processing began |
| completed_at | TIMESTAMPTZ | When finished |
| input_params | JSONB | Trip requirements sent to AI |
| result_data | JSONB | AI-generated itinerary data |
| error_message | TEXT | If failed |
| retry_count | INTEGER | Failed attempt count |
| max_retries | INTEGER | Default 3 |
| next_retry_at | TIMESTAMPTZ | When to retry |
| tokens_used | INTEGER | AI API usage |
| model_version | VARCHAR(50) | AI model version |

**Retry Logic:**
- Failed jobs retry with exponential backoff
- Max 3 retries before manual intervention
- next_retry_at enables delayed retry scheduling

#### `ai_feedback` Table
For continuous AI improvement.

| Field | Type | Description |
|-------|------|-------------|
| trip_id | UUID | Related trip |
| itinerary_id | UUID | Related itinerary |
| feedback_type | VARCHAR(30) | 'rating', 'correction', 'suggestion' |
| rating | INTEGER | 1-5 satisfaction |
| feedback_text | TEXT | Detailed feedback |
| rated_item_type | VARCHAR(30) | What was rated |
| rated_item_id | UUID | Specific item rated |
| user_id | UUID | Who gave feedback |

---

### 12. External API Management

#### `external_api_logs` Table (Partitioned)
| Field | Type | Description |
|-------|------|-------------|
| api_provider | VARCHAR(50) | 'google_places', 'amadeus', 'booking' |
| api_endpoint | VARCHAR(200) | API endpoint called |
| request_method | VARCHAR(10) | GET, POST, etc. |
| request_params | JSONB | Parameters sent |
| response_status | INTEGER | HTTP status code |
| response_body | JSONB | Response data |
| error_message | TEXT | If error occurred |
| request_started_at | TIMESTAMPTZ | Call start |
| request_completed_at | TIMESTAMPTZ | Call end |
| duration_ms | INTEGER | Response time |
| rate_limit_remaining | INTEGER | API quota remaining |

**Partitioning Strategy:**
- Partitioned by month (created_at)
- Automatic partition creation via cron job
- Old partitions archived after 90 days

---

## Indexing Strategy

### Core Indexes

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| users | idx_users_email | B-tree | Login lookup |
| users | idx_users_oauth | B-tree | OAuth authentication |
| cities | idx_cities_location | GiST | Nearby city queries |
| cities | idx_cities_search | GIN | Full-text search |
| cities | idx_cities_name_trgm | GIN | Fuzzy name matching |
| trips | idx_trips_user_status | B-tree | User's trip list |
| trips | idx_trips_planning | B-tree | Find trips needing AI |
| itinerary_items | idx_itinerary_items_order | B-tree | Day schedule display |
| itinerary_items | idx_itinerary_items_delayed | B-tree | Delayed items query |
| attractions | idx_attractions_location | GiST | Nearby attractions |
| attractions | idx_attractions_search | GIN | Full-text search |
| flights | idx_flights_route | B-tree | Route-based queries |
| accommodations | idx_accommodations_dates | B-tree | Date availability |

---

## Caching Strategies

### 1. External API Data Caching

**Attractions Table:**
- `external_data` JSONB caches full API response
- `external_data_cached_at` tracks freshness
- TTL: 7 days for stable data, 1 day for dynamic data

**Flight Search Cache:**
- Hash-based lookup for identical searches
- TTL: 1 hour (prices change frequently)
- Hit tracking for effectiveness analysis

**Accommodation Search Cache:**
- Similar to flight cache
- TTL: 2 hours (more stable than flights)

### 2. Booking Links Caching

- Cached with expiration aligned to provider policies
- Affiliate codes preserved for revenue tracking
- Deeplink URLs for mobile app integration

### 3. Review Caching

- External reviews cached to reduce API calls
- Update frequency based on review velocity
- Source attribution maintained

---

## Scalability Considerations

### 1. Partitioning

**Partitioned Tables:**
- `external_api_logs` - By month
- `user_activities` - By month
- `notifications` - By month (optional)

### 2. Read Replicas

Recommended read replica usage:
- Attraction searches
- Trip browsing
- Report generation
- Analytics queries

### 3. Connection Pooling

- Use PgBouncer for connection pooling
- Separate pools for OLTP and reporting

### 4. Archival Strategy

| Data Type | Retention | Archive To |
|-----------|-----------|------------|
| API logs | 90 days | S3/ Glacier |
| User activities | 1 year | Data warehouse |
| Old notifications | 30 days | Soft delete |
| Completed trips | Forever | Keep (compress JSONB) |

---

## Security Features

### 1. Row Level Security (RLS)

Enabled on all user-data tables:
```sql
CREATE POLICY users_own_data ON users
    FOR ALL USING (id = current_setting('app.current_user_id')::UUID);
```

### 2. Data Encryption

- Passwords: Argon2id hashing
- PII: Consider column-level encryption for sensitive fields
- Connections: TLS required

### 3. Audit Trail

- `created_at` and `updated_at` on all tables
- `user_activities` table for action logging
- `external_api_logs` for third-party integration audit

---

## Query Patterns

### 1. Get Trip Summary
```sql
SELECT * FROM trip_summary 
WHERE user_id = ? AND trip_status = 'planning';
```

### 2. Find Attractions by Category
```sql
SELECT * FROM attractions 
WHERE category_ids @> ARRAY[?]::UUID[] 
  AND city_id = ?
ORDER BY popularity_score DESC;
```

### 3. Get Daily Itinerary
```sql
SELECT * FROM itinerary_day_detail 
WHERE itinerary_id = ? 
ORDER BY day_number;
```

### 4. Search Cities
```sql
SELECT * FROM cities 
WHERE search_vector @@ plainto_tsquery('english', ?)
   OR name % ?  -- Trigram fuzzy match
ORDER BY popularity_score DESC 
LIMIT 10;
```

### 5. Nearby Attractions
```sql
SELECT * FROM attractions 
WHERE ST_DWithin(
    location, 
    ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, 
    5000  -- 5km radius
)
ORDER BY ST_Distance(location, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography);
```

---

## Migration Strategy

### Version Control
- Use migrations tool (Flyway, Liquibase, or custom)
- Each migration has up/down scripts
- Migrations are idempotent

### Zero-Downtime Migrations
1. Create new table/column
2. Dual-write to old and new
3. Backfill data
4. Switch reads to new
5. Remove old

### Example Migration Pattern
```sql
-- Step 1: Add new column
ALTER TABLE trips ADD COLUMN new_field TYPE;

-- Step 2: Create trigger for dual-write
CREATE TRIGGER sync_new_field 
    BEFORE INSERT OR UPDATE ON trips
    FOR EACH ROW EXECUTE FUNCTION sync_new_field_fn();

-- Step 3: Backfill
UPDATE trips SET new_field = compute_from_old(old_field);

-- Step 4: Make required
ALTER TABLE trips ALTER COLUMN new_field SET NOT NULL;

-- Step 5: Drop old
ALTER TABLE trips DROP COLUMN old_field;
```

---

## Performance Monitoring

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Query response time (p95) | < 100ms | > 500ms |
| Index hit ratio | > 99% | < 95% |
| Cache hit ratio | > 80% | < 60% |
| Connection pool usage | < 70% | > 90% |
| Replication lag | < 1s | > 5s |

### Slow Query Analysis
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

---

## Conclusion

This database schema provides a solid foundation for an Agentic Trip Planning Software with:

1. **Comprehensive entity coverage** for all core features
2. **AI integration** through dedicated planning and feedback tables
3. **Performance optimization** via strategic indexing and caching
4. **Scalability** through partitioning and read replicas
5. **Flexibility** using JSONB for dynamic data
6. **Security** with RLS and proper access controls

The design supports the key user goals:
- Maximize time well spent → AI-optimized itineraries with confidence scores
- See more attractions → Efficient scheduling with travel time consideration
- Avoid tourist traps → `prefer_offbeat` preference and AI recommendations
- Find cheap options → Budget tracking and price comparison via booking links
