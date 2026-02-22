import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import TripNav from '../components/TripNav'
import ItineraryChat from '../components/ItineraryChat'
import './TripView.css'

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.05, duration: 0.3, ease: [0.4, 0, 0.2, 1] },
  }),
}

function StatusTag({ status }) {
  const map = {
    completed: { label: 'Done', cls: 'itin-item__tag--done' },
    delayed: { label: 'Delayed', cls: 'itin-item__tag--delayed' },
    planned: { label: 'Planned', cls: 'itin-item__tag--planned' },
    skipped: { label: 'Skipped', cls: 'itin-item__tag--skipped' },
  }
  const c = map[status] || map.planned
  return <span className={`itin-item__tag ${c.cls}`}>{c.label}</span>
}

export default function TripView() {
  const { tripId } = useParams()
  const { user } = useAuth()

  const [trip, setTrip] = useState(null)
  const [days, setDays] = useState([])
  const [selectedDay, setSelectedDay] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadData() {
    try {
      setLoading(true)
      const [tripData, itinData] = await Promise.all([
        api.getTrip(tripId, user.id),
        api.getItinerary(tripId, user.id),
      ])
      setTrip(tripData)
      setDays(itinData.days || [])
      if (itinData.days?.length) {
        setSelectedDay(itinData.days[0].day_number)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleComplete(itemId) {
    try {
      await api.completeItem(tripId, itemId, user.id)
      setDays((prev) =>
        prev.map((d) => ({
          ...d,
          items: d.items.map((it) => (it.id === itemId ? { ...it, status: 'completed' } : it)),
        }))
      )
    } catch (err) {
      console.error('Failed to complete item:', err)
    }
  }

  async function handleDelay(itemId, newDay) {
    try {
      await api.delayItem(tripId, itemId, newDay, user.id)
      setDays((prev) =>
        prev.map((d) => ({
          ...d,
          items: d.items.map((it) =>
            it.id === itemId ? { ...it, status: 'delayed', delayed_to_day: newDay } : it
          ),
        }))
      )
    } catch (err) {
      console.error('Failed to delay item:', err)
    }
  }

  const handleChatSend = useCallback(
    async (message) => {
      setChatLoading(true)
      try {
        const result = await api.chatModifyItinerary(tripId, user.id, message)
        // Reload itinerary to reflect changes
        const itinData = await api.getItinerary(tripId, user.id)
        setDays(itinData.days || [])
        return result
      } finally {
        setChatLoading(false)
      }
    },
    [tripId, user.id]
  )

  const currentDay = days.find((d) => d.day_number === selectedDay)
  const items = currentDay?.items || []

  return (
    <motion.div
      className="trip-view"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <TripNav />

      {/* Trip header */}
      {trip && (
        <header className="trip-view__header">
          <div className="trip-view__header-info">
            <h1 className="trip-view__title">{trip.title}</h1>
            <p className="trip-view__meta">
              📍 {trip.destination} &nbsp;·&nbsp; 📅 {trip.start_date} → {trip.end_date}
            </p>
          </div>
          <a
            href={api.getICalUrl(tripId, user.id)}
            className="trip-view__ical-btn"
            download
          >
            📅 Download .ics
          </a>
        </header>
      )}

      {error && <div className="trip-view__error">{error}</div>}

      {!loading && days.length === 0 ? (
        <div className="trip-view__empty">
          <p>No itinerary items yet. Start planning first!</p>
        </div>
      ) : (
        <>
          {/* Day selector */}
          <div className="trip-view__day-selector">
            {days.map((d) => (
              <button
                key={d.day_number}
                className={`trip-view__day-btn ${d.day_number === selectedDay ? 'trip-view__day-btn--active' : ''}`}
                onClick={() => setSelectedDay(d.day_number)}
              >
                Day {d.day_number}
              </button>
            ))}
          </div>

          {/* Items */}
          <div className="trip-view__items-header">
            <h2>Day {selectedDay}</h2>
            <span className="trip-view__items-count">{items.length} activities</span>
          </div>

          <div className="trip-view__timeline">
            <AnimatePresence mode="wait">
              {items.map((item, i) => (
                <motion.div
                  key={item.id}
                  className="itin-item"
                  variants={itemVariants}
                  initial="hidden"
                  animate="visible"
                  custom={i}
                >
                  <div className="itin-item__time">
                    <span className="itin-item__time-text">{item.start_time}</span>
                    <span className="itin-item__duration">{item.duration_minutes}m</span>
                  </div>

                  <div className="itin-item__connector">
                    <div className="itin-item__dot" />
                    {i < items.length - 1 && <div className="itin-item__line" />}
                  </div>

                  <div className="itin-item__content">
                    <div className="itin-item__header">
                      <h3 className="itin-item__title">
                        {item.title}
                        {item.is_ai_suggested ? ' ⭐' : ''}
                      </h3>
                      <StatusTag status={item.status} />
                    </div>

                    <p className="itin-item__desc">{item.description}</p>

                    {item.location && (
                      <div className="itin-item__location">
                        {item.google_maps_url ? (
                          <a
                            href={item.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="itin-item__maps-link"
                          >
                            📍 {item.location}
                          </a>
                        ) : (
                          <span>📍 {item.location}</span>
                        )}
                      </div>
                    )}

                    {item.cost_usd > 0 && (
                      <div className="itin-item__cost">
                        💵 ${item.cost_usd}
                        {item.currency !== 'USD' && item.cost_local && (
                          <span className="itin-item__cost-local"> ({item.cost_local})</span>
                        )}
                      </div>
                    )}

                    {item.status === 'planned' && (
                      <div className="itin-item__actions">
                        <button
                          className="itin-item__action-btn itin-item__action-btn--done"
                          onClick={() => handleComplete(item.id)}
                        >
                          ✓ Done
                        </button>
                        <select
                          className="itin-item__delay-select"
                          defaultValue=""
                          onChange={(e) => {
                            if (e.target.value) handleDelay(item.id, parseInt(e.target.value))
                          }}
                        >
                          <option value="" disabled>Delay to...</option>
                          {days.map((d) => (
                            <option key={d.day_number} value={d.day_number}>
                              Day {d.day_number}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </>
      )}

      {/* AI Chat for itinerary modifications */}
      {trip && days.length > 0 && (
        <ItineraryChat onSend={handleChatSend} loading={chatLoading} />
      )}
    </motion.div>
  )
}
