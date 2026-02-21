-- ============================================================================
-- AGENTIC TRIP PLANNER - COMPREHENSIVE DATABASE SCHEMA
-- PostgreSQL 15+ Compatible
-- ============================================================================
-- Design Principles:
-- 1. Normalized schema for data integrity (3NF where practical)
-- 2. Strategic denormalization for read performance on hot paths
-- 3. JSONB for flexible schema areas (external API responses, preferences)
-- 4. Partitioning strategy for time-series data (bookings, itineraries)
-- 5. Comprehensive indexing for query performance
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis"; -- For geospatial queries on destinations
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search on names/descriptions

-- ============================================================================
-- CORE USER MANAGEMENT
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- Argon2id hashed
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    avatar_url TEXT,
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,
    
    -- Security
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    
    -- OAuth support (Pinterest, Google, etc.)
    oauth_provider VARCHAR(50), -- 'google', 'pinterest', 'apple'
    oauth_provider_id VARCHAR(255),
    
    -- Preferences stored as JSONB for flexibility
    preferences JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- User sessions for authentication
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL, -- Hashed JWT or session token
    refresh_token_hash VARCHAR(255),
    
    -- Session metadata
    ip_address INET,
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    
    -- Expiration
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Status
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ
);

-- ============================================================================
-- DESTINATION MANAGEMENT (Cities, Countries, Regions)
-- ============================================================================

CREATE TABLE countries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso_code CHAR(2) NOT NULL UNIQUE, -- ISO 3166-1 alpha-2
    iso_code_3 CHAR(3) UNIQUE, -- ISO 3166-1 alpha-3
    name VARCHAR(100) NOT NULL,
    name_local VARCHAR(100),
    
    -- Geospatial data
    location GEOGRAPHY(POINT, 4326), -- Capital or centroid
    bounds GEOGRAPHY(POLYGON, 4326), -- Country boundaries
    
    -- Metadata
    currency_code CHAR(3),
    timezone VARCHAR(50),
    language_codes VARCHAR(10)[],
    
    -- Tourism data (for recommendations)
    popularity_score DECIMAL(3,2) DEFAULT 0.00, -- 0.00 to 1.00
    avg_daily_cost_low INTEGER, -- Budget travel USD/day
    avg_daily_cost_mid INTEGER, -- Mid-range USD/day
    avg_daily_cost_high INTEGER, -- Luxury USD/day
    
    -- External IDs for API integration
    google_places_id VARCHAR(255),
    tripadvisor_id VARCHAR(255),
    
    -- Full-text search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_id UUID NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
    
    -- Naming
    name VARCHAR(100) NOT NULL,
    name_local VARCHAR(100),
    aliases VARCHAR(100)[], -- Alternative names
    
    -- Geospatial
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    
    -- Classification
    city_type VARCHAR(20) DEFAULT 'city' CHECK (city_type IN ('capital', 'major_city', 'city', 'town', 'village')),
    population INTEGER,
    
    -- Tourism metrics
    popularity_score DECIMAL(3,2) DEFAULT 0.00,
    is_tourist_destination BOOLEAN DEFAULT FALSE,
    best_visit_seasons VARCHAR(10)[], -- ['spring', 'summer', 'autumn', 'winter']
    
    -- External IDs
    google_places_id VARCHAR(255),
    tripadvisor_id VARCHAR(255),
    iata_code CHAR(3), -- For flight searches
    
    -- Full-text search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint for city+country combination
    CONSTRAINT unique_city_in_country UNIQUE (country_id, name)
);

-- City neighborhoods/areas (for accommodation recommendations)
CREATE TABLE city_areas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Geospatial bounds
    bounds GEOGRAPHY(POLYGON, 4326),
    center_location GEOGRAPHY(POINT, 4326),
    
    -- Characteristics
    area_type VARCHAR(30) CHECK (area_type IN ('historic_center', 'business_district', 'nightlife', 'residential', 'beach', 'suburb')),
    safety_rating INTEGER CHECK (safety_rating BETWEEN 1 AND 5),
    walkability_score INTEGER CHECK (walkability_score BETWEEN 1 AND 10),
    
    -- For recommendations
    is_recommended_for_tourists BOOLEAN DEFAULT FALSE,
    pros JSONB DEFAULT '[]',
    cons JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TRIP MANAGEMENT
-- ============================================================================

CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic info
    title VARCHAR(200) NOT NULL,
    description TEXT,
    trip_status VARCHAR(20) DEFAULT 'planning' 
        CHECK (trip_status IN ('planning', 'booked', 'in_progress', 'completed', 'cancelled')),
    
    -- Destination (can be city or country level)
    primary_destination_type VARCHAR(10) NOT NULL CHECK (primary_destination_type IN ('city', 'country')),
    primary_city_id UUID REFERENCES cities(id),
    primary_country_id UUID REFERENCES countries(id),
    
    -- Dates
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_days INTEGER GENERATED ALWAYS AS (end_date - start_date + 1) STORED,
    
    -- Travelers
    num_travelers INTEGER NOT NULL DEFAULT 1,
    traveler_details JSONB DEFAULT '[]', -- [{"type": "adult", "age": 30}, ...]
    
    -- Budget
    budget_currency CHAR(3) DEFAULT 'USD',
    budget_total_max INTEGER, -- Total trip budget
    budget_flight_max INTEGER,
    budget_accommodation_max INTEGER,
    budget_activities_max INTEGER,
    
    -- AI Planning
    planning_status VARCHAR(20) DEFAULT 'pending' 
        CHECK (planning_status IN ('pending', 'in_progress', 'completed', 'failed')),
    ai_planning_job_id UUID, -- Reference to background job
    ai_generated_at TIMESTAMPTZ,
    
    -- Trip settings
    trip_purpose VARCHAR(50) CHECK (trip_purpose IN ('leisure', 'business', 'adventure', 'romantic', 'family', 'solo')),
    travel_pace VARCHAR(20) DEFAULT 'moderate' CHECK (travel_pace IN ('relaxed', 'moderate', 'fast')),
    
    -- Metadata
    cover_image_url TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    share_token VARCHAR(64) UNIQUE, -- For sharing trip with others
    
    -- Statistics (denormalized for performance)
    total_estimated_cost DECIMAL(10,2),
    total_booked_cost DECIMAL(10,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_dates CHECK (end_date >= start_date),
    CONSTRAINT valid_destination CHECK (
        (primary_destination_type = 'city' AND primary_city_id IS NOT NULL) OR
        (primary_destination_type = 'country' AND primary_country_id IS NOT NULL)
    )
);

-- Trip destinations (for multi-city/country trips)
CREATE TABLE trip_destinations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Destination reference
    destination_type VARCHAR(10) NOT NULL CHECK (destination_type IN ('city', 'country')),
    city_id UUID REFERENCES cities(id),
    country_id UUID REFERENCES countries(id),
    
    -- Visit order and timing
    visit_order INTEGER NOT NULL,
    arrival_date DATE,
    departure_date DATE,
    nights INTEGER,
    
    -- Status
    is_primary_destination BOOLEAN DEFAULT FALSE,
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_destination_ref CHECK (
        (destination_type = 'city' AND city_id IS NOT NULL) OR
        (destination_type = 'country' AND country_id IS NOT NULL)
    )
);

-- ============================================================================
-- CATEGORIES AND INTERESTS (Pinterest Integration Ready)
-- ============================================================================

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Category info
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Hierarchy
    parent_category_id UUID REFERENCES categories(id),
    level INTEGER DEFAULT 1,
    
    -- Visual
    icon_url TEXT,
    color_hex CHAR(7),
    image_url TEXT,
    
    -- Pinterest integration
    pinterest_board_id VARCHAR(100),
    pinterest_keyword VARCHAR(100),
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User category preferences for trips
CREATE TABLE trip_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    
    -- Priority/importance
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    
    -- Pinterest integration
    pinterest_pins JSONB DEFAULT '[]', -- Cached pin data
    last_synced_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_trip_category UNIQUE (trip_id, category_id)
);

-- ============================================================================
-- USER PREFERENCES AND RESTRICTIONS
-- ============================================================================

CREATE TABLE dietary_restrictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    keywords VARCHAR(50)[], -- For AI matching with restaurants
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-populate common dietary restrictions
INSERT INTO dietary_restrictions (name, display_name, description, keywords) VALUES
('vegetarian', 'Vegetarian', 'No meat, poultry, or fish', ARRAY['vegetarian', 'meat-free', 'plant-based']),
('vegan', 'Vegan', 'No animal products', ARRAY['vegan', 'plant-based', 'dairy-free', 'egg-free']),
('halal', 'Halal', 'Islamic dietary laws', ARRAY['halal', 'muslim-friendly']),
('kosher', 'Kosher', 'Jewish dietary laws', ARRAY['kosher', 'jewish']),
('gluten_free', 'Gluten Free', 'No gluten-containing ingredients', ARRAY['gluten-free', 'celiac', 'coeliac']),
('dairy_free', 'Dairy Free', 'No dairy products', ARRAY['dairy-free', 'lactose-free']),
('nut_free', 'Nut Free', 'No tree nuts or peanuts', ARRAY['nut-free', 'peanut-free', 'allergy']),
('pescatarian', 'Pescatarian', 'Vegetarian plus fish', ARRAY['pescatarian', 'fish', 'seafood']),
('keto', 'Keto/Low Carb', 'Low carbohydrate diet', ARRAY['keto', 'low-carb', 'atkins']),
('halal_friendly', 'Halal Friendly', 'Halal options available', ARRAY['halal-friendly']);

CREATE TABLE accessibility_needs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-populate accessibility needs
INSERT INTO accessibility_needs (name, display_name, description) VALUES
('wheelchair', 'Wheelchair Accessible', 'Full wheelchair accessibility required'),
('mobility_limited', 'Limited Mobility', 'Limited walking ability, elevators preferred'),
('visual_impairment', 'Visual Impairment', 'Visual accessibility features needed'),
('hearing_impairment', 'Hearing Impairment', 'Hearing accessibility features needed'),
('stroller_friendly', 'Stroller Friendly', 'Suitable for strollers and young children');

