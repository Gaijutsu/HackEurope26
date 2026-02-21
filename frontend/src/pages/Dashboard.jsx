import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import './Dashboard.css'

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.97 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: i * 0.08, duration: 0.4, ease: [0.4, 0, 0.2, 1] },
  }),
}

function StatusBadge({ status }) {
  const config = {
    completed: { label: 'Planning Complete', icon: '✅', className: 'dash-card__status--done' },
    in_progress: { label: 'Planning...', icon: '🔄', className: 'dash-card__status--progress' },
    pending: { label: 'Pending', icon: '⏳', className: 'dash-card__status--pending' },
    failed: { label: 'Failed', icon: '❌', className: 'dash-card__status--failed' },
  }
  const c = config[status] || config.pending
  return (
    <span className={`dash-card__status ${c.className}`}>
      {c.icon} {c.label}
    </span>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [trips, setTrips] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTrips()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadTrips() {
    try {
      setLoading(true)
      const data = await api.getTrips(user.id)
      setTrips(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(tripId) {
    if (!confirm('Delete this trip?')) return
    try {
      await api.deleteTrip(tripId, user.id)
      setTrips((prev) => prev.filter((t) => t.id !== tripId))
    } catch (err) {
      setError(err.message)
    }
  }

  function handleView(trip) {
    if (trip.planning_status === 'completed') {
      navigate(`/trips/${trip.id}`)
    } else if (trip.planning_status === 'pending' || trip.planning_status === 'failed') {
      navigate(`/trips/${trip.id}/planning`)
    } else {
      navigate(`/trips/${trip.id}/planning`)
    }
  }

  return (
    <motion.div
      className="dashboard"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">My Trips</h1>
          <p className="dashboard__subtitle">
            {trips.length > 0
              ? `${trips.length} trip${trips.length !== 1 ? 's' : ''} planned`
              : 'No trips yet — start planning!'}
          </p>
        </div>
        <motion.button
          className="dashboard__new-btn"
          onClick={() => navigate('/')}
          whileHover={{ scale: 1.03, y: -2 }}
          whileTap={{ scale: 0.97 }}
        >
          <span>+</span> New Trip
        </motion.button>
      </header>

      {error && <div className="dashboard__error">{error}</div>}

      {loading ? (
        <div className="dashboard__grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="dash-card dash-card--skeleton">
              <div className="dash-card__skeleton-line dash-card__skeleton-line--title" />
              <div className="dash-card__skeleton-line" />
              <div className="dash-card__skeleton-line dash-card__skeleton-line--short" />
            </div>
          ))}
        </div>
      ) : trips.length === 0 ? (
        <motion.div
          className="dashboard__empty"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="dashboard__empty-icon">🗺️</div>
          <h2>No trips yet</h2>
          <p>Start by choosing a destination and we'll craft the perfect itinerary for you.</p>
          <motion.button
            className="dashboard__new-btn"
            onClick={() => navigate('/')}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Create Your First Trip
          </motion.button>
        </motion.div>
      ) : (
        <div className="dashboard__grid">
          <AnimatePresence>
            {trips.map((trip, i) => (
              <motion.div
                key={trip.id}
                className="dash-card"
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                custom={i}
                layout
                whileHover={{ y: -4 }}
              >
                <div className="dash-card__body" onClick={() => handleView(trip)}>
                  <h3 className="dash-card__title">{trip.title}</h3>
                  <p className="dash-card__dest">📍 {trip.destination}</p>
                  <p className="dash-card__dates">📅 {trip.start_date} → {trip.end_date}</p>
                  <StatusBadge status={trip.planning_status} />
                </div>
                <div className="dash-card__actions">
                  <button
                    className="dash-card__action dash-card__action--view"
                    onClick={() => handleView(trip)}
                  >
                    View
                  </button>
                  <button
                    className="dash-card__action dash-card__action--delete"
                    onClick={() => handleDelete(trip.id)}
                  >
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  )
}
