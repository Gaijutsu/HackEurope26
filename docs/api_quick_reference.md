# API Quick Reference Guide
## Agentic Trip Planning Software

---

## Base URL
```
Production:  https://api.tripplanner.com/v1
Staging:     https://staging-api.tripplanner.com/v1
Local:       http://localhost:8080/v1
```

---

## Authentication

All endpoints (except auth endpoints) require a Bearer token:
```
Authorization: Bearer <jwt_token>
```

### Get Token
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

---

## Endpoint Summary

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Create new account | No |
| POST | `/auth/login` | User login | No |
| POST | `/auth/refresh` | Refresh access token | No |
| POST | `/auth/logout` | Logout user | Yes |
| POST | `/auth/forgot-password` | Request password reset | No |
| POST | `/auth/reset-password` | Reset password | No |
| GET | `/auth/oauth/{provider}` | OAuth login (google, facebook, apple) | No |

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current user profile |
| PUT | `/users/me` | Update user profile |
| GET | `/users/me/preferences` | Get user preferences |
| PUT | `/users/me/preferences` | Update user preferences |
| PUT | `/users/me/password` | Change password |
| DELETE | `/users/me/account` | Delete account |

### Trip Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trips` | List user's trips |
| POST | `/trips` | Create new trip |
| GET | `/trips/{tripId}` | Get trip details |
| PUT | `/trips/{tripId}` | Update trip |
| DELETE | `/trips/{tripId}` | Delete trip |
| POST | `/trips/{tripId}/duplicate` | Duplicate trip |

### Planning Workflow Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/trips/{tripId}/planning` | Start AI planning |
| GET | `/trips/{tripId}/planning` | Get planning status |
| POST | `/trips/{tripId}/planning/cancel` | Cancel planning |
| POST | `/trips/{tripId}/planning/regenerate` | Regenerate plan |

### City Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trips/{tripId}/cities` | Get trip cities |
| POST | `/trips/{tripId}/cities` | Add city to trip |
| PUT | `/trips/{tripId}/cities/{cityId}` | Update city |
| DELETE | `/trips/{tripId}/cities/{cityId}` | Remove city |
| PUT | `/trips/{tripId}/cities/reorder` | Reorder cities |

### Flight Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trips/{tripId}/flights` | Get trip flights |
| POST | `/trips/{tripId}/flights` | Add flight |
| GET | `/trips/{tripId}/flights/{flightId}` | Get flight details |
| PUT | `/trips/{tripId}/flights/{flightId}` | Update flight |
| DELETE | `/trips/{tripId}/flights/{flightId}` | Remove flight |
| POST | `/trips/{tripId}/flights/{flightId}/select` | Select flight |
| POST | `/trips/{tripId}/flights/{flightId}/book` | Mark as booked |

### Accommodation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trips/{tripId}/accommodations` | Get accommodations |
| POST | `/trips/{tripId}/accommodations` | Add accommodation |
| GET | `/trips/{tripId}/accommodations/{id}` | Get accommodation details |
| PUT | `/trips/{tripId}/accommodations/{id}` | Update accommodation |
| DELETE | `/trips/{tripId}/accommodations/{id}` | Remove accommodation |
| POST | `/trips/{tripId}/accommodations/{id}/select` | Select accommodation |
| POST | `/trips/{tripId}/accommodations/{id}/book` | Mark as booked |

### Itinerary Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trips/{tripId}/itinerary` | Get full itinerary |
| PUT | `/trips/{tripId}/itinerary` | Update full itinerary |
| GET | `/trips/{tripId}/itinerary/days/{date}` | Get day itinerary |
| PUT | `/trips/{tripId}/itinerary/days/{date}` | Update day itinerary |
| POST | `/trips/{tripId}/itinerary/items` | Add itinerary item |
| PUT | `/trips/{tripId}/itinerary/items/{itemId}` | Update item |
| DELETE | `/trips/{tripId}/itinerary/items/{itemId}` | Remove item |
| POST | `/trips/{tripId}/itinerary/items/{itemId}/delay` | Delay item to another day |
| POST | `/trips/{tripId}/itinerary/items/{itemId}/complete` | Mark item complete |
| PUT | `/trips/{tripId}/itinerary/reorder` | Reorder items |
| POST | `/trips/{tripId}/itinerary/optimize` | AI optimize itinerary |

### Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search/flights` | Search flights |
| POST | `/search/flights` | Advanced flight search |
| GET | `/search/hotels` | Search hotels |
| POST | `/search/hotels` | Advanced hotel search |
| GET | `/search/attractions` | Search attractions |
| POST | `/search/attractions` | Advanced attraction search |
| GET | `/search/autocomplete` | Location autocomplete |

### Pinterest Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users/me/pinterest/connect` | Connect Pinterest account |
| GET | `/users/me/pinterest/boards` | Get Pinterest boards |
| GET | `/users/me/pinterest/interests` | Extract interests from pins |
| POST | `/trips/{tripId}/pinterest/import` | Import pins as trip ideas |

### Notification Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications` | Get notifications |
| POST | `/notifications/{id}/read` | Mark notification as read |
| POST | `/notifications/read-all` | Mark all as read |