-- Trip-level preferences and restrictions
CREATE TABLE trip_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Dietary restrictions (many-to-many via array for simplicity)
    dietary_restriction_ids UUID[],
    
    -- Accessibility needs
    accessibility_need_ids UUID[],
    
    -- Custom restrictions (free text)
    custom_restrictions TEXT,
    
    -- Accommodation preferences
    accommodation_types VARCHAR(20)[], -- ['hotel', 'hostel', 'airbnb', 'resort']
    accommodation_amenities VARCHAR(50)[], -- ['wifi', 'pool', 'gym', 'spa']
    min_accommodation_rating DECIMAL(2,1), -- Minimum star rating
    
    -- Activity preferences
    preferred_activity_times VARCHAR(20)[], -- ['morning', 'afternoon', 'evening']
    avoid_crowds BOOLEAN DEFAULT FALSE,
    prefer_offbeat BOOLEAN DEFAULT FALSE, -- Avoid tourist traps
    
    -- Transportation
    preferred_transport_modes VARCHAR(20)[], -- ['flight', 'train', 'bus', 'car']
    
    -- Additional JSONB for extensibility
    additional_preferences JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ITINERARY MANAGEMENT
-- ============================================================================

CREATE TABLE itineraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Itinerary version (AI may generate multiple options)
    version INTEGER DEFAULT 1,
    is_selected BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    name VARCHAR(100),
    description TEXT,
    
    -- AI generation info
    generated_by VARCHAR(50) DEFAULT 'ai', -- 'ai', 'manual', 'hybrid'
    ai_model_version VARCHAR(50),
    generation_prompt TEXT,
    
    -- Statistics
    total_activities INTEGER DEFAULT 0,
    total_estimated_cost DECIMAL(10,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_trip_version UNIQUE (trip_id, version)
);

-- Daily itinerary breakdown
CREATE TABLE itinerary_days (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    itinerary_id UUID NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
    
    -- Date info
    day_number INTEGER NOT NULL, -- Day 1, Day 2, etc.
    date DATE NOT NULL,
    
    -- Location
    city_id UUID REFERENCES cities(id),
    country_id UUID REFERENCES countries(id),
    
    -- Daily summary
    title VARCHAR(200),
    notes TEXT,
    
    -- Statistics
    total_activities INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_itinerary_day UNIQUE (itinerary_id, day_number)
);

-- Individual itinerary items/activities
CREATE TABLE itinerary_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    itinerary_day_id UUID NOT NULL REFERENCES itinerary_days(id) ON DELETE CASCADE,
    
    -- Ordering
    item_order INTEGER NOT NULL,
    
    -- Time
    start_time TIME,
    end_time TIME,
    duration_minutes INTEGER,
    
    -- Activity reference (can link to attraction or be free-form)
    item_type VARCHAR(30) NOT NULL CHECK (item_type IN (
        'attraction', 'activity', 'meal', 'transport', 
        'accommodation_checkin', 'accommodation_checkout',
        'free_time', 'custom'
    )),
    attraction_id UUID REFERENCES attractions(id), -- Defined below
    
    -- Free-form activity details
    title VARCHAR(200) NOT NULL,
    description TEXT,
    notes TEXT,
    
    -- Location
    location_name VARCHAR(200),
    location_address TEXT,
    location_coordinates GEOGRAPHY(POINT, 4326),
    
    -- Booking info
    booking_required BOOLEAN DEFAULT FALSE,
    booking_status VARCHAR(20) DEFAULT 'none' CHECK (booking_status IN ('none', 'pending', 'booked', 'cancelled')),
    booking_reference VARCHAR(100),
    booking_url TEXT,
    ticket_url TEXT,
    
    -- Cost
    cost_per_person DECIMAL(10,2),
    cost_currency CHAR(3) DEFAULT 'USD',
    is_included_in_pass BOOLEAN DEFAULT FALSE, -- City pass, etc.
    
    -- Status and management
    status VARCHAR(20) DEFAULT 'planned' CHECK (status IN ('planned', 'completed', 'skipped', 'delayed', 'cancelled')),
    delayed_to_day_id UUID REFERENCES itinerary_days(id),
    
    -- AI recommendations
    ai_recommendation_reason TEXT,
    ai_confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    
    -- User feedback
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    
    -- External data
    external_ids JSONB DEFAULT '{}', -- {google_places_id, tripadvisor_id, ...}
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ATTRACTIONS AND ACTIVITIES
-- ============================================================================

