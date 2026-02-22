import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './ItineraryChat.css'

const SUGGESTIONS = [
  "It's raining — avoid walking, use transit instead",
  "Trains are cancelled today, only walk",
  "I want to spend day 2 walking around",
  "I'd like to visit a museum on day 1",
  "Add a nice rooftop bar on the last evening",
  "My return flight was cancelled",
]

export default function ItineraryChat({ onSend, loading }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  async function handleSend(text) {
    const msg = (text ?? input).trim()
    if (!msg || loading) return

    setMessages((prev) => [...prev, { role: 'user', text: msg }])
    setInput('')

    try {
      const result = await onSend(msg)
      setMessages((prev) => [...prev, { role: 'assistant', text: result.reply }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `⚠️ ${err.message || 'Something went wrong.'}` },
      ])
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="itinchat">
      {/* Toggle button */}
      <button
        className={`itinchat__toggle ${open ? 'itinchat__toggle--open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        title="Chat with AI to modify your itinerary"
      >
        {open ? '✕' : '💬'}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="itinchat__panel"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25 }}
          >
            <div className="itinchat__header">
              <span className="itinchat__header-icon">✨</span>
              <span className="itinchat__header-title">Modify Itinerary</span>
            </div>

            <div className="itinchat__messages">
              {messages.length === 0 && (
                <div className="itinchat__welcome">
                  <p className="itinchat__welcome-text">
                    Tell me what changed and I'll update your itinerary.
                  </p>
                  <div className="itinchat__suggestions">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        className="itinchat__suggestion"
                        onClick={() => handleSend(s)}
                        disabled={loading}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`itinchat__msg itinchat__msg--${m.role}`}>
                  <div className="itinchat__msg-bubble">{m.text}</div>
                </div>
              ))}

              {loading && (
                <div className="itinchat__msg itinchat__msg--assistant">
                  <div className="itinchat__msg-bubble itinchat__msg-bubble--loading">
                    <span className="itinchat__dot" />
                    <span className="itinchat__dot" />
                    <span className="itinchat__dot" />
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            <form
              className="itinchat__input-row"
              onSubmit={(e) => {
                e.preventDefault()
                handleSend()
              }}
            >
              <input
                ref={inputRef}
                className="itinchat__input"
                type="text"
                placeholder={loading ? 'Updating itinerary…' : 'e.g. "It\u2019s raining on day 2"'}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />
              <button
                className="itinchat__send"
                type="submit"
                disabled={!input.trim() || loading}
              >
                ➤
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