### Real-time Endpoints

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WebSocket | `wss://api.tripplanner.com/v1/ws/connect` | Real-time updates |
| SSE | `https://api.tripplanner.com/v1/sse/subscribe` | Server-sent events |

---

## Common Request/Response Examples

### Create Trip
```http
POST /trips
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Japan Adventure 2024",
  "description": "Two-week exploration of Japan",
  "destination": {
    "type": "country",
    "name": "Japan",
    "code": "JP"
  },
  "dates": {
    "startDate": "2024-04-01",
    "endDate": "2024-04-15",
    "isFlexible": false
  },
  "travelers": 2,
  "budget": {
    "total": 5000,
    "currency": "USD"
  },
  "preferences": {
    "dietaryRestrictions": ["vegetarian"],
    "interestCategories": ["culture", "food", "history"]
  }
}
```

**Response:**
```json
{
  "id": "trp_87654321-4321-4321-4321-cba987654321",
  "name": "Japan Adventure 2024",
  "status": "draft",
  "destination": {
    "type": "country",
    "name": "Japan",
    "code": "JP"
  },
  "dates": {
    "startDate": "2024-04-01",
    "endDate": "2024-04-15",
    "durationDays": 15
  },
  "createdAt": "2024-01-15T10:30:00Z"
}
```

### Start Planning
```http
POST /trips/trp_xxx/planning
Authorization: Bearer <token>
Content-Type: application/json

{
  "options": {
    "includeFlights": true,
    "includeAccommodation": true,
    "includeActivities": true,
    "optimizeFor": "balanced",
    "priorityCategories": ["culture", "food"]
  }
}
```

**Response:**
```json
{
  "planningId": "pln_abc123",
  "status": "started",
  "message": "Trip planning initiated. Connect to WebSocket for real-time updates."
}
```

### Search Flights
```http
GET /search/flights?origin=JFK&destination=NRT&departureDate=2024-04-01&returnDate=2024-04-15&adults=2&cabinClass=economy
Authorization: Bearer <token>
```

**Response:**
```json
{
  "searchId": "sch_flt_001",
  "results": [
    {
      "id": "flt_123",
      "type": "outbound",
      "segments": [
        {
          "flightNumber": "JL005",
          "airline": {
            "code": "JL",
            "name": "Japan Airlines"
          },
          "departure": {
            "airport": { "code": "JFK", "name": "John F. Kennedy" },
            "datetime": "2024-04-01T10:00:00-05:00"
          },
          "arrival": {
            "airport": { "code": "NRT", "name": "Narita" },
            "datetime": "2024-04-02T14:30:00+09:00"
          },
          "duration": "PT14H30M",
          "cabinClass": "economy"
        }
      ],
      "price": {
        "amount": 899,
        "currency": "USD"
      },
      "status": "suggested"
    }
  ]
}
```

### Delay Itinerary Item
```http
POST /trips/trp_xxx/itinerary/items/itm_yyy/delay
Authorization: Bearer <token>
Content-Type: application/json

{
  "targetDate": "2024-04-03",
  "targetTime": "14:00"
}
```

**Response:**
```json
{
  "originalItem": {
    "id": "itm_yyy",
    "date": "2024-04-01",
    "title": "Tokyo National Museum"
  },
  "newItem": {
    "id": "itm_yyy",
    "date": "2024-04-03",
    "startTime": "14:00",
    "title": "Tokyo National Museum"
  },
  "affectedItems": [
    {
      "itemId": "itm_zzz",
      "change": "time_shifted",
      "newStartTime": "10:30"
    }
  ]
}
```

---

## Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "dates.startDate",
        "message": "Start date must be in the future"
      }
    ]
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Pagination

List endpoints support pagination:

```http
GET /trips?page=2&limit=20
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 150,
    "totalPages": 8,
    "hasNext": true,
    "hasPrev": true
  }
}
```

---

## WebSocket Message Examples

### Subscribe to Trip
```json
{
  "type": "subscribe",
  "subscriptions": [
    {
      "channel": "trip",
      "tripId": "trp_xxx",
      "events": ["planning", "itinerary"]
    }
  ],
  "requestId": "req_001"
}
```

### Planning Progress Update
```json
{
  "type": "planning_update",
  "event": "planning_progress",
  "tripId": "trp_xxx",
  "data": {
    "stage": "finding_flights",
    "progress": 45,
    "message": "Searching for flights from JFK to NRT..."
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## External API Integrations

| Service | Provider | Primary Use |
|---------|----------|-------------|
| Flight Search | Amadeus | Flight offers, pricing |
| Hotel Search | Booking.com | Hotel listings, availability |
| Attractions | Google Places | Points of interest, reviews |
| Interest Extraction | Pinterest | User preference analysis |

---

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 10 requests/minute |
| General API | 100 requests/minute |
| Search | 30 requests/minute |
| WebSocket | 100 messages/minute |

---

## Data Models Summary

### Trip Status Flow
```
draft → planning → planned → active → completed
   ↓
cancelled
```

### Planning Stages
```
not_started → analyzing → generating_itinerary → 
finding_flights → finding_hotels → finding_activities → completed
```

### Booking Status
```
suggested → selected → reserved → booked → cancelled
```

### Itinerary Item Status
```
planned → completed/skipped/delayed
```