CREATE TABLE attractions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Location
    city_id UUID REFERENCES cities(id),
    country_id UUID REFERENCES countries(id),
    area_id UUID REFERENCES city_areas(id),
    
    -- Basic info
    name VARCHAR(200) NOT NULL,
    name_local VARCHAR(200),
    description TEXT,
    short_description VARCHAR(500),
    
    -- Classification
    attraction_type VARCHAR(50) CHECK (attraction_type IN (
        'museum', 'landmark', 'park', 'temple', 'church', 'mosque',
        'market', 'shopping', 'restaurant', 'entertainment', 
        'nature', 'beach', 'hiking', 'tour', 'workshop', 'event'
    )),
    category_ids UUID[], -- Links to categories
    
    -- Location details
    address TEXT,
    location GEOGRAPHY(POINT, 4326),
    directions TEXT,
    
    -- Contact
    phone VARCHAR(50),
    website_url TEXT,
    email VARCHAR(255),
    
    -- Operating hours (stored as JSONB for flexibility)
    opening_hours JSONB, -- {"monday": {"open": "09:00", "close": "17:00"}, ...}
    timezone VARCHAR(50),
    
    -- Visit info
    typical_visit_duration INTEGER, -- Minutes
    best_visit_time TEXT,
    crowdedness_level VARCHAR(20) CHECK (crowdedness_level IN ('low', 'moderate', 'high', 'very_high')),
    
    -- Pricing
    pricing_type VARCHAR(20) CHECK (pricing_type IN ('free', 'paid', 'donation')),
    price_adult DECIMAL(10,2),
    price_child DECIMAL(10,2),
    price_senior DECIMAL(10,2),
    price_student DECIMAL(10,2),
    price_currency CHAR(3),
    
    -- Ratings and reviews
    avg_rating DECIMAL(2,1),
    review_count INTEGER DEFAULT 0,
    
    -- Accessibility
    accessibility_features JSONB DEFAULT '{}',
    
    -- Tags for AI matching
    tags VARCHAR(50)[],
    
    -- External IDs
    google_places_id VARCHAR(255),
    tripadvisor_id VARCHAR(255),
    getyourguide_id VARCHAR(100),
    viator_id VARCHAR(100),
    
    -- Media
    image_urls TEXT[],
    primary_image_url TEXT,
    
    -- Full-text search
    search_vector TSVECTOR,
    
    -- Caching
    external_data_cached_at TIMESTAMPTZ,
    external_data JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attraction reviews (cached from external sources)
CREATE TABLE attraction_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attraction_id UUID NOT NULL REFERENCES attractions(id) ON DELETE CASCADE,
    
    -- Review source
    source VARCHAR(50) NOT NULL, -- 'google', 'tripadvisor', 'internal'
    external_review_id VARCHAR(255),
    
    -- Review content
    author_name VARCHAR(100),
    author_avatar_url TEXT,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    review_date DATE,
    
    -- Metadata
    helpful_count INTEGER DEFAULT 0,
    language_code VARCHAR(10),
    
    -- Caching
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_external_review UNIQUE (source, external_review_id)
);

-- ============================================================================
-- FLIGHT MANAGEMENT
-- ============================================================================

CREATE TABLE flights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Flight details
    flight_type VARCHAR(20) NOT NULL CHECK (flight_type IN ('outbound', 'return', 'domestic', 'connecting')),
    
    -- Route
    departure_airport_code CHAR(3) NOT NULL,
    arrival_airport_code CHAR(3) NOT NULL,
    departure_city_id UUID REFERENCES cities(id),
    arrival_city_id UUID REFERENCES cities(id),
    
    -- Times
    departure_datetime TIMESTAMPTZ NOT NULL,
    arrival_datetime TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    
    -- Airline
    airline_code CHAR(2),
    airline_name VARCHAR(100),
    flight_number VARCHAR(20),
    
    -- Booking class
    cabin_class VARCHAR(20) CHECK (cabin_class IN ('economy', 'premium_economy', 'business', 'first')),
    
    -- Pricing
    price_per_person DECIMAL(10,2),
    total_price DECIMAL(10,2),
    price_currency CHAR(3) DEFAULT 'USD',
    
    -- Booking status
    booking_status VARCHAR(20) DEFAULT 'suggested' 
        CHECK (booking_status IN ('suggested', 'considering', 'booked', 'cancelled')),
    
    -- Booking details
    booking_reference VARCHAR(50),
    booking_platform VARCHAR(50), -- 'booking.com', 'expedia', 'airline_direct'
    booking_url TEXT,
    pnr_code VARCHAR(20),
    
    -- Passengers
    passenger_details JSONB DEFAULT '[]',
    
    -- Layover info (for connecting flights)
    is_connecting_flight BOOLEAN DEFAULT FALSE,
    layover_airport_code CHAR(3),
    layover_duration_minutes INTEGER,
    
    -- External data
    external_flight_id VARCHAR(255), -- From flight API
    external_data JSONB DEFAULT '{}',
    external_data_cached_at TIMESTAMPTZ,
    
    -- User notes
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Flight search cache (for performance)
CREATE TABLE flight_search_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Search parameters hash
    search_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Search parameters
    origin_airport CHAR(3) NOT NULL,
    destination_airport CHAR(3) NOT NULL,
    departure_date DATE NOT NULL,
    return_date DATE,
    passengers INTEGER NOT NULL,
    cabin_class VARCHAR(20),
    
    -- Cached results
    results JSONB NOT NULL,
    
    -- Cache metadata
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Usage tracking
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ
);

