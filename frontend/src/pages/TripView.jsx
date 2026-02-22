import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import TripNav from '../components/TripNav'
import ItineraryChat from '../components/ItineraryChat'
import ItineraryMap from '../components/ItineraryMap'
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

function TravelRoute({ travelInfo, travelPrefs }) {
  if (!travelInfo || !travelInfo.display) return null

  const walking = travelInfo.walking || {}
  const transit = travelInfo.transit || {}
  const recommended = travelInfo.recommended || 'walking'
  const avoid = (travelPrefs?.avoid || []).map((m) => m.toLowerCase())

  const walkAvoided = avoid.includes('walking')
  const transitAvoided = avoid.includes('transit')

  return (
    <div className="travel-route">
      <div className="travel-route__line" />
      <div className="travel-route__badges">
        {/* Primary recommended badge */}
        <span className={`travel-route__badge travel-route__badge--${recommended}`}>
          {travelInfo.display}
        </span>

        {/* Secondary option (the non-recommended one) */}
        {recommended === 'walking' && transit.duration_text && (
          <span className={`travel-route__badge travel-route__badge--alt${transitAvoided ? ' travel-route__badge--avoided' : ''}`}>
            🚇 {transit.duration_text} ({transit.transit_name || 'transit'})
            {transitAvoided && ' ⚠️'}
          </span>
        )}
        {recommended === 'transit' && walking.duration_text && (
          <span className={`travel-route__badge travel-route__badge--alt${walkAvoided ? ' travel-route__badge--avoided' : ''}`}>
            🚶 {walking.duration_text}
            {walkAvoided && ' ⚠️'}
          </span>
        )}

        {/* Distance */}
        {walking.distance_text && (
          <span className="travel-route__distance">
            📏 {walking.distance_text}
          </span>
        )}
      </div>
      <div className="travel-route__line" />
    </div>
  )
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
  const [travelPrefs, setTravelPrefs] = useState(null)

  // New: budget tracker, disruption alerts, travel guide
  const [budget, setBudget] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [guideText, setGuideText] = useState('')
  const [guideLoading, setGuideLoading] = useState(false)
  const [showGuide, setShowGuide] = useState(false)

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

      // Load budget + disruptions in background
      api.getTripBudget(tripId, user.id).then(setBudget).catch(() => {})
      api.getDisruptions(tripId, user.id).then((d) => setAlerts(d.alerts || [])).catch(() => {})
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerateGuide() {
    setGuideLoading(true)
    try {
      const result = await api.generateTravelGuide(tripId, user.id)
      setGuideText(result.guide)
      setShowGuide(true)
    } catch (err) {
      setGuideText(`⚠️ Failed to generate guide: ${err.message}`)
      setShowGuide(true)
    } finally {
      setGuideLoading(false)
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
        // Capture travel preferences returned by the AI
        if (result.travel_prefs && (result.travel_prefs.avoid?.length || result.travel_prefs.prefer?.length)) {
          setTravelPrefs(result.travel_prefs)
        }
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

      {/* Budget tracker */}
      {budget && (
        <div className="budget-tracker">
          <div className="budget-tracker__header">
            <h3 className="budget-tracker__title">💰 Budget Tracker</h3>
            <span className="budget-tracker__level">{budget.budget_level} · {budget.duration_days}d · {budget.num_travelers} traveler{budget.num_travelers > 1 ? 's' : ''}</span>
          </div>
          <div className="budget-tracker__bar-wrap">
            <div className="budget-tracker__bar">
              <div
                className="budget-tracker__bar-booked"
                style={{ width: `${Math.min((budget.total_booked / budget.estimated_budget) * 100, 100)}%` }}
                title={`Booked: $${budget.total_booked}`}
              />
              <div
                className="budget-tracker__bar-planned"
                style={{ width: `${Math.min((budget.total_planned / budget.estimated_budget) * 100, 100 - (budget.total_booked / budget.estimated_budget) * 100)}%` }}
                title={`Planned: $${budget.total_planned}`}
              />
            </div>
            <span className="budget-tracker__label">
              ${budget.total_all.toLocaleString()} / ${budget.estimated_budget.toLocaleString()}
            </span>
          </div>
          <div className="budget-tracker__breakdown">
            <span>✈️ Flights: ${budget.breakdown.flights_booked + budget.breakdown.flights_selected}</span>
            <span>🏨 Hotels: ${budget.breakdown.accommodations_booked + budget.breakdown.accommodations_selected}</span>
            <span>🎭 Activities: ${budget.breakdown.activities}</span>
          </div>
        </div>
      )}

      {/* Disruption alerts */}
      {alerts.length > 0 && (
        <div className="disruption-alerts">
          <h3 className="disruption-alerts__title">⚠️ Weather Alerts</h3>
          <div className="disruption-alerts__list">
            {alerts.slice(0, 5).map((alert, i) => (
              <div key={i} className={`disruption-alert disruption-alert--${alert.severity}`}>
                <div className="disruption-alert__info">
                  <span className="disruption-alert__title">{alert.title}</span>
                  <span className="disruption-alert__msg">{alert.message}</span>
                </div>
                {alert.auto_prompt && (
                  <button
                    className="disruption-alert__adapt-btn"
                    onClick={() => handleChatSend(alert.auto_prompt)}
                  >
                    🔄 Auto-adapt
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Travel guide section */}
      <div className="travel-guide-section">
        <button
          className="travel-guide-section__btn"
          onClick={handleGenerateGuide}
          disabled={guideLoading}
        >
          {guideLoading ? '⚙️ Generating guide...' : '📖 Generate Travel Guide'}
        </button>
        {showGuide && (
          <div className="travel-guide-section__content">
            <button className="travel-guide-section__close" onClick={() => setShowGuide(false)}>✕</button>
            <div className="travel-guide-section__text">
              {guideText.split('\n').map((line, i) => {
                if (line.startsWith('## ')) return <h2 key={i}>{line.slice(3)}</h2>
                if (line.startsWith('### ')) return <h3 key={i}>{line.slice(4)}</h3>
                if (line.startsWith('- ')) return <li key={i}>{line.slice(2)}</li>
                if (line.startsWith('**') && line.endsWith('**')) return <p key={i}><strong>{line.slice(2, -2)}</strong></p>
                if (line.trim() === '') return <br key={i} />
                return <p key={i}>{line}</p>
              })}
            </div>
          </div>
        )}
      </div>

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

          {/* Active travel preference banner */}
          {travelPrefs && (travelPrefs.avoid?.length > 0 || travelPrefs.prefer?.length > 0) && (
            <div className="travel-prefs-banner">
              <span className="travel-prefs-banner__icon">🔀</span>
              <span className="travel-prefs-banner__text">
                Routes adjusted
                {travelPrefs.avoid?.length > 0 && (
                  <> — avoiding <strong>{travelPrefs.avoid.join(', ')}</strong></>
                )}
                {travelPrefs.prefer?.length > 0 && (
                  <> — preferring <strong>{travelPrefs.prefer.join(', ')}</strong></>
                )}
              </span>
              <button
                className="travel-prefs-banner__clear"
                onClick={() => setTravelPrefs(null)}
                title="Clear travel preferences"
              >
                ✕
              </button>
            </div>
          )}

          {/* Two-column body: itinerary left, map right */}
          <div className="trip-view__body">
            {/* Left: items list */}
            <div className="trip-view__left">
              <div className="trip-view__items-header">
                <h2>Day {selectedDay}</h2>
                <span className="trip-view__items-count">{items.length} activities</span>
              </div>

              <div className="trip-view__timeline">
                <AnimatePresence mode="wait">
                  {items.map((item, i) => (
                    <motion.div
                      key={item.id}
                      className="itin-item-wrapper"
                      variants={itemVariants}
                      initial="hidden"
                      animate="visible"
                      custom={i}
                    >
                      {/* Travel route badge between items */}
                      {i > 0 && item.travel_info && item.travel_info.display && (
                        <TravelRoute travelInfo={item.travel_info} travelPrefs={travelPrefs} />
                      )}

                      <div className="itin-item">
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
                      </div>{/* /itin-item */}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* Right: map */}
            <div className="trip-view__right">
              <ItineraryMap
                key={selectedDay}
                items={items}
                destination={trip?.destination || ''}
              />
            </div>
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
