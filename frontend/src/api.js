/**
 * API client for the Agentic Trip Planner backend.
 * All API calls go through this module for consistency.
 */

const API_URL = 'http://localhost:8000'

/**
 * Get stored auth token from localStorage.
 */
function getToken() {
  return localStorage.getItem('token')
}

/**
 * Build headers with optional auth token.
 */
function authHeaders(extra = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...extra }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * Generic fetch wrapper with error handling.
 */
async function apiFetch(path, options = {}) {
  const url = `${API_URL}${path}`
  const res = await fetch(url, {
    headers: authHeaders(options.headers),
    ...options,
    headers: authHeaders(options.headers),
  })

  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }

  // Handle no-content responses
  if (res.status === 204) return null
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────

export async function login(email, password) {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function register(name, email, password) {
  return apiFetch('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

// ── Trips ─────────────────────────────────────────────────────────────────

export async function getTrips(userId) {
  return apiFetch(`/trips?user_id=${encodeURIComponent(userId)}`)
}

export async function getTrip(tripId, userId) {
  return apiFetch(`/trips/${tripId}?user_id=${encodeURIComponent(userId)}`)
}

export async function createTrip(userId, tripData) {
  return apiFetch(`/trips?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: JSON.stringify(tripData),
  })
}

export async function deleteTrip(tripId, userId) {
  return apiFetch(`/trips/${tripId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
}

// ── Planning ──────────────────────────────────────────────────────────────

export async function startPlanning(tripId, userId) {
  return apiFetch(`/trips/${tripId}/plan?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
  })
}

export async function getPlanningStatus(tripId, userId) {
  return apiFetch(`/trips/${tripId}/plan/status?user_id=${encodeURIComponent(userId)}`)
}

/**
 * Start SSE stream for planning progress.
 * Returns an EventSource-like interface using fetch streaming.
 */
export function streamPlanning(tripId, userId, { onProgress, onComplete, onError }) {
  const url = `${API_URL}/trips/${tripId}/plan/stream?user_id=${encodeURIComponent(userId)}`
  let cancelled = false

  async function consume() {
    try {
      const res = await fetch(url, { headers: authHeaders() })
      if (!res.ok) {
        onError?.(new Error(`Stream failed: HTTP ${res.status}`))
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (!cancelled) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'complete') {
              onComplete?.(event)
            } else if (event.type === 'error') {
              onError?.(new Error(event.message || 'Unknown error'))
            } else {
              onProgress?.(event)
            }
          } catch {
            // skip unparseable lines
          }
        }
      }
    } catch (err) {
      if (!cancelled) onError?.(err)
    }
  }

  consume()

  return {
    cancel() {
      cancelled = true
    },
  }
}

export async function regenerateItinerary(tripId, userId) {
  return apiFetch(`/trips/${tripId}/regenerate-itinerary?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
  })
}

/**
 * Send a chat message to modify the itinerary via an AI agent.
 * Returns { reply: string, days_planned: number }
 */
export async function chatModifyItinerary(tripId, userId, message) {
  return apiFetch(`/trips/${tripId}/chat?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

// ── Itinerary ─────────────────────────────────────────────────────────────

export async function getItinerary(tripId, userId) {
  return apiFetch(`/trips/${tripId}/itinerary?user_id=${encodeURIComponent(userId)}`)
}

export async function completeItem(tripId, itemId, userId) {
  return apiFetch(
    `/trips/${tripId}/itinerary/items/${itemId}/complete?user_id=${encodeURIComponent(userId)}`,
    { method: 'PUT' }
  )
}

export async function delayItem(tripId, itemId, newDay, userId) {
  return apiFetch(
    `/trips/${tripId}/itinerary/items/${itemId}/delay?user_id=${encodeURIComponent(userId)}&new_day=${newDay}`,
    { method: 'PUT' }
  )
}

// ── iCal ──────────────────────────────────────────────────────────────────

export function getICalUrl(tripId, userId) {
  return `${API_URL}/trips/${tripId}/ical?user_id=${encodeURIComponent(userId)}`
}

// ── Flights ───────────────────────────────────────────────────────────────

export async function getFlights(tripId, userId) {
  return apiFetch(`/trips/${tripId}/flights?user_id=${encodeURIComponent(userId)}`)
}

export async function bookFlight(tripId, flightId, userId) {
  return apiFetch(
    `/trips/${tripId}/flights/${flightId}/book?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' }
  )
}

export async function selectFlight(tripId, flightId, userId) {
  return apiFetch(
    `/trips/${tripId}/flights/${flightId}/select?user_id=${encodeURIComponent(userId)}`,
    { method: 'PUT' }
  )
}

// ── Accommodations ────────────────────────────────────────────────────────

export async function getAccommodations(tripId, userId) {
  return apiFetch(`/trips/${tripId}/accommodations?user_id=${encodeURIComponent(userId)}`)
}

export async function bookAccommodation(tripId, accId, userId) {
  return apiFetch(
    `/trips/${tripId}/accommodations/${accId}/book?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' }
  )
}

export async function selectAccommodation(tripId, accId, userId) {
  return apiFetch(
    `/trips/${tripId}/accommodations/${accId}/select?user_id=${encodeURIComponent(userId)}`,
    { method: 'PUT' }
  )
}

// ── Pinterest (mood boards) ──────────────────────────────────────────────

export async function getPinterestImages(city, country) {
  const url = `${API_URL}/pinterest?city=${encodeURIComponent(city)}&country=${encodeURIComponent(country)}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch mood boards')
  return res.json()
}

// ── Health ────────────────────────────────────────────────────────────────

export async function healthCheck() {
  return apiFetch('/health')
}

// ── Credits ───────────────────────────────────────────────────────────────

export async function getCredits(userId) {
  return apiFetch(`/credits?user_id=${encodeURIComponent(userId)}`)
}

export async function adjustCredits(userId, amount) {
  return apiFetch(`/credits/adjust?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: JSON.stringify({ amount }),
  })
}

export async function createCheckoutSession(userId, packageId) {
  return apiFetch(`/credits/checkout?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: JSON.stringify({ package: packageId }),
  })
}

export async function verifyCheckoutSuccess(userId, sessionId) {
  return apiFetch(`/credits/success?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`)
}

// ── Budget tracker ────────────────────────────────────────────────────────

export async function getTripBudget(tripId, userId) {
  return apiFetch(`/trips/${tripId}/budget?user_id=${encodeURIComponent(userId)}`)
}

// ── Disruption / weather monitor ──────────────────────────────────────────

export async function getDisruptions(tripId, userId) {
  return apiFetch(`/trips/${tripId}/disruptions?user_id=${encodeURIComponent(userId)}`)
}

// ── Travel guide generator ────────────────────────────────────────────────

export async function generateTravelGuide(tripId, userId) {
  return apiFetch(`/trips/${tripId}/travel-guide?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

// ── Chat history ──────────────────────────────────────────────────────────

export async function getChatHistory(tripId, userId) {
  return apiFetch(`/trips/${tripId}/chat/history?user_id=${encodeURIComponent(userId)}`)
}

// ── Booking verification ──────────────────────────────────────────────────

export async function verifyBooking(tripId, itemType, itemId, sessionId, userId) {
  const params = new URLSearchParams({
    item_type: itemType,
    item_id: itemId,
    session_id: sessionId,
    user_id: userId,
  })
  return apiFetch(`/trips/${tripId}/booking/verify?${params.toString()}`)
}