-- ============================================================================
-- ACCOMMODATION MANAGEMENT
-- ============================================================================

CREATE TABLE accommodations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Stay details
    city_id UUID REFERENCES cities(id),
    area_id UUID REFERENCES city_areas(id),
    
    -- Property info
    property_name VARCHAR(200) NOT NULL,
    property_type VARCHAR(30) CHECK (property_type IN (
        'hotel', 'hostel', 'resort', 'apartment', 'bnb', 
        'guesthouse', 'villa', 'campsite', 'capsule'
    )),
    
    -- Location
    address TEXT,
    location GEOGRAPHY(POINT, 4326),
    
    -- Dates
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    nights INTEGER GENERATED ALWAYS AS (check_out_date - check_in_date) STORED,
    
    -- Room details
    room_type VARCHAR(100),
    num_rooms INTEGER DEFAULT 1,
    num_guests INTEGER NOT NULL,
    
    -- Amenities
    amenities JSONB DEFAULT '[]',
    
    -- Pricing
    price_per_night DECIMAL(10,2),
    total_price DECIMAL(10,2),
    price_currency CHAR(3) DEFAULT 'USD',
    taxes_fees DECIMAL(10,2),
    
    -- Ratings
    star_rating DECIMAL(2,1),
    guest_rating DECIMAL(2,1),
    review_count INTEGER,
    
    -- Booking status
    booking_status VARCHAR(20) DEFAULT 'suggested' 
        CHECK (booking_status IN ('suggested', 'considering', 'booked', 'cancelled')),
    
    -- Booking details
    booking_reference VARCHAR(50),
    booking_platform VARCHAR(50), -- 'booking.com', 'airbnb', 'expedia'
    booking_url TEXT,
    confirmation_number VARCHAR(100),
    
    -- Cancellation policy
    cancellation_policy TEXT,
    free_cancellation_until DATE,
    
    -- Contact
    property_phone VARCHAR(50),
    property_email VARCHAR(255),
    
    -- External IDs
    external_property_id VARCHAR(255),
    external_data JSONB DEFAULT '{}',
    external_data_cached_at TIMESTAMPTZ,
    
    -- Images
    image_urls TEXT[],
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_accommodation_dates CHECK (check_out_date > check_in_date)
);

-- Accommodation search cache
CREATE TABLE accommodation_search_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Search parameters hash
    search_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Search parameters
    city_id UUID REFERENCES cities(id),
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    guests INTEGER NOT NULL,
    rooms INTEGER DEFAULT 1,
    
    -- Cached results
    results JSONB NOT NULL,
    
    -- Cache metadata
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Usage tracking
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ
);

-- ============================================================================
-- BOOKING LINKS AND EXTERNAL INTEGRATIONS
-- ============================================================================

-- Generic booking links table for attractions, activities, etc.
CREATE TABLE booking_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Polymorphic reference
    linkable_type VARCHAR(30) NOT NULL, -- 'attraction', 'trip', 'itinerary_item'
    linkable_id UUID NOT NULL,
    
    -- Link details
    provider VARCHAR(50) NOT NULL, -- 'getyourguide', 'viator', 'klook', 'expedia'
    provider_display_name VARCHAR(100),
    booking_url TEXT NOT NULL,
    deeplink_url TEXT, -- Mobile app deep link
    
    -- Pricing
    price_from DECIMAL(10,2),
    price_currency CHAR(3) DEFAULT 'USD',
    
    -- Availability
    is_available BOOLEAN DEFAULT TRUE,
    availability_note TEXT,
    
    -- Metadata
    affiliate_code VARCHAR(100),
    
    -- Caching
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Index for polymorphic queries
    CONSTRAINT unique_linkable_provider UNIQUE (linkable_type, linkable_id, provider)
);

-- External API call logs (for debugging and rate limiting)
CREATE TABLE external_api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request info
    api_provider VARCHAR(50) NOT NULL, -- 'google_places', 'tripadvisor', 'amadeus', 'booking'
    api_endpoint VARCHAR(200) NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    request_params JSONB,
    
    -- Response info
    response_status INTEGER,
    response_body JSONB,
    error_message TEXT,
    
    -- Performance
    request_started_at TIMESTAMPTZ NOT NULL,
    request_completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Rate limiting
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for API logs
CREATE TABLE external_api_logs_2024_01 PARTITION OF external_api_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- ============================================================================
-- AI PLANNING AND BACKGROUND JOBS
-- ============================================================================

