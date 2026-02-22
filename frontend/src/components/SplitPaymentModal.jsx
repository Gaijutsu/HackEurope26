import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import * as api from '../api'
import './SplitPaymentModal.css'

export default function SplitPaymentModal({
  isOpen,
  onClose,
  tripId,
  userId,
  itemType,
  itemId,
  itemName,
  totalCost,
  numTravelers,
  currency = 'USD',
  onSuccess,
}) {
  const [payerNames, setPayerNames] = useState(() => 
    Array(numTravelers).fill('').map((_, i) => `Traveler ${i + 1}`)
  )
  const [loading, setLoading] = useState(false)
  const [splits, setSplits] = useState(null)
  const [error, setError] = useState('')

  // Re-sync payer names when numTravelers changes (trip loads async)
  useEffect(() => {
    setPayerNames(prev => {
      if (prev.length === numTravelers) return prev
      return Array(numTravelers).fill('').map((_, i) =>
        i < prev.length ? prev[i] : `Traveler ${i + 1}`
      )
    })
  }, [numTravelers])

  // Reset state when modal reopens
  useEffect(() => {
    if (isOpen) {
      setSplits(null)
      setError('')
    }
  }, [isOpen])

  const shareAmount = totalCost ? (totalCost / numTravelers).toFixed(2) : '0.00'

  async function handleCreateSplits() {
    if (payerNames.some(name => !name.trim())) {
      setError('Please enter names for all travelers')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const result = await api.createSplitPayments(tripId, userId, {
        itemType,
        itemId,
        payerNames: payerNames.map(n => n.trim()),
      })
      if (result.warning && !result.splits) {
        setError(result.warning)
      } else {
        setSplits(result)
        onSuccess?.()
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function copyLink(url) {
    navigator.clipboard.writeText(url)
    alert('Payment link copied to clipboard!')
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        className="split-modal-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="split-modal"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="split-modal__close" onClick={onClose}>×</button>
          
          <h2 className="split-modal__title">💰 Split Payment</h2>
          <p className="split-modal__subtitle">{itemName}</p>
          
          <div className="split-modal__summary">
            <div className="split-summary__row">
              <span>Total Cost:</span>
              <strong>{currency} {totalCost?.toFixed(2)}</strong>
            </div>
            <div className="split-summary__row">
              <span>Travelers:</span>
              <strong>{numTravelers}</strong>
            </div>
            <div className="split-summary__row split-summary__row--highlight">
              <span>Each pays:</span>
              <strong>{currency} {shareAmount}</strong>
            </div>
          </div>

          {!splits ? (
            <>
              <h3 className="split-modal__section-title">Enter Traveler Names</h3>
              <div className="split-modal__names">
                {payerNames.map((name, i) => (
                  <div key={i} className="split-name__row">
                    <label>Person {i + 1}</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => {
                        const newNames = [...payerNames]
                        newNames[i] = e.target.value
                        setPayerNames(newNames)
                      }}
                      placeholder={`Traveler ${i + 1}`}
                    />
                  </div>
                ))}
              </div>

              {error && <p className="split-modal__error">{error}</p>}

              <button
                className="split-modal__btn split-modal__btn--primary"
                onClick={handleCreateSplits}
                disabled={loading}
              >
                {loading ? 'Creating payment links...' : 'Generate Payment Links'}
              </button>
            </>
          ) : (
            <div className="split-modal__links">
              <h3 className="split-modal__section-title">Share These Links</h3>
              <p className="split-modal__hint">
                Each person can pay their share using their unique link:
              </p>
              
              <div className="split-links__list">
                {splits.splits?.map((split, i) => (
                  <div key={i} className="split-link__item">
                    <div className="split-link__info">
                      <strong>{split.payer_name}</strong>
                      <span className={`split-link__status split-link__status--${split.status}`}>
                        {split.status}
                      </span>
                    </div>
                    <div className="split-link__amount">
                      {currency} {split.share_amount}
                    </div>
                    {split.checkout_url ? (
                      <button
                        className="split-link__copy-btn"
                        onClick={() => copyLink(split.checkout_url)}
                      >
                        Copy Link
                      </button>
                    ) : split.status === 'paid' ? (
                      <span className="split-link__paid">✓ Paid</span>
                    ) : (
                      <span className="split-link__offline">Offline mode</span>
                    )}
                  </div>
                ))}
              </div>

              <button
                className="split-modal__btn split-modal__btn--secondary"
                onClick={() => setSplits(null)}
              >
                Start Over
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
