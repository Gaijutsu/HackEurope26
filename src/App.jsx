import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Landing from './pages/Landing'
import PlanForm from './pages/PlanForm'
import './App.css'

function App() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/plan" element={<PlanForm />} />
      </Routes>
    </AnimatePresence>
  )
}

export default App