CREATE TABLE ai_planning_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    
    -- Job status
    status VARCHAR(20) DEFAULT 'queued' 
        CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Processing
    worker_id VARCHAR(100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Input/Output
    input_params JSONB NOT NULL,
    result_data JSONB,
    error_message TEXT,
    
    -- Retry logic
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMPTZ,
    
    -- Performance metrics
    processing_duration_ms INTEGER,
    tokens_used INTEGER,
    model_version VARCHAR(50),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI feedback for continuous improvement
CREATE TABLE ai_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID REFERENCES trips(id),
    itinerary_id UUID REFERENCES itineraries(id),
    
    -- Feedback type
    feedback_type VARCHAR(30) NOT NULL, -- 'rating', 'correction', 'suggestion'
    
    -- Content
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    
    -- What was being rated
    rated_item_type VARCHAR(30), -- 'itinerary', 'attraction', 'accommodation', 'flight'
    rated_item_id UUID,
    
    -- User
    user_id UUID NOT NULL REFERENCES users(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- NOTIFICATIONS AND USER ACTIVITY
-- ============================================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification content
    type VARCHAR(50) NOT NULL, -- 'trip_reminder', 'booking_confirmation', 'price_alert'
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    
    -- Deep link
    action_url TEXT,
    action_type VARCHAR(50),
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    -- Delivery
    sent_via VARCHAR(20)[], -- ['push', 'email', 'sms']
    
    -- Related entities
    related_trip_id UUID REFERENCES trips(id),
    related_entity_type VARCHAR(30),
    related_entity_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User activity log (for analytics)
CREATE TABLE user_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Activity details
    activity_type VARCHAR(50) NOT NULL, -- 'view_trip', 'book_flight', 'add_attraction'
    activity_data JSONB,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_provider_id) WHERE oauth_provider IS NOT NULL;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Sessions indexes
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at) WHERE is_revoked = FALSE;

-- Countries/Cities indexes
CREATE INDEX idx_countries_iso ON countries(iso_code);
CREATE INDEX idx_countries_location ON countries USING GIST(location);
CREATE INDEX idx_cities_country ON cities(country_id);
CREATE INDEX idx_cities_location ON cities USING GIST(location);
CREATE INDEX idx_cities_iata ON cities(iata_code) WHERE iata_code IS NOT NULL;
CREATE INDEX idx_cities_search ON cities USING GIN(search_vector);
CREATE INDEX idx_cities_name_trgm ON cities USING GIN(name gin_trgm_ops);

-- Trips indexes
CREATE INDEX idx_trips_user ON trips(user_id);
CREATE INDEX idx_trips_dates ON trips(start_date, end_date);
CREATE INDEX idx_trips_status ON trips(trip_status);
CREATE INDEX idx_trips_user_status ON trips(user_id, trip_status);
CREATE INDEX idx_trips_planning ON trips(planning_status) WHERE planning_status IN ('pending', 'in_progress');

-- Trip destinations indexes
CREATE INDEX idx_trip_destinations_trip ON trip_destinations(trip_id);
CREATE INDEX idx_trip_destinations_city ON trip_destinations(city_id) WHERE city_id IS NOT NULL;
CREATE INDEX idx_trip_destinations_order ON trip_destinations(trip_id, visit_order);

-- Categories indexes
CREATE INDEX idx_categories_parent ON categories(parent_category_id) WHERE parent_category_id IS NOT NULL;

-- Trip categories indexes
CREATE INDEX idx_trip_categories_trip ON trip_categories(trip_id);
CREATE INDEX idx_trip_categories_category ON trip_categories(category_id);

-- Itineraries indexes
CREATE INDEX idx_itineraries_trip ON itineraries(trip_id);
CREATE INDEX idx_itineraries_selected ON itineraries(trip_id) WHERE is_selected = TRUE;

-- Itinerary days indexes
CREATE INDEX idx_itinerary_days_itinerary ON itinerary_days(itinerary_id);
CREATE INDEX idx_itinerary_days_date ON itinerary_days(date);

-- Itinerary items indexes
CREATE INDEX idx_itinerary_items_day ON itinerary_items(itinerary_day_id);
CREATE INDEX idx_itinerary_items_order ON itinerary_items(itinerary_day_id, item_order);
CREATE INDEX idx_itinerary_items_type ON itinerary_items(item_type);
CREATE INDEX idx_itinerary_items_status ON itinerary_items(status);
CREATE INDEX idx_itinerary_items_attraction ON itinerary_items(attraction_id) WHERE attraction_id IS NOT NULL;
CREATE INDEX idx_itinerary_items_delayed ON itinerary_items(delayed_to_day_id) WHERE delayed_to_day_id IS NOT NULL;
CREATE INDEX idx_itinerary_items_location ON itinerary_items USING GIST(location_coordinates) WHERE location_coordinates IS NOT NULL;

-- Attractions indexes
CREATE INDEX idx_attractions_city ON attractions(city_id);
CREATE INDEX idx_attractions_country ON attractions(country_id);
CREATE INDEX idx_attractions_type ON attractions(attraction_type);
CREATE INDEX idx_attractions_location ON attractions USING GIST(location);
CREATE INDEX idx_attractions_search ON attractions USING GIN(search_vector);
CREATE INDEX idx_attractions_active ON attractions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_attractions_rating ON attractions(avg_rating) WHERE avg_rating IS NOT NULL;
CREATE INDEX idx_attractions_external_google ON attractions(google_places_id) WHERE google_places_id IS NOT NULL;
CREATE INDEX idx_attractions_external_tripadvisor ON attractions(tripadvisor_id) WHERE tripadvisor_id IS NOT NULL;

