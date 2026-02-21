# WebSocket & Server-Sent Events (SSE) Specification
## Agentic Trip Planning Software

---

## Table of Contents
1. [Overview](#overview)
2. [WebSocket Specification](#websocket-specification)
3. [SSE Specification](#sse-specification)
4. [Message Types](#message-types)
5. [Connection Management](#connection-management)
6. [Security](#security)
7. [Error Handling](#error-handling)
8. [Implementation Examples](#implementation-examples)

---

## Overview

Real-time communication is essential for the Agentic Trip Planning Software to provide:
- Live updates during AI trip planning
- Price change notifications
- Collaborative trip editing
- Progress tracking for long-running operations

### Communication Patterns

| Feature | Protocol | Use Case |
|---------|----------|----------|
| Planning Progress | WebSocket | Bidirectional updates during planning |
| Notifications | Both | Price alerts, booking confirmations |
| Live Collaboration | WebSocket | Multiple users editing same trip |
| Simple Updates | SSE | One-way server-to-client updates |

---

## WebSocket Specification

### Connection Endpoint
```
wss://api.tripplanner.com/v1/ws/connect
```

### Connection Flow

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│ Client  │                    │  Load   │                    │  WS     │
│         │                    │ Balancer│                    │ Server  │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │  1. Authenticate (REST)      │                              │
     │─────────────────────────────▶│                              │
     │                              │                              │
     │  2. Receive JWT Token        │                              │
     │◀─────────────────────────────│                              │
     │                              │                              │
     │  3. WS Connect + Bearer      │                              │
     │─────────────────────────────▶│─────────────────────────────▶│
     │                              │                              │
     │  4. Connection Ack           │                              │
     │◀─────────────────────────────│◀─────────────────────────────│
     │                              │                              │
     │  5. Subscribe to Trip        │                              │
     │─────────────────────────────▶│─────────────────────────────▶│
     │                              │                              │
     │  6. Real-time Updates        │                              │
     │◀═════════════════════════════│◀═════════════════════════════│
```

### Connection Request

**Headers:**
```
Authorization: Bearer <jwt_token>
X-Client-Version: 1.0.0
```

**Query Parameters:**
```
?token=<jwt_token>&client_id=<client_id>
```

### Connection Response (Server → Client)

```json
{
  "type": "connection_ack",
  "connectionId": "conn_abc123def456",
  "serverTime": "2024-01-15T10:30:00.000Z",
  "heartbeatInterval": 30000,
  "supportedProtocols": ["json"],
  "userId": "usr_12345678-1234-1234-1234-123456789abc"
}
```

### Heartbeat Mechanism

**Client → Server (Ping):**
```json
{
  "type": "ping",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Server → Client (Pong):**
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00.050Z",
  "latency_ms": 50
}
```

**Rules:**
- Client must send ping every 30 seconds
- Server responds with pong within 5 seconds
- If no pong received, client should reconnect
- Server disconnects client after 60 seconds of inactivity

### Subscription Management

#### Subscribe to Trip Updates

**Client → Server:**
```json
{
  "type": "subscribe",
  "subscriptions": [
    {
      "channel": "trip",
      "tripId": "trp_87654321-4321-4321-4321-cba987654321",
      "events": ["planning", "itinerary", "flight", "accommodation"]
    }
  ],
  "requestId": "req_sub_001"
}
```

**Server → Client (Ack):**
```json
{
  "type": "subscription_ack",
  "requestId": "req_sub_001",
  "subscriptions": [
    {
      "channel": "trip",
      "tripId": "trp_87654321-4321-4321-4321-cba987654321",
      "status": "subscribed",
      "subscribedAt": "2024-01-15T10:30:01.000Z"
    }
  ]
}
```

#### Unsubscribe from Trip Updates

**Client → Server:**
```json
{
  "type": "unsubscribe",
  "subscriptions": [
    {
      "channel": "trip",
      "tripId": "trp_87654321-4321-4321-4321-cba987654321"
    }
  ],
  "requestId": "req_unsub_001"
}
```

#### Subscribe to Notifications

**Client → Server:**
```json
{
  "type": "subscribe",
  "subscriptions": [
    {
      "channel": "notifications",
      "filter": {
        "severity": ["info", "warning", "error"],
        "categories": ["price_alert", "booking", "planning"]
      }
    }
  ],
  "requestId": "req_sub_002"
}
```

---

## SSE Specification

### Connection Endpoint
```
https://api.tripplanner.com/v1/sse/subscribe
```

### Connection Flow

```javascript
// Client-side JavaScript
const eventSource = new EventSource(
  'https://api.tripplanner.com/v1/sse/subscribe?token=<jwt_token>'
);

eventSource.onopen = () => {
  console.log('SSE connection established');
};

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleEvent(data);
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Auto-reconnect is handled by browser
};

// Event listeners for specific event types
eventSource.addEventListener('planning_update', (event) => {
  const data = JSON.parse(event.data);
  updatePlanningProgress(data);
});

eventSource.addEventListener('notification', (event) => {
  const data = JSON.parse(event.data);
  showNotification(data);
});
```

### SSE Event Format

```
event: planning_update
id: msg_001
data: {"tripId": "trp_xxx", "stage": "generating_itinerary", "progress": 65}
retry: 5000

event: notification
id: msg_002
data: {"id": "not_xxx", "title": "Price Drop!", "message": "Flight price dropped by $50"}
retry: 5000
```

### SSE vs WebSocket Decision Matrix

| Scenario | Recommended Protocol | Reason |
|----------|---------------------|--------|
| Planning Progress | WebSocket | Bidirectional control |
| Price Alerts | SSE | Simple, one-way updates |
| Collaborative Editing | WebSocket | Real-time sync needed |
| System Notifications | SSE | Fire-and-forget |
| Trip Sharing | WebSocket | Presence awareness |

---

## Message Types

### 1. Planning Update Messages

#### Planning Started
```json
{
  "type": "planning_update",
  "event": "planning_started",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "planningId": "pln_abc123",
    "startedAt": "2024-01-15T10:30:00Z",
    "estimatedDuration": 120,
    "stages": [
      "analyzing",
      "generating_itinerary",
      "finding_flights",
      "finding_hotels",
      "finding_activities",
      "completed"
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Planning Progress
```json
{
  "type": "planning_update",
  "event": "planning_progress",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "stage": "finding_flights",
    "progress": 45,
    "overallProgress": 60,
    "message": "Searching for flights from JFK to NRT...",
    "details": {
      "currentTask": "Searching 15 airlines",
      "resultsFound": 127
    }
  },
  "timestamp": "2024-01-15T10:31:30Z"
}
```

#### Planning Stage Complete
```json
{
  "type": "planning_update",
  "event": "stage_complete",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "stage": "finding_flights",
    "results": {
      "flightsFound": 127,
      "bestPrice": 899,
      "currency": "USD"
    },
    "nextStage": "finding_hotels"
  },
  "timestamp": "2024-01-15T10:32:00Z"
}
```

#### Planning Completed
```json
{
  "type": "planning_update",
  "event": "planning_completed",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "planningId": "pln_abc123",
    "completedAt": "2024-01-15T10:35:00Z",
    "duration": 300,
    "summary": {
      "citiesPlanned": 4,
      "flightsFound": 3,
      "hotelsFound": 8,
      "activitiesFound": 24,
      "totalEstimatedCost": 4850
    },
    "redirectUrl": "/trips/trp_xxx/itinerary"
  },
  "timestamp": "2024-01-15T10:35:00Z"
}
```

#### Planning Error
```json
{
  "type": "planning_update",
  "event": "planning_error",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "stage": "finding_flights",
    "error": {
      "code": "EXTERNAL_API_ERROR",
      "message": "Flight search service temporarily unavailable",
      "recoverable": true
    },
    "retryOptions": {
      "canRetry": true,
      "retryIn": 30
    }
  },
  "timestamp": "2024-01-15T10:33:00Z"
}
```

### 2. Itinerary Update Messages

#### Item Added
```json
{
  "type": "itinerary_update",
  "event": "item_added",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "date": "2024-04-01",
    "item": {
      "id": "itm_new123",
      "type": "attraction",
      "title": "Tokyo National Museum",
      "startTime": "10:00",
      "endTime": "13:00"
    },
    "addedBy": {
      "userId": "usr_xxx",
      "userName": "John Doe"
    }
  },
  "timestamp": "2024-01-15T10:40:00Z"
}
```

#### Item Updated
```json
{
  "type": "itinerary_update",
  "event": "item_updated",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "date": "2024-04-01",
    "itemId": "itm_xxx",
    "changes": {
      "startTime": {
        "from": "10:00",
        "to": "11:00"
      },
      "duration": {
        "from": "PT2H",
        "to": "PT3H"
      }
    },
    "updatedBy": {
      "userId": "usr_xxx",
      "userName": "John Doe"
    }
  },
  "timestamp": "2024-01-15T10:41:00Z"
}
```

#### Item Delayed
```json
{
  "type": "itinerary_update",
  "event": "item_delayed",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "itemId": "itm_xxx",
    "from": {
      "date": "2024-04-01",
      "startTime": "10:00"
    },
    "to": {
      "date": "2024-04-02",
      "startTime": "14:00"
    },
    "affectedItems": [
      {
        "itemId": "itm_yyy",
        "change": "time_shifted",
        "newStartTime": "10:30"
      }
    ],
    "delayedBy": {
      "userId": "usr_xxx",
      "userName": "John Doe"
    }
  },
  "timestamp": "2024-01-15T10:42:00Z"
}
```

#### Item Removed
```json
{
  "type": "itinerary_update",
  "event": "item_removed",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "date": "2024-04-01",
    "itemId": "itm_xxx",
    "item": {
      "title": "Tokyo Tower Visit",
      "type": "attraction"
    },
    "removedBy": {
      "userId": "usr_xxx",
      "userName": "John Doe"
    }
  },
  "timestamp": "2024-01-15T10:43:00Z"
}
```

### 3. Flight Update Messages

#### Flight Price Change
```json
{
  "type": "flight_update",
  "event": "price_change",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "flightId": "flt_xxx",
    "change": {
      "oldPrice": 1200,
      "newPrice": 1050,
      "currency": "USD",
      "difference": -150,
      "percentageChange": -12.5
    },
    "flight": {
      "flightNumber": "JL005",
      "airline": "Japan Airlines",
      "route": "JFK → NRT"
    },
    "actionUrl": "/trips/trp_xxx/flights/flt_xxx"
  },
  "timestamp": "2024-01-15T11:00:00Z"
}
```

#### Flight Status Update
```json
{
  "type": "flight_update",
  "event": "status_update",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "flightId": "flt_xxx",
    "flightNumber": "JL005",
    "status": {
      "from": "scheduled",
      "to": "delayed"
    },
    "details": {
      "delay": "PT2H30M",
      "newDeparture": "2024-04-01T12:30:00+09:00",
      "reason": "Weather conditions"
    }
  },
  "timestamp": "2024-01-15T11:30:00Z"
}
```

### 4. Accommodation Update Messages

#### Hotel Price Change
```json
{
  "type": "accommodation_update",
  "event": "price_change",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "accommodationId": "acc_xxx",
    "hotelName": "Park Hyatt Tokyo",
    "change": {
      "oldPrice": 450,
      "newPrice": 380,
      "currency": "USD",
      "difference": -70,
      "nights": 4,
      "totalSavings": 280
    },
    "actionUrl": "/trips/trp_xxx/accommodations/acc_xxx"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 5. Notification Messages

```json
{
  "type": "notification",
  "data": {
    "id": "not_xxx",
    "title": "Flight Price Drop!",
    "message": "Your selected flight from JFK to NRT dropped by $150",
    "severity": "info",
    "category": "price_alert",
    "icon": "trending_down",
    "action": {
      "type": "navigate",
      "url": "/trips/trp_xxx/flights",
      "label": "View Flight"
    },
    "dismissible": true,
    "expiresAt": "2024-01-16T12:00:00Z"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 6. Collaboration Messages

#### User Joined Trip
```json
{
  "type": "collaboration",
  "event": "user_joined",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "user": {
      "id": "usr_yyy",
      "name": "Jane Smith",
      "avatar": "https://cdn.tripplanner.com/avatars/usr_yyy.jpg"
    },
    "joinedAt": "2024-01-15T13:00:00Z"
  },
  "timestamp": "2024-01-15T13:00:00Z"
}
```

#### User Left Trip
```json
{
  "type": "collaboration",
  "event": "user_left",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "user": {
      "id": "usr_yyy",
      "name": "Jane Smith"
    },
    "leftAt": "2024-01-15T14:00:00Z"
  },
  "timestamp": "2024-01-15T14:00:00Z"
}
```

#### Cursor Position (for live editing)
```json
{
  "type": "collaboration",
  "event": "cursor_position",
  "tripId": "trp_87654321-4321-4321-4321-cba987654321",
  "data": {
    "user": {
      "id": "usr_yyy",
      "name": "Jane Smith",
      "color": "#FF5733"
    },
    "position": {
      "view": "itinerary",
      "date": "2024-04-01",
      "itemId": "itm_xxx"
    }
  },
  "timestamp": "2024-01-15T13:05:00Z"
}
```

---

## Connection Management

### Reconnection Strategy

```javascript
class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url;
    this.options = {
      maxReconnectAttempts: 10,
      initialReconnectDelay: 1000,
      maxReconnectDelay: 30000,
      reconnectDecay: 1.5,
      ...options
    };
    
    this.reconnectAttempts = 0;
    this.reconnectDelay = this.options.initialReconnectDelay;
    this.subscriptions = new Map();
    this.messageQueue = [];
  }

  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.reconnectDelay = this.options.initialReconnectDelay;
      this.resubscribeAll();
      this.flushMessageQueue();
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      if (!event.wasClean) {
        this.scheduleReconnect();
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }
    
    setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * this.options.reconnectDecay,
        this.options.maxReconnectDelay
      );
      console.log(`Reconnecting... attempt ${this.reconnectAttempts}`);
      this.connect();
    }, this.reconnectDelay);
  }

  resubscribeAll() {
    for (const [key, subscription] of this.subscriptions) {
      this.send({
        type: 'subscribe',
        subscriptions: [subscription]
      });
    }
  }

  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  send(message) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
    }
  }

  subscribe(subscription) {
    const key = `${subscription.channel}:${subscription.tripId || 'global'}`;
    this.subscriptions.set(key, subscription);
    this.send({
      type: 'subscribe',
      subscriptions: [subscription]
    });
  }

  unsubscribe(subscription) {
    const key = `${subscription.channel}:${subscription.tripId || 'global'}`;
    this.subscriptions.delete(key);
    this.send({
      type: 'unsubscribe',
      subscriptions: [subscription]
    });
  }
}
```

### Connection State Machine

```
┌─────────┐    connect()     ┌──────────┐
│  IDLE   │─────────────────▶│CONNECTING│
└─────────┘                  └────┬─────┘
                                  │
                    onopen success │
                                  ▼
┌─────────┐    onclose clean  ┌──────────┐
│ CLOSED  │◀──────────────────│ CONNECTED│
└─────────┘                   └────┬─────┘
                                   │
                    onerror/onclose│
                    unexpected     │
                                   ▼
                          ┌──────────────┐
                          │ RECONNECTING │
                          └──────────────┘
```

---

## Security

### Authentication

1. **Token-based Authentication**
   - JWT token from REST API authentication
   - Token passed in query parameter or header
   - Token validated on connection

2. **Connection Validation**
   ```javascript
   // Server-side connection handler
   function validateConnection(token) {
     try {
       const decoded = jwt.verify(token, JWT_SECRET);
       return {
         valid: true,
         userId: decoded.sub,
         permissions: decoded.permissions
       };
     } catch (error) {
       return { valid: false, error: error.message };
     }
   }
   ```

### Authorization

```javascript
// Check if user can access trip
function canAccessTrip(userId, tripId) {
  // Check if user is trip owner
  const trip = await db.trips.findOne({ id: tripId });
  if (trip.userId === userId) return true;
  
  // Check if user is a collaborator
  const collaborator = await db.collaborators.findOne({
    tripId,
    userId,
    status: 'active'
  });
  return !!collaborator;
}

// Message filtering based on permissions
function filterMessage(message, userPermissions) {
  if (message.type === 'planning_update' && !userPermissions.canViewPlanning) {
    return null;
  }
  return message;
}
```

### Rate Limiting

```javascript
// Per-connection rate limiting
class ConnectionRateLimiter {
  constructor(limit = 100, windowMs = 60000) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.requests = [];
  }

  canProceed() {
    const now = Date.now();
    this.requests = this.requests.filter(r => now - r < this.windowMs);
    
    if (this.requests.length >= this.limit) {
      return false;
    }
    
    this.requests.push(now);
    return true;
  }
}
```

---

## Error Handling

### Client Error Messages

```json
{
  "type": "error",
  "error": {
    "code": "INVALID_SUBSCRIPTION",
    "message": "Invalid subscription format",
    "details": {
      "field": "tripId",
      "issue": "Trip ID is required"
    }
  },
  "requestId": "req_xxx"
}
```

### Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `UNAUTHORIZED` | Invalid or expired token | Re-authenticate |
| `FORBIDDEN` | Insufficient permissions | Request access |
| `INVALID_MESSAGE` | Malformed message | Check message format |
| `INVALID_SUBSCRIPTION` | Invalid subscription | Check subscription params |
| `RATE_LIMITED` | Too many messages | Slow down |
| `INTERNAL_ERROR` | Server error | Retry with backoff |
| `TRIP_NOT_FOUND` | Trip doesn't exist | Verify trip ID |

### Error Recovery

```javascript
function handleWebSocketError(error) {
  switch (error.code) {
    case 'UNAUTHORIZED':
      // Redirect to login
      window.location.href = '/login';
      break;
      
    case 'RATE_LIMITED':
      // Back off and retry
      setTimeout(() => reconnect(), 5000);
      break;
      
    case 'INTERNAL_ERROR':
      // Exponential backoff
      scheduleReconnectWithBackoff();
      break;
      
    default:
      // Log and continue
      console.error('WebSocket error:', error);
  }
}
```

---

## Implementation Examples

### Server Implementation (Node.js with Socket.io)

```javascript
const io = require('socket.io')(server, {
  cors: { origin: '*' },
  pingTimeout: 60000,
  pingInterval: 30000
});

// Authentication middleware
io.use(async (socket, next) => {
  try {
    const token = socket.handshake.query.token;
    const decoded = jwt.verify(token, JWT_SECRET);
    socket.userId = decoded.sub;
    next();
  } catch (error) {
    next(new Error('Authentication failed'));
  }
});

io.on('connection', (socket) => {
  console.log(`User ${socket.userId} connected`);
  
  // Send connection ack
  socket.emit('message', {
    type: 'connection_ack',
    connectionId: socket.id,
    serverTime: new Date().toISOString()
  });
  
  // Handle subscriptions
  socket.on('subscribe', async (data) => {
    for (const sub of data.subscriptions) {
      if (sub.channel === 'trip') {
        // Verify access
        const hasAccess = await canAccessTrip(socket.userId, sub.tripId);
        if (!hasAccess) {
          socket.emit('message', {
            type: 'error',
            error: { code: 'FORBIDDEN', message: 'Access denied' },
            requestId: data.requestId
          });
          continue;
        }
        
        socket.join(`trip:${sub.tripId}`);
      }
      
      if (sub.channel === 'notifications') {
        socket.join(`notifications:${socket.userId}`);
      }
    }
    
    socket.emit('message', {
      type: 'subscription_ack',
      requestId: data.requestId,
      subscriptions: data.subscriptions.map(s => ({
        ...s,
        status: 'subscribed'
      }))
    });
  });
  
  // Handle ping
  socket.on('ping', (data) => {
    socket.emit('message', {
      type: 'pong',
      timestamp: new Date().toISOString(),
      clientTimestamp: data.timestamp
    });
  });
  
  socket.on('disconnect', () => {
    console.log(`User ${socket.userId} disconnected`);
  });
});

// Broadcast planning update
async function broadcastPlanningUpdate(tripId, data) {
  io.to(`trip:${tripId}`).emit('message', {
    type: 'planning_update',
    tripId,
    data,
    timestamp: new Date().toISOString()
  });
}
```

### Client Implementation (React Hook)

```javascript
import { useEffect, useRef, useState, useCallback } from 'react';

export function useTripWebSocket(tripId, token) {
  const ws = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const reconnectAttempts = useRef(0);

  useEffect(() => {
    if (!tripId || !token) return;

    const connect = () => {
      const wsUrl = `wss://api.tripplanner.com/v1/ws/connect?token=${token}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        
        // Subscribe to trip updates
        ws.current.send(JSON.stringify({
          type: 'subscribe',
          subscriptions: [{
            channel: 'trip',
            tripId,
            events: ['planning', 'itinerary', 'flight', 'accommodation']
          }]
        }));
      };

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        setMessages(prev => [...prev, message]);
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        
        // Reconnect with exponential backoff
        if (reconnectAttempts.current < 10) {
          const delay = Math.min(
            1000 * Math.pow(1.5, reconnectAttempts.current),
            30000
          );
          setTimeout(connect, delay);
          reconnectAttempts.current++;
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connect();

    // Heartbeat
    const heartbeat = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
      }
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      ws.current?.close();
    };
  }, [tripId, token]);

  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, messages, sendMessage };
}
```

### SSE Client Implementation

```javascript
export function useTripSSE(tripId, token) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (!tripId || !token) return;

    const connect = () => {
      const url = `https://api.tripplanner.com/v1/sse/subscribe?token=${token}&tripId=${tripId}`;
      eventSourceRef.current = new EventSource(url);

      eventSourceRef.current.onopen = () => {
        setIsConnected(true);
      };

      eventSourceRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
      };

      eventSourceRef.current.addEventListener('planning_update', (event) => {
        const data = JSON.parse(event.data);
        handlePlanningUpdate(data);
      });

      eventSourceRef.current.addEventListener('notification', (event) => {
        const data = JSON.parse(event.data);
        showNotification(data);
      });

      eventSourceRef.current.onerror = (error) => {
        console.error('SSE error:', error);
        setIsConnected(false);
        // Auto-reconnect is handled by browser
      };
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [tripId, token]);

  return { isConnected, events };
}
```

---

## Scaling Considerations

### Horizontal Scaling with Redis Pub/Sub

```javascript
// Server with Redis adapter
const io = require('socket.io')(server);
const redisAdapter = require('socket.io-redis');

io.adapter(redisAdapter({
  host: 'redis-cluster',
  port: 6379
}));

// Broadcasting across servers
async function broadcastToTrip(tripId, message) {
  // This will be broadcast to all servers
  io.to(`trip:${tripId}`).emit('message', message);
}

// Or using Redis directly for cross-server communication
const redis = require('redis');
const publisher = redis.createClient();

function publishUpdate(tripId, data) {
  publisher.publish(`trip:${tripId}`, JSON.stringify(data));
}

// Subscribe to updates
const subscriber = redis.createClient();
subscriber.on('message', (channel, message) => {
  const data = JSON.parse(message);
  const tripId = channel.replace('trip:', '');
  io.to(`trip:${tripId}`).emit('message', data);
});
```

### Load Balancing with Sticky Sessions

```nginx
# Nginx configuration
upstream websocket_backend {
    ip_hash;  # Sticky sessions for WebSocket
    server ws1.tripplanner.com:8080;
    server ws2.tripplanner.com:8080;
    server ws3.tripplanner.com:8080;
}

server {
    listen 443 ssl;
    server_name api.tripplanner.com;

    location /v1/ws/ {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```
