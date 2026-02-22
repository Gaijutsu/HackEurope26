import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import Navbar from '../components/Navbar'
import * as api from '../api'
import './BuyCredits.css'

const PACKAGES = [
  { id: '1', credits: 1, price: '$1.99', perCredit: '$1.99', label: '1 Trip Credit' },
  { id: '5', credits: 5, price: '$7.99', perCredit: '$1.60', label: '5 Trip Credits', popular: true },
  { id: '10', credits: 10, price: '$11.99', perCredit: '$1.20', label: '10 Trip Credits', best: true },
]

const pageVariants = {
  initial: { opacity: 0, y: 30 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  },
}

export default function BuyCredits() {
  const { user, credits, refreshCredits, isAuthenticated } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(null) // which package is loading
  const [successMessage, setSuccessMessage] = useState('')

  // Handle redirect back from Stripe
  useEffect(() => {
    const sessionId = searchParams.get('session_id')
    if (sessionId && user?.id) {
      // Call the success endpoint which verifies the session with Stripe and grants credits
      api.verifyCheckoutSuccess(user.id, sessionId).then((data) => {
        refreshCredits()
        setSuccessMessage('Payment successful! Your credits have been added.')
      }).catch(() => {
        refreshCredits()
      })
    }
  }, [searchParams, user?.id, refreshCredits])

  if (!isAuthenticated) {
    return (
      <>
        <Navbar />
        <div className="credits-page">
          <div className="credits-page__container">
            <h1 className="credits-page__title">Trip Credits</h1>
            <p className="credits-page__subtitle">Please log in to purchase trip credits.</p>
            <button className="credits-page__login-btn" onClick={() => navigate('/login')}>
              Log in
            </button>
          </div>
        </div>
      </>
    )
  }

  const handlePurchase = async (packageId) => {
    setLoading(packageId)
    try {
      const result = await api.createCheckoutSession(user.id, packageId)
      if (result.fallback) {
        // Stripe not configured — credits granted directly
        await refreshCredits()
        setSuccessMessage(`Credits added! You now have ${result.credits} credits.`)
      } else if (result.url) {
        // Redirect to Stripe Checkout
        window.location.href = result.url
      }
    } catch (err) {
      console.error('Checkout failed:', err)
      alert(err.message || 'Failed to start checkout')
    } finally {
      setLoading(null)
    }
  }

  return (
    <>
      <Navbar />
      <motion.div
        className="credits-page"
        variants={pageVariants}
        initial="initial"
        animate="animate"
      >
        <div className="credits-page__container">
          <div className="credits-page__header">
            <h1 className="credits-page__title">Trip Credits</h1>
            <p className="credits-page__subtitle">
              Each credit lets you plan one AI-powered trip itinerary
            </p>
            <div className="credits-page__balance">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v12M6 12h12" />
              </svg>
              <span className="credits-page__balance-count">{credits}</span>
              <span className="credits-page__balance-label">credit{credits !== 1 ? 's' : ''} remaining</span>
            </div>
          </div>

          {successMessage && (
            <motion.div
              className="credits-page__success"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
              {successMessage}
            </motion.div>
          )}

          <div className="credits-page__grid">
            {PACKAGES.map((pkg) => (
              <motion.div
                key={pkg.id}
                className={`credits-card${pkg.popular ? ' credits-card--popular' : ''}${pkg.best ? ' credits-card--best' : ''}`}
                whileHover={{ y: -4, boxShadow: '0 12px 40px rgba(0,0,0,0.08)' }}
                transition={{ duration: 0.2 }}
              >
                {pkg.popular && <span className="credits-card__badge">Most Popular</span>}
                {pkg.best && <span className="credits-card__badge credits-card__badge--best">Best Value</span>}
                <div className="credits-card__credits">{pkg.credits}</div>
                <div className="credits-card__label">
                  trip credit{pkg.credits > 1 ? 's' : ''}
                </div>
                <div className="credits-card__price">{pkg.price}</div>
                <div className="credits-card__per-credit">{pkg.perCredit} / credit</div>
                <button
                  className="credits-card__btn"
                  onClick={() => handlePurchase(pkg.id)}
                  disabled={loading !== null}
                >
                  {loading === pkg.id ? (
                    <span className="credits-card__spinner" />
                  ) : (
                    'Purchase'
                  )}
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </>
  )
}