-- Flights indexes
CREATE INDEX idx_flights_trip ON flights(trip_id);
CREATE INDEX idx_flights_status ON flights(booking_status);
CREATE INDEX idx_flights_dates ON flights(departure_datetime, arrival_datetime);
CREATE INDEX idx_flights_route ON flights(departure_airport_code, arrival_airport_code);
CREATE INDEX idx_flights_external ON flights(external_flight_id) WHERE external_flight_id IS NOT NULL;

-- Flight search cache indexes
CREATE INDEX idx_flight_cache_hash ON flight_search_cache(search_hash);
CREATE INDEX idx_flight_cache_expires ON flight_search_cache(expires_at);

-- Accommodations indexes
CREATE INDEX idx_accommodations_trip ON accommodations(trip_id);
CREATE INDEX idx_accommodations_status ON accommodations(booking_status);
CREATE INDEX idx_accommodations_dates ON accommodations(check_in_date, check_out_date);
CREATE INDEX idx_accommodations_city ON accommodations(city_id);
CREATE INDEX idx_accommodations_external ON accommodations(external_property_id) WHERE external_property_id IS NOT NULL;

-- Accommodation search cache indexes
CREATE INDEX idx_accom_cache_hash ON accommodation_search_cache(search_hash);
CREATE INDEX idx_accom_cache_expires ON accommodation_search_cache(expires_at);

-- Booking links indexes
CREATE INDEX idx_booking_links_polymorphic ON booking_links(linkable_type, linkable_id);
CREATE INDEX idx_booking_links_provider ON booking_links(provider);

-- API logs indexes
CREATE INDEX idx_api_logs_provider ON external_api_logs(api_provider);
CREATE INDEX idx_api_logs_created ON external_api_logs(created_at);
CREATE INDEX idx_api_logs_endpoint ON external_api_logs(api_endpoint);

-- AI jobs indexes
CREATE INDEX idx_ai_jobs_trip ON ai_planning_jobs(trip_id);
CREATE INDEX idx_ai_jobs_status ON ai_planning_jobs(status);
CREATE INDEX idx_ai_jobs_processing ON ai_planning_jobs(status, next_retry_at) WHERE status IN ('queued', 'failed');

-- Notifications indexes
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- ============================================================================
-- FULL-TEXT SEARCH SETUP
-- ============================================================================

-- Create search vector update function for cities
CREATE OR REPLACE FUNCTION update_city_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.name_local, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.aliases, ' '), '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_city_search_vector
    BEFORE INSERT OR UPDATE ON cities
    FOR EACH ROW
    EXECUTE FUNCTION update_city_search_vector();

-- Create search vector update function for attractions
CREATE OR REPLACE FUNCTION update_attraction_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.name_local, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.short_description, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_attraction_search_vector
    BEFORE INSERT OR UPDATE ON attractions
    FOR EACH ROW
    EXECUTE FUNCTION update_attraction_search_vector();

-- ============================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_countries_updated_at BEFORE UPDATE ON countries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cities_updated_at BEFORE UPDATE ON cities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trips_updated_at BEFORE UPDATE ON trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_itineraries_updated_at BEFORE UPDATE ON itineraries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_itinerary_items_updated_at BEFORE UPDATE ON itinerary_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_attractions_updated_at BEFORE UPDATE ON attractions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_flights_updated_at BEFORE UPDATE ON flights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accommodations_updated_at BEFORE UPDATE ON accommodations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trip_preferences_updated_at BEFORE UPDATE ON trip_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ai_jobs_updated_at BEFORE UPDATE ON ai_planning_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on user-related tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_destinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE itineraries ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE accommodations ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY users_own_data ON users
    FOR ALL USING (id = current_setting('app.current_user_id')::UUID);

CREATE POLICY trips_own_data ON trips
    FOR ALL USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY trip_destinations_own_data ON trip_destinations
    FOR ALL USING (trip_id IN (SELECT id FROM trips WHERE user_id = current_setting('app.current_user_id')::UUID));

-- Shared trips (via share_token) are readable
CREATE POLICY trips_shared_read ON trips
    FOR SELECT USING (is_public = TRUE OR share_token IS NOT NULL);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Trip summary view
