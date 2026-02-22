import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useAuth } from './contexts/AuthContext'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import PlanForm from './pages/PlanForm'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Planning from './pages/Planning'
import TripView from './pages/TripView'
import Flights from './pages/Flights'
import Accommodations from './pages/Accommodations'
import BuyCredits from './pages/BuyCredits'
import './App.css'

// Group trip sub-routes under one key so tab switches are instant (no exit→enter animation)
function getRouteKey(pathname) {
  const tripMatch = pathname.match(/^\/trips\/[^/]+/)
  if (tripMatch) return tripMatch[0]
  return pathname
}

function App() {
  const location = useLocation()
  const { isAuthenticated } = useAuth()

  // Hide navbar on landing and auth pages for cleaner UX
  const hideNavbar = ['/', '/login', '/register', '/credits', '/credits/success'].includes(location.pathname) || location.pathname.startsWith('/plan')

  return (
    <>
      {!hideNavbar && isAuthenticated && <Navbar />}
      <AnimatePresence mode="wait">
        <Routes location={location} key={getRouteKey(location.pathname)}>
          {/* Public routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/plan" element={<PlanForm />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/credits" element={<BuyCredits />} />
          <Route path="/credits/success" element={<BuyCredits />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/trips/:tripId/planning" element={<ProtectedRoute><Planning /></ProtectedRoute>} />
          <Route path="/trips/:tripId" element={<ProtectedRoute><TripView /></ProtectedRoute>} />
          <Route path="/trips/:tripId/flights" element={<ProtectedRoute><Flights /></ProtectedRoute>} />
          <Route path="/trips/:tripId/accommodations" element={<ProtectedRoute><Accommodations /></ProtectedRoute>} />
        </Routes>
      </AnimatePresence>
    </>
  )
}

export default App
