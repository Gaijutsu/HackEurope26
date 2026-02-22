import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import TripNav from '../components/TripNav'
import './Accommodations.css'

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

export default function Accommodations() {
  const { tripId } = useParams()
  const { user } = useAuth()

  const [accommodations, setAccommodations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadAccommodations()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadAccommodations() {
    try {
      setLoading(true)
      const data = await api.getAccommodations(tripId, user.id)
      setAccommodations(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleBook(accId) {
    try {
      const result = await api.bookAccommodation(tripId, accId, user.id)
      setAccommodations((prev) =>
        prev.map((a) => (a.id === accId ? { ...a, status: 'booked' } : a))
      )
      if (result.booking_url) {
        window.open(result.booking_url, '_blank')
      }
    } catch (err) {
      console.error('Failed to book accommodation:', err)
    }
  }

  async function handleSelect(accId, city) {
    try {
      await api.selectAccommodation(tripId, accId, user.id)
      setAccommodations((prev) =>
        prev.map((a) => {
          if (a.city === city) {
            return { ...a, status: a.id === accId ? 'selected' : 'suggested' }
          }
          return a
        })
      )
    } catch (err) {
      console.error('Failed to select accommodation:', err)
    }
  }

  return (
    <motion.div
      className="accom-page"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <TripNav />

      <header className="accom-page__header">
        <h1 className="accom-page__title">🏨 Accommodations</h1>
      </header>

      {error && <div className="accom-page__error">{error}</div>}

      {!loading && accommodations.length === 0 ? (
        <div className="accom-page__empty">
          <p>No accommodations found. Start planning to generate options.</p>
        </div>
      ) : (
        <div className="accom-page__list">
          {accommodations.map((acc) => (
            <AccomCard
              key={acc.id}
              acc={acc}
              onBook={() => handleBook(acc.id)}
              onSelect={() => handleSelect(acc.id, acc.city)}
            />
          ))}
        </div>
      )}
    </motion.div>
  )
}

function AccomCard({ acc, onBook, onSelect }) {
  const isBooked = acc.status === 'booked'
  const isSelected = acc.status === 'selected'

  return (
    <motion.div
      className={`accom-card ${isSelected ? 'accom-card--selected' : ''} ${isBooked ? 'accom-card--booked' : ''}`}
      whileHover={{ y: -2 }}
    >
      <div className="accom-card__main">
        <div className="accom-card__info">
          <h3 className="accom-card__name">{acc.name}</h3>
          <div className="accom-card__details">
            {acc.rating && (
              <span className="accom-card__rating">⭐ {acc.rating}/5</span>
            )}
            <span className="accom-card__type">{acc.type}</span>
          </div>
          <p className="accom-card__location">📍 {acc.city} — {acc.address}</p>
          <p className="accom-card__dates">📅 {acc.check_in_date} → {acc.check_out_date}</p>
          {acc.amenities && acc.amenities.length > 0 && (
            <div className="accom-card__amenities">
              {acc.amenities.slice(0, 4).map((a, i) => (
                <span key={i} className="accom-card__amenity">✓ {a}</span>
              ))}
            </div>
          )}
        </div>

        <div className="accom-card__pricing">
          <span className="accom-card__price">${acc.price_per_night}</span>
          <span className="accom-card__price-label">/ night</span>
          <span className="accom-card__total">Total: ${acc.total_price}</span>
        </div>
      </div>

      <div className="accom-card__actions">
        {isBooked ? (
          <span className="accom-card__booked-badge">✓ Booked</span>
        ) : (
          <>
            <button
              className={`accom-card__action ${isSelected ? 'accom-card__action--selected' : ''}`}
              onClick={onSelect}
            >
              {isSelected ? '✓ Selected' : 'Select'}
            </button>
            <button className="accom-card__action accom-card__action--book" onClick={onBook}>
              Book
            </button>
            {acc.booking_url && (
              <a
                href={acc.booking_url}
                target="_blank"
                rel="noopener noreferrer"
                className="accom-card__action accom-card__action--external"
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
