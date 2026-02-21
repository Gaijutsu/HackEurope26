# External API Integration Patterns
## Agentic Trip Planning Software

---

## Table of Contents
1. [Overview](#overview)
2. [Flight Search APIs](#flight-search-apis)
3. [Hotel Booking APIs](#hotel-booking-apis)
4. [Attraction/Activity APIs](#attractionactivity-apis)
5. [Pinterest Integration](#pinterest-integration)
6. [Common Patterns](#common-patterns)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Overview

This document outlines the integration patterns for external APIs used in the Agentic Trip Planning Software. All integrations follow a consistent pattern:

1. **Client Request** → Backend API
2. **Backend** → External API (with caching)
3. **Response Normalization** → Standard schema
4. **Enrichment** → Additional data from secondary sources
5. **Client Response** → Unified format

### Architecture Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│  Backend API │────▶│  Cache Layer    │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │                       │
                           ▼                       ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  External    │◀────│  Cache Check    │
                    │    APIs      │     │                 │
                    └──────────────┘     └─────────────────┘
```

---

## Flight Search APIs

### Primary Provider: Amadeus API
**Documentation:** https://developers.amadeus.com/

#### Configuration
```yaml
amadeus:
  base_url: "https://api.amadeus.com/v2"
  auth:
    type: "oauth2_client_credentials"
    token_url: "https://api.amadeus.com/v1/security/oauth2/token"
    client_id: "${AMADEUS_CLIENT_ID}"
    client_secret: "${AMADEUS_CLIENT_SECRET}"
  rate_limits:
    requests_per_minute: 100
    requests_per_day: 10000
  timeout: 30s
  retry:
    max_attempts: 3
    backoff: exponential
```

#### API Endpoints Used

##### 1. Flight Offers Search
```
GET /v2/shopping/flight-offers
```

**Request Parameters:**
```json
{
  "originLocationCode": "JFK",
  "destinationLocationCode": "NRT",
  "departureDate": "2024-04-01",
  "returnDate": "2024-04-15",
  "adults": 2,
  "children": 0,
  "infants": 0,
  "travelClass": "ECONOMY",
  "maxPrice": 2000,
  "max": 50
}
```

**Response Mapping to Internal Schema:**
```javascript
// Amadeus Response → Internal Flight Schema
{
  id: generateUUID(),
  type: determineFlightType(offer),
  segments: offer.itineraries.map(itinerary => ({
    flightNumber: itinerary.segments[0].number,
    airline: {
      code: itinerary.segments[0].carrierCode,
      name: getAirlineName(itinerary.segments[0].carrierCode),
      logo: getAirlineLogo(itinerary.segments[0].carrierCode)
    },
    departure: {
      airport: {
        code: itinerary.segments[0].departure.iataCode,
        ...getAirportDetails(itinerary.segments[0].departure.iataCode)
      },
      datetime: itinerary.segments[0].departure.at,
      terminal: itinerary.segments[0].departure.terminal
    },
    arrival: {
      airport: {
        code: itinerary.segments[0].arrival.iataCode,
        ...getAirportDetails(itinerary.segments[0].arrival.iataCode)
      },
      datetime: itinerary.segments[0].arrival.at,
      terminal: itinerary.segments[0].arrival.terminal
    },
    duration: itinerary.segments[0].duration,
    aircraft: itinerary.segments[0].aircraft.code,
    cabinClass: mapCabinClass(offer.travelerPricings[0].fareDetailsBySegment[0].cabin),
    baggage: extractBaggageInfo(offer)
  })),
  price: {
    amount: parseFloat(offer.price.total),
    currency: offer.price.currency,
    breakdown: {
      base: parseFloat(offer.price.base),
      taxes: parseFloat(offer.price.totalTaxes || 0),
      fees: parseFloat(offer.price.fees?.reduce((sum, f) => sum + parseFloat(f.amount), 0) || 0)
    }
  },
  bookingDetails: {
    provider: "amadeus",
    bookingUrl: generateDeepLink(offer)
  },
  status: "suggested"
}
```

##### 2. Flight Price Analysis (for price tracking)
```
GET /v1/analytics/itinerary-price-metrics
```

#### Caching Strategy
```yaml
flight_search:
  key_pattern: "flight:search:{origin}:{destination}:{departure}:{adults}:{cabin}"
  ttl: 900  # 15 minutes
  
flight_details:
  key_pattern: "flight:details:{flight_number}:{date}"
  ttl: 3600  # 1 hour
  
airport_info:
  key_pattern: "airport:{iata_code}"
  ttl: 86400  # 24 hours
  
airline_info:
  key_pattern: "airline:{iata_code}"
  ttl: 86400  # 24 hours (rarely changes)
```

#### Fallback Strategy
```javascript
const flightProviders = [
  { name: 'amadeus', priority: 1 },
  { name: 'skyscanner', priority: 2 },
  { name: 'kayak', priority: 3 }
];

async function searchFlightsWithFallback(params) {
  for (const provider of flightProviders.sort((a, b) => a.priority - b.priority)) {
    try {
      const results = await searchWithProvider(provider.name, params);
      if (results && results.length > 0) {
        return results;
      }
    } catch (error) {
      logger.warn(`Flight search failed for ${provider.name}:`, error);
      continue;
    }
  }
  throw new Error('All flight search providers failed');
}
```

---

### Secondary Provider: Skyscanner API
**Documentation:** https://partners.skyscanner.net/

#### Configuration
```yaml
skyscanner:
  base_url: "https://partners.api.skyscanner.net/apiservices"
  auth:
    type: "api_key"
    header: "x-api-key"
  rate_limits:
    requests_per_minute: 50
```

---

## Hotel Booking APIs

### Primary Provider: Booking.com Affiliate API
**Documentation:** https://affiliate.booking.com/

#### Configuration
```yaml
booking_com:
  base_url: "https://distribution-xml.booking.com/json/bookings"
  auth:
    type: "basic_auth"
    username: "${BOOKING_COM_USERNAME}"
    password: "${BOOKING_COM_PASSWORD}"
  rate_limits:
    requests_per_minute: 200
  timeout: 30s
```

#### API Endpoints Used

##### 1. Hotel Search
```
GET /getHotels
```

**Request Parameters:**
```json
{
  "city_ids": "-246227",
  "checkin": "2024-04-01",
  "checkout": "2024-04-05",
  "room1": "A,A",  // 2 adults
  "rows": 50,
  "min_review_score": 7,
  "output": "hotel_details,room_details"
}
```

**Response Mapping:**
```javascript
// Booking.com Response → Internal Accommodation Schema
{
  id: generateUUID(),
  name: hotel.hotel_name,
  type: mapHotelType(hotel.accommodation_type),
  description: hotel.hotel_description,
  address: {
    street: hotel.address,
    city: hotel.city,
    postalCode: hotel.zip,
    country: hotel.country
  },
  coordinates: {
    latitude: parseFloat(hotel.latitude),
    longitude: parseFloat(hotel.longitude)
  },
  rating: parseFloat(hotel.review_score) / 2,  // Convert to 5-star scale
  reviewCount: hotel.review_nr,
  images: hotel.photos?.map(p => p.url_original) || [],
  amenities: hotel.facilities?.map(f => f.name) || [],
  rooms: hotel.rooms?.map(room => ({
    id: room.room_id,
    type: room.name,
    description: room.description,
    maxOccupancy: room.max_occupancy,
    bedType: room.bed_type,
    size: room.room_surface_in_m2 ? `${room.room_surface_in_m2} sqm` : null,
    amenities: room.facilities?.map(f => f.name) || [],
    pricePerNight: {
      amount: parseFloat(room.min_rate.extracted_value),
      currency: room.min_rate.currency
    }
  })),
  price: {
    amount: calculateTotalPrice(hotel),
    currency: hotel.currency_code
  },
  bookingDetails: {
    provider: "booking.com",
    providerLogo: "https://cdn.tripplanner.com/logos/booking.com.png",
    bookingUrl: generateAffiliateLink(hotel)
  },
  policies: {
    checkInTime: hotel.checkin_from,
    checkOutTime: hotel.checkout_until,
    cancellationPolicy: hotel.cancellation_policy
  }
}
```

##### 2. Hotel Availability
```
GET /getHotelAvailability
```

#### Caching Strategy
```yaml
hotel_search:
  key_pattern: "hotel:search:{city}:{checkin}:{checkout}:{adults}"
  ttl: 3600  # 1 hour
  
hotel_details:
  key_pattern: "hotel:details:{hotel_id}"
  ttl: 86400  # 24 hours
  
hotel_availability:
  key_pattern: "hotel:avail:{hotel_id}:{checkin}:{checkout}"
  ttl: 600  # 10 minutes (prices change frequently)
```

### Secondary Provider: Airbnb API
**Note:** Airbnb API requires partnership agreement

#### Configuration
```yaml
airbnb:
  base_url: "https://api.airbnb.com/v2"
  auth:
    type: "oauth2"
  rate_limits:
    requests_per_minute: 30
```

---

## Attraction/Activity APIs

### Primary Provider: Google Places API
**Documentation:** https://developers.google.com/maps/documentation/places/web-service

#### Configuration
```yaml
google_places:
  base_url: "https://maps.googleapis.com/maps/api/place"
  auth:
    type: "api_key"
    key: "${GOOGLE_PLACES_API_KEY}"
  rate_limits:
    requests_per_day: 100000  # Depends on plan
  timeout: 10s
```

#### API Endpoints Used

##### 1. Nearby Search
```
GET /nearbysearch/json
```

**Request Parameters:**
```json
{
  "location": "35.6762,139.6503",  // Tokyo coordinates
  "radius": 5000,  // 5km radius
  "type": "tourist_attraction",
  "keyword": "museum",
  "key": "YOUR_API_KEY"
}
```

**Response Mapping:**
```javascript
// Google Places Response → Internal Attraction Schema
{
  id: place.place_id,
  name: place.name,
  description: place.vicinity,  // Short address
  category: mapPlaceType(place.types),
  location: {
    name: place.name,
    address: place.vicinity,
    coordinates: {
      latitude: place.geometry.location.lat,
      longitude: place.geometry.location.lng
    },
    placeId: place.place_id
  },
  rating: place.rating,
  reviewCount: place.user_ratings_total,
  images: [],  // Populated by separate Photos API call
  openingHours: place.opening_hours?.weekday_text,
  ticketInfo: {
    price: null,  // Google doesn't provide pricing
    freeEntry: place.price_level === 0,
    bookingRequired: false
  }
}
```

##### 2. Place Details
```
GET /details/json
```

##### 3. Place Photos
```
GET /photo
```

#### Caching Strategy
```yaml
place_search:
  key_pattern: "places:search:{lat}:{lng}:{radius}:{type}"
  ttl: 86400  # 24 hours
  
place_details:
  key_pattern: "places:details:{place_id}"
  ttl: 604800  # 7 days
  
place_photos:
  key_pattern: "places:photo:{photo_reference}"
  ttl: 2592000  # 30 days
```

### Secondary Provider: TripAdvisor API
**Documentation:** https://www.tripadvisor.com/developers

#### Configuration
```yaml
tripadvisor:
  base_url: "https://api.content.tripadvisor.com/api/v1"
  auth:
    type: "api_key"
    key: "${TRIPADVISOR_API_KEY}"
```

### Activity Booking Provider: GetYourGuide
**Documentation:** https://partner.getyourguide.com/

---

## Pinterest Integration

### API: Pinterest API v5
**Documentation:** https://developers.pinterest.com/docs/api/v5/

#### OAuth Flow
```
1. User clicks "Connect Pinterest" in app
2. Redirect to: https://www.pinterest.com/oauth/?client_id=APP_ID&redirect_uri=CALLBACK&scope=boards:read,pins:read
3. User authorizes app
4. Pinterest redirects to callback with authorization code
5. Exchange code for access token
6. Store token securely for user
```

#### Configuration
```yaml
pinterest:
  auth_url: "https://www.pinterest.com/oauth/"
  token_url: "https://api.pinterest.com/v5/oauth/token"
  api_url: "https://api.pinterest.com/v5"
  scopes:
    - boards:read
    - pins:read
    - user_accounts:read
```

#### API Endpoints Used

##### 1. Get User Boards
```
GET /v5/boards
```

##### 2. Get Board Pins
```
GET /v5/boards/{board_id}/pins
```

##### 3. Get Pin Details
```
GET /v5/pins/{pin_id}
```

#### Interest Extraction Pipeline
```javascript
async function extractInterestsFromPinterest(accessToken, boardIds = null) {
  // 1. Get user's boards
  const boards = boardIds 
    ? await getSpecificBoards(accessToken, boardIds)
    : await getAllBoards(accessToken);
  
  // 2. Fetch pins from boards
  const pins = await Promise.all(
    boards.map(board => getBoardPins(accessToken, board.id))
  );
  
  // 3. Analyze images using ML service
  const analyzedPins = await Promise.all(
    pins.flat().map(pin => analyzePinImage(pin))
  );
  
  // 4. Extract categories and interests
  const categories = aggregateCategories(analyzedPins);
  
  // 5. Map to travel categories
  const travelInterests = mapToTravelCategories(categories);
  
  return {
    categories: travelInterests,
    confidence: calculateConfidence(travelInterests),
    sampleImages: getSampleImages(analyzedPins, 5)
  };
}

async function analyzePinImage(pin) {
  // Use image recognition service (e.g., Google Vision, AWS Rekognition)
  const labels = await imageRecognitionService.labelDetection(pin.media.images.original.url);
  
  return {
    pinId: pin.id,
    labels: labels.map(l => ({
      name: l.description,
      confidence: l.score
    })),
    dominantColors: pin.dominant_color,
    board: pin.board_id
  };
}
```

#### Category Mapping
```javascript
const categoryMapping = {
  // Pinterest/ML categories → Travel categories
  'beach': ['nature', 'relaxation'],
  'mountain': ['adventure', 'nature'],
  'museum': ['culture', 'history'],
  'restaurant': ['food'],
  'temple': ['culture', 'history'],
  'hiking': ['adventure', 'nature'],
  'shopping': ['shopping'],
  'spa': ['wellness'],
  'nightlife': ['nightlife'],
  'architecture': ['culture', 'history'],
  'art gallery': ['art', 'culture'],
  'street food': ['food'],
  'luxury hotel': ['luxury'],
  'backpacking': ['adventure'],
  'wildlife': ['nature', 'adventure']
};
```

---

## Common Patterns

### Circuit Breaker Pattern
```javascript
class CircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 60000;
    this.state = 'CLOSED';  // CLOSED, OPEN, HALF_OPEN
    this.failureCount = 0;
    this.lastFailureTime = null;
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.resetTimeout) {
        this.state = 'HALF_OPEN';
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
    }
  }
}

// Usage
const amadeusCircuitBreaker = new CircuitBreaker({
  failureThreshold: 5,
  resetTimeout: 60000
});

async function searchFlights(params) {
  return amadeusCircuitBreaker.execute(async () => {
    return await amadeusClient.searchFlights(params);
  });
}
```

### Request Deduplication
```javascript
class RequestDeduplicator {
  constructor() {
    this.pendingRequests = new Map();
  }

  async execute(key, fn) {
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key);
    }

    const promise = fn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }
}

// Usage for flight search
deduplicator.execute(
  `flight:${origin}:${destination}:${date}`,
  () => amadeusClient.searchFlights(params)
);
```

### Response Caching with Stale-While-Revalidate
```javascript
async function getCachedOrFetch(key, fetchFn, options = {}) {
  const { ttl = 3600, staleTtl = 86400 } = options;
  
  // Try to get from cache
  const cached = await cache.get(key);
  
  if (cached) {
    const age = Date.now() - cached.timestamp;
    
    // If fresh, return immediately
    if (age < ttl * 1000) {
      return cached.data;
    }
    
    // If stale but not expired, return and refresh in background
    if (age < staleTtl * 1000) {
      // Trigger background refresh
      fetchAndCache(key, fetchFn, options).catch(console.error);
      return cached.data;
    }
  }
  
  // Cache miss or expired, fetch fresh data
  return fetchAndCache(key, fetchFn, options);
}
```

---

## Error Handling

### Standardized Error Response
```javascript
class ExternalAPIError extends Error {
  constructor(provider, originalError, context = {}) {
    super(`External API Error: ${provider}`);
    this.provider = provider;
    this.originalError = originalError;
    this.context = context;
    this.timestamp = new Date().toISOString();
  }

  toJSON() {
    return {
      error: {
        code: 'EXTERNAL_API_ERROR',
        message: `Failed to fetch data from ${this.provider}`,
        provider: this.provider,
        timestamp: this.timestamp,
        userMessage: 'We\'re having trouble connecting to our travel partners. Please try again in a moment.'
      }
    };
  }
}

// Error classification
function classifyError(error, provider) {
  if (error.code === 'ECONNRESET' || error.code === 'ETIMEDOUT') {
    return { type: 'NETWORK', retryable: true };
  }
  
  if (error.response?.status === 429) {
    return { type: 'RATE_LIMIT', retryable: true, retryAfter: error.response.headers['retry-after'] };
  }
  
  if (error.response?.status >= 500) {
    return { type: 'SERVER_ERROR', retryable: true };
  }
  
  if (error.response?.status === 401 || error.response?.status === 403) {
    return { type: 'AUTH', retryable: false };
  }
  
  if (error.response?.status === 404) {
    return { type: 'NOT_FOUND', retryable: false };
  }
  
  return { type: 'UNKNOWN', retryable: false };
}
```

---

## Rate Limiting

### Token Bucket Implementation
```javascript
class TokenBucket {
  constructor(capacity, refillRate) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = refillRate;  // tokens per second
    this.lastRefill = Date.now();
  }

  async consume(tokens = 1) {
    this.refill();
    
    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }
    
    // Wait for tokens to be available
    const waitTime = Math.ceil((tokens - this.tokens) / this.refillRate * 1000);
    await sleep(waitTime);
    return this.consume(tokens);
  }

  refill() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsed * this.refillRate);
    this.lastRefill = now;
  }
}

