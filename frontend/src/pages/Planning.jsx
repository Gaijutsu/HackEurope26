import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import './Planning.css'

const AGENTS = [
  { key: 'DestinationResearcher', icon: '🔍', name: 'Destination Researcher', desc: 'Researching your destination with web search' },
  { key: 'CitySelector', icon: '🏙️', name: 'City Selector', desc: 'Choosing optimal cities to visit' },
  { key: 'FlightFinder', icon: '✈️', name: 'Flight Finder', desc: 'Searching for the best flights' },
  { key: 'AccommodationFinder', icon: '🏨', name: 'Accommodation Finder', desc: 'Finding perfect places to stay' },
  { key: 'ItineraryPlanner', icon: '📅', name: 'Itinerary Planner', desc: 'Building your day-by-day plan' },
  { key: 'PlanValidator', icon: '✅', name: 'Plan Validator', desc: 'Validating coherence, timing & costs' },
]

const AGENT_ORDER = {
  DestinationResearcher: 1,
  CitySelector: 2,
  FlightFinder: 3,
  AccommodationFinder: 4,
  ItineraryPlanner: 5,
  PlanValidator: 6,
}

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

export default function Planning() {
  const { tripId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [trip, setTrip] = useState(null)
  const [agentStates, setAgentStates] = useState({})
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState([])
  const [statusText, setStatusText] = useState('Preparing agent pipeline...')
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState('')
  const streamRef = useRef(null)
  const logsEndRef = useRef(null)
  const startedRef = useRef(false)

  useEffect(() => {
    // Guard against React StrictMode double-mount
    if (startedRef.current) return
    startedRef.current = true
    loadTripAndStart()
    return () => {
      if (streamRef.current) streamRef.current.cancel()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadTripAndStart() {
    try {
      const tripData = await api.getTrip(tripId, user.id)
      setTrip(tripData)

      if (tripData.planning_status === 'completed') {
        setIsComplete(true)
        setProgress(100)
        setStatusText('Planning already completed!')
        return
      }

      if (tripData.planning_status === 'in_progress') {
        setStatusText('⏳ Planning is already in progress…')
        setProgress(50)
        return
      }

      // Start SSE stream
      setStatusText('🚀 Starting agent pipeline...')
      streamRef.current = api.streamPlanning(tripId, user.id, {
        onProgress: handleProgress,
        onComplete: handleComplete,
        onError: handleError,
      })
    } catch (err) {
      setError(err.message)
    }
  }

  function handleProgress(event) {
    const agentName = event.agent || 'Unknown'
    const status = event.status || ''
    const message = event.message || ''

    const idx = AGENT_ORDER[agentName] || 0

    if (status === 'running') {
      const pct = Math.min(Math.round(((idx - 1) / 6) * 100), 95)
      setProgress(pct)
      setStatusText(`🔄 ${agentName}: ${message}`)
      setAgentStates((prev) => ({ ...prev, [agentName]: 'running' }))
    } else if (status === 'done') {
      const pct = Math.min(Math.round((idx / 6) * 100), 95)
      setProgress(pct)
      setStatusText(`✅ ${agentName}: ${message}`)
      setAgentStates((prev) => ({ ...prev, [agentName]: 'done' }))
    } else if (status === 'skipped') {
      setStatusText(`⏭️ ${agentName}: ${message}`)
      setAgentStates((prev) => ({ ...prev, [agentName]: 'skipped' }))
    }

    setLogs((prev) => [...prev, { agent: agentName, status, message, time: new Date().toLocaleTimeString() }])
  }

  function handleComplete() {
    setProgress(100)
    setStatusText('✅ All agents finished! Trip plan ready.')
    setIsComplete(true)
  }

  function handleError(err) {
    setError(err.message || 'Planning failed')
    setStatusText('❌ Planning encountered an error')
  }

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  function getAgentStatus(key) {
    return agentStates[key] || 'waiting'
  }

  function getAgentIcon(status) {
    switch (status) {
      case 'running': return '🔄'
      case 'done': return '✅'
      case 'skipped': return '⏭️'
      default: return '⏳'
    }
  }

  return (
    <motion.div
      className="planning"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <header className="planning__header">
        <h1 className="planning__title">
          {isComplete ? '🎉 Trip Plan Ready!' : '🤖 AI Agents Planning Your Trip...'}
        </h1>
        {trip && (
          <p className="planning__meta">
            📍 {trip.destination} &nbsp;·&nbsp; 📅 {trip.start_date} → {trip.end_date}
          </p>
        )}
      </header>

      {error && <div className="planning__error">{error}</div>}

      {/* Progress bar */}
      <div className="planning__progress-wrap">
        <div className="planning__progress-bar">
          <motion.div
            className="planning__progress-fill"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <span className="planning__progress-pct">{progress}%</span>
      </div>

      <p className="planning__status-text">{statusText}</p>

      {/* Agent pipeline */}
      <div className="planning__agents">
        <h2 className="planning__section-title">🧠 Agent Pipeline</h2>
        <div className="planning__agent-list">
          {AGENTS.map((agent) => {
            const status = getAgentStatus(agent.key)
            return (
              <motion.div
                key={agent.key}
                className={`planning__agent planning__agent--${status}`}
                layout
              >
                <span className="planning__agent-icon">{agent.icon}</span>
                <div className="planning__agent-info">
                  <span className="planning__agent-name">{agent.name}</span>
                  <span className="planning__agent-desc">{agent.desc}</span>
                </div>
                <span className="planning__agent-status">{getAgentIcon(status)}</span>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Activity log */}
      {logs.length > 0 && (
        <div className="planning__logs">
          <h3 className="planning__logs-title">📋 Activity Log</h3>
          <div className="planning__logs-list">
            {logs.map((log, i) => (
              <div key={i} className={`planning__log planning__log--${log.status}`}>
                <span className="planning__log-time">{log.time}</span>
                <span className="planning__log-agent">{log.agent}</span>
                <span className="planning__log-msg">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* Completion actions */}
      {isComplete && (
        <motion.div
          className="planning__done-actions"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <motion.button
            className="planning__action-btn planning__action-btn--primary"
            onClick={() => navigate(`/trips/${tripId}`)}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.97 }}
          >
            📅 View Itinerary
          </motion.button>
          <motion.button
            className="planning__action-btn"
            onClick={() => navigate(`/trips/${tripId}/flights`)}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            ✈️ View Flights
          </motion.button>
          <motion.button
            className="planning__action-btn"
            onClick={() => navigate(`/trips/${tripId}/accommodations`)}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            🏨 View Hotels
          </motion.button>
        </motion.div>
      )}
    </motion.div>
  )
}
