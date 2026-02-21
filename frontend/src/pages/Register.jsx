import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'
import './Auth.css'

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
}

export default function Register() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { loginUser } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name || !email || !password) {
      setError('Please fill in all fields')
      return
    }

    setLoading(true)
    setError('')

    try {
      const data = await api.register(name, email, password)
      loginUser(data)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      className="auth"
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <div className="auth__bg-orb auth__bg-orb--1" />
      <div className="auth__bg-orb auth__bg-orb--2" />

      <div className="auth__card">
        <div className="auth__header">
          <Link to="/" className="auth__logo">precise.ly</Link>
          <h1 className="auth__title">Create account</h1>
          <p className="auth__subtitle">Start planning your dream trips</p>
        </div>

        <form className="auth__form" onSubmit={handleSubmit}>
          {error && <div className="auth__error">{error}</div>}

          <div className="auth__field">
            <label htmlFor="name" className="auth__label">Name</label>
            <input
              id="name"
              type="text"
              className="auth__input"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          </div>

          <div className="auth__field">
            <label htmlFor="email" className="auth__label">Email</label>
            <input
              id="email"
              type="email"
              className="auth__input"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="auth__field">
            <label htmlFor="password" className="auth__label">Password</label>
            <input
              id="password"
              type="password"
              className="auth__input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>

          <motion.button
            type="submit"
            className="auth__submit"
            disabled={loading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? <span className="auth__spinner" /> : 'Create account'}
          </motion.button>
        </form>

        <div className="auth__footer">
          <p>Already have an account? <Link to="/login" className="auth__link">Sign in</Link></p>
        </div>
      </div>
    </motion.div>
  )
}