// Per-provider rate limiters
const rateLimiters = {
  amadeus: new TokenBucket(100, 100/60),  // 100 per minute
  booking: new TokenBucket(200, 200/60),   // 200 per minute
  google_places: new TokenBucket(100, 100/86400)  // 100 per day
};
```

### Queue-Based Rate Limiting
```javascript
class RateLimitedQueue {
  constructor(rateLimit, interval = 60000) {
    this.queue = [];
    this.processing = false;
    this.rateLimit = rateLimit;
    this.interval = interval;
    this.requests = [];
  }

  async enqueue(fn) {
    return new Promise((resolve, reject) => {
      this.queue.push({ fn, resolve, reject });
      this.process();
    });
  }

  async process() {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;
    
    // Clean old requests outside the interval
    const cutoff = Date.now() - this.interval;
    this.requests = this.requests.filter(r => r > cutoff);
    
    // Check rate limit
    if (this.requests.length >= this.rateLimit) {
      const waitTime = this.requests[0] + this.interval - Date.now();
      await sleep(waitTime);
    }
    
    const { fn, resolve, reject } = this.queue.shift();
    
    try {
      this.requests.push(Date.now());
      const result = await fn();
      resolve(result);
    } catch (error) {
      reject(error);
    } finally {
      this.processing = false;
      this.process();
    }
  }
}
```

---

## Monitoring & Observability

### Metrics to Track
```yaml
metrics:
  external_api:
    - request_count (by provider, endpoint)
    - request_duration (by provider, endpoint)
    - error_count (by provider, error_type)
    - cache_hit_rate (by provider)
    - rate_limit_hits (by provider)
    - circuit_breaker_state (by provider)
```

### Logging Format
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "component": "external_api",
  "provider": "amadeus",
  "operation": "flight_search",
  "request_id": "req_123",
  "duration_ms": 245,
  "cache_hit": false,
  "result_count": 25,
  "status": "success"
}
```