CREATE VIEW trip_summary AS
SELECT 
    t.id,
    t.user_id,
    t.title,
    t.trip_status,
    t.start_date,
    t.end_date,
    t.duration_days,
    t.num_travelers,
    t.budget_total_max,
    t.total_estimated_cost,
    t.total_booked_cost,
    t.cover_image_url,
    CASE 
        WHEN t.primary_destination_type = 'city' THEN c.name
        ELSE co.name
    END AS primary_destination_name,
    CASE 
        WHEN t.primary_destination_type = 'city' THEN co.name
        ELSE NULL
    END AS primary_destination_country,
    (SELECT COUNT(*) FROM itineraries i WHERE i.trip_id = t.id) AS itinerary_count,
    (SELECT COUNT(*) FROM flights f WHERE f.trip_id = t.id AND f.booking_status = 'booked') AS booked_flights,
    (SELECT COUNT(*) FROM accommodations a WHERE a.trip_id = t.id AND a.booking_status = 'booked') AS booked_accommodations
FROM trips t
LEFT JOIN cities c ON t.primary_city_id = c.id
LEFT JOIN countries co ON t.primary_country_id = co.id OR c.country_id = co.id;

-- Daily itinerary view with all items
CREATE VIEW itinerary_day_detail AS
SELECT 
    id.id AS day_id,
    id.itinerary_id,
    id.day_number,
    id.date,
    id.title AS day_title,
    id.notes AS day_notes,
    i.trip_id,
    c.name AS city_name,
    co.name AS country_name,
    json_agg(
        json_build_object(
            'item_id', ii.id,
            'order', ii.item_order,
            'start_time', ii.start_time,
            'end_time', ii.end_time,
            'duration_minutes', ii.duration_minutes,
            'type', ii.item_type,
            'title', ii.title,
            'description', ii.description,
            'status', ii.status,
            'booking_status', ii.booking_status,
            'cost_per_person', ii.cost_per_person
        ) ORDER BY ii.item_order
    ) FILTER (WHERE ii.id IS NOT NULL) AS items
FROM itinerary_days id
JOIN itineraries i ON id.itinerary_id = i.id
LEFT JOIN cities c ON id.city_id = c.id
LEFT JOIN countries co ON id.country_id = co.id
LEFT JOIN itinerary_items ii ON ii.itinerary_day_id = id.id
GROUP BY id.id, id.itinerary_id, id.day_number, id.date, id.title, id.notes, i.trip_id, c.name, co.name;

-- ============================================================================
-- SEED DATA - ESSENTIAL CATEGORIES
-- ============================================================================

INSERT INTO categories (name, display_name, description, level, sort_order) VALUES
-- Level 1: Main categories
('sightseeing', 'Sightseeing', 'Famous landmarks and must-see attractions', 1, 1),
('culture', 'Culture & History', 'Museums, historical sites, and cultural experiences', 1, 2),
('food', 'Food & Dining', 'Restaurants, food tours, and culinary experiences', 1, 3),
('nature', 'Nature & Outdoors', 'Parks, hiking, beaches, and outdoor activities', 1, 4),
('adventure', 'Adventure', 'Thrilling activities and adrenaline experiences', 1, 5),
('nightlife', 'Nightlife', 'Bars, clubs, and evening entertainment', 1, 6),
('shopping', 'Shopping', 'Markets, malls, and shopping districts', 1, 7),
('relaxation', 'Relaxation', 'Spas, wellness, and peaceful experiences', 1, 8),
('family', 'Family Friendly', 'Activities suitable for families with children', 1, 9),
('local_experience', 'Local Experiences', 'Authentic local activities and off-the-beaten-path', 1, 10);

-- Level 2: Sub-categories
INSERT INTO categories (name, display_name, description, parent_category_id, level, sort_order)
SELECT 
    sub.name, sub.display_name, sub.description, c.id, 2, sub.sort_order
FROM categories c
CROSS JOIN LATERAL (VALUES
    ('monuments', 'Monuments & Landmarks', 'Iconic structures and monuments', 1),
    ('architecture', 'Architecture', 'Notable buildings and architectural sites', 2),
    ('local_food', 'Local Cuisine', 'Traditional and local dishes', 3),
    ('fine_dining', 'Fine Dining', 'High-end restaurants', 4),
    ('street_food', 'Street Food', 'Street food and food stalls', 5),
    ('hiking', 'Hiking & Trekking', 'Walking and hiking trails', 6),
    ('beaches', 'Beaches', 'Beaches and coastal areas', 7),
    ('wildlife', 'Wildlife', 'Animal encounters and wildlife viewing', 8)
) AS sub(name, display_name, description, sort_order)
WHERE c.name = 'sightseeing';

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Core user accounts with OAuth support';
COMMENT ON TABLE trips IS 'Main trip entity containing destination and date information';
COMMENT ON TABLE itineraries IS 'AI-generated or manual trip plans';
COMMENT ON TABLE itinerary_items IS 'Individual activities/attractions within a day';
COMMENT ON TABLE attractions IS 'Points of interest with external API integration';
COMMENT ON TABLE flights IS 'Flight options and bookings';
COMMENT ON TABLE accommodations IS 'Hotel and lodging options and bookings';
COMMENT ON TABLE flight_search_cache IS 'Cached flight search results for performance';
COMMENT ON TABLE accommodation_search_cache IS 'Cached accommodation search results';
COMMENT ON TABLE ai_planning_jobs IS 'Background jobs for AI trip generation';
