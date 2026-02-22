import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import TripNav from '../components/TripNav'
import './Flights.css'

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

function formatDateTime(dt) {
  if (!dt) return ''
  return dt.slice(0, 16).replace('T', ' ')
}

function formatDuration(mins) {
  if (!mins) return ''
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h}h ${m}m`
}

export default function Flights() {
  const { tripId } = useParams()
  const { user } = useAuth()

  const [searchParams, setSearchParams] = useSearchParams()
  const [flights, setFlights] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [bookingMsg, setBookingMsg] = useState('')

  useEffect(() => {
    loadFlights()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle Stripe redirect: verify booking on return
  useEffect(() => {
    const bookedId = searchParams.get('booked')
    const sessionId = searchParams.get('session_id')
    if (bookedId && sessionId) {
      api.verifyBooking(tripId, 'flight', bookedId, sessionId, user.id)
        .then(() => {
          setBookingMsg('✅ Flight booked successfully!')
          setFlights((prev) =>
            prev.map((f) => (f.id === bookedId ? { ...f, status: 'booked' } : f))
          )
          // Clean up URL params
          setSearchParams({})
          setTimeout(() => setBookingMsg(''), 4000)
        })
        .catch(() => setBookingMsg('⚠️ Could not verify booking — please check your email.'))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadFlights() {
    try {
      setLoading(true)
      const data = await api.getFlights(tripId, user.id)
      setFlights(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleBook(flightId) {
    try {
      const result = await api.bookFlight(tripId, flightId, user.id)
      // If backend returns a Stripe Checkout URL, redirect to it
      if (result.url) {
        window.location.href = result.url
        return
      }
      // Fallback: direct booking (Stripe not configured)
      setFlights((prev) =>
        prev.map((f) => (f.id === flightId ? { ...f, status: 'booked' } : f))
      )
      if (result.booking_url) {
        window.open(result.booking_url, '_blank')
      }
    } catch (err) {
      console.error('Failed to book flight:', err)
    }
  }

  async function handleSelect(flightId, flightType) {
    try {
      await api.selectFlight(tripId, flightId, user.id)
      setFlights((prev) =>
        prev.map((f) => {
          if (f.flight_type === flightType) {
            return { ...f, status: f.id === flightId ? 'selected' : 'suggested' }
          }
          return f
        })
      )
    } catch (err) {
      console.error('Failed to select flight:', err)
    }
  }

  const outbound = flights.filter((f) => f.flight_type === 'outbound')
  const returnFlights = flights.filter((f) => f.flight_type === 'return')

  return (
    <motion.div
      className="flights-page"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <TripNav />

      <header className="flights-page__header">
        <h1 className="flights-page__title">✈️ Flights</h1>
      </header>

      {bookingMsg && <div className="flights-page__success">{bookingMsg}</div>}
      {error && <div className="flights-page__error">{error}</div>}

      {!loading && flights.length === 0 ? (
        <div className="flights-page__empty">
          <p>No flights found. Start planning to generate flight options.</p>
        </div>
      ) : (
        <>
          {outbound.length > 0 && (
            <section className="flights-page__section">
              <h2 className="flights-page__section-title">Outbound Flights</h2>
              <div className="flights-page__list">
                {outbound.map((flight) => (
                  <FlightCard
                    key={flight.id}
                    flight={flight}
                    onBook={() => handleBook(flight.id)}
                    onSelect={() => handleSelect(flight.id, flight.flight_type)}
                  />
                ))}
              </div>
            </section>
          )}

          {returnFlights.length > 0 && (
            <section className="flights-page__section">
              <h2 className="flights-page__section-title">Return Flights</h2>
              <div className="flights-page__list">
                {returnFlights.map((flight) => (
                  <FlightCard
                    key={flight.id}
                    flight={flight}
                    onBook={() => handleBook(flight.id)}
                    onSelect={() => handleSelect(flight.id, flight.flight_type)}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </motion.div>
  )
}

function FlightCard({ flight, onBook, onSelect }) {
  const isBooked = flight.status === 'booked'
  const isSelected = flight.status === 'selected'

  return (
    <motion.div
      className={`flight-card ${isSelected ? 'flight-card--selected' : ''} ${isBooked ? 'flight-card--booked' : ''}`}
      whileHover={{ y: -2 }}
    >
      <div className="flight-card__main">
        <div className="flight-card__airline">
          <span className="flight-card__airline-name">{flight.airline}</span>
          <span className="flight-card__flight-num">{flight.flight_number}</span>
        </div>

        <div className="flight-card__route">
          <div className="flight-card__endpoint">
            <span className="flight-card__airport">{flight.from_airport}</span>
            <span className="flight-card__datetime">🛫 {formatDateTime(flight.departure_datetime)}</span>
          </div>
          <div className="flight-card__arrow">
            <div className="flight-card__arrow-line" />
            <span className="flight-card__duration">⏱️ {formatDuration(flight.duration_minutes)}</span>
          </div>
          <div className="flight-card__endpoint">
            <span className="flight-card__airport">{flight.to_airport}</span>
            <span className="flight-card__datetime">🛬 {formatDateTime(flight.arrival_datetime)}</span>
          </div>
        </div>

        <div className="flight-card__price-area">
          <span className="flight-card__price">${flight.price}</span>
          <span className="flight-card__currency">{flight.currency}</span>
        </div>
      </div>

      <div className="flight-card__actions">
        {isBooked ? (
          <span className="flight-card__booked-badge">✓ Booked</span>
        ) : (
          <>
            <button
              className={`flight-card__action ${isSelected ? 'flight-card__action--selected' : ''}`}
              onClick={onSelect}
            >
              {isSelected ? '✓ Selected' : 'Select'}
            </button>
            <button className="flight-card__action flight-card__action--book" onClick={onBook}>
              Book
            </button>
            {flight.booking_url && (
              <a
                href={flight.booking_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flight-card__action flight-card__action--external"
              >
                Open ↗
              </a>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}
