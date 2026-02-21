import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import './PlanForm.css'

const MOOD_DATA = {
    1: { title: 'Café Culture', vibe: 'romantic', image: '/images/mood-european-cafe.png' },
    2: { title: 'Paradise Found', vibe: 'tropical', image: '/images/mood-tropical-beach.png' },
    3: { title: 'Alpine Escape', vibe: 'adventure', image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=400&fit=crop&q=80' },
    4: { title: 'City Lights', vibe: 'urban', image: 'https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&h=400&fit=crop&q=80' },
}

const ACCOMMODATION_TYPES = ['Hotel', 'Hostel', 'Airbnb', 'Resort', 'Camping', 'Boutique Stay']
const FOOD_OPTIONS = ['No restrictions', 'Vegetarian', 'Vegan', 'Gluten-free', 'Halal', 'Kosher']

const pageVariants = {
    initial: { opacity: 0, y: 40 },
    animate: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.6,
            ease: [0.4, 0, 0.2, 1],
            staggerChildren: 0.08,
            delayChildren: 0.2,
        },
    },
    exit: {
        opacity: 0,
        y: -20,
        transition: { duration: 0.3 },
    },
}

const itemVariants = {
    initial: { opacity: 0, y: 20 },
    animate: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
    },
}

function buildVibeText(upvotedIds, downvotedIds) {
    const parts = []
    const upVibes = upvotedIds.map((id) => MOOD_DATA[id]?.vibe).filter(Boolean)
    const downVibes = downvotedIds.map((id) => MOOD_DATA[id]?.vibe).filter(Boolean)
    if (upVibes.length) parts.push(`I love: ${upVibes.join(', ')}`)
    if (downVibes.length) parts.push(`Not for me: ${downVibes.join(', ')}`)
    return parts.join('. ')
}

export default function PlanForm() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const destination = searchParams.get('destination') || 'Your destination'
    const moodId = searchParams.get('mood') || '1'
    const mood = MOOD_DATA[moodId] || MOOD_DATA[1]

    // Build initial vibe from URL params (populated by "Continue with your vibes")
    const upvotedParam = searchParams.get('upvoted') || ''
    const downvotedParam = searchParams.get('downvoted') || ''
    const upvotedIds = upvotedParam ? upvotedParam.split(',').filter(Boolean) : []
    const downvotedIds = downvotedParam ? downvotedParam.split(',').filter(Boolean) : []
    const initialVibe = buildVibeText(upvotedIds, downvotedIds)

    const today = new Date().toISOString().split('T')[0]

    const [form, setForm] = useState({
        vibe: initialVibe,
        startDate: '',
        endDate: '',
        budget: '',
        accommodation: '',
        foodRequirements: '',
        travelers: '1',
        notes: '',
    })

    const [submitted, setSubmitted] = useState(false)
    const [errors, setErrors] = useState({})

    const handleChange = (e) => {
        const { name, value } = e.target
        setForm((prev) => {
            const next = { ...prev, [name]: value }
            // If departure date is changed to be after the current return date,
            // or if return date is not set, sync return date to departure
            if (name === 'startDate') {
                if (!prev.endDate || value > prev.endDate) {
                    next.endDate = value
                }
            }
            return next
        })
        // Clear error when user types
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }))
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()

        const newErrors = {}
        if (!form.vibe.trim()) newErrors.vibe = 'Please describe your vibe'
        if (!form.budget) newErrors.budget = 'Please enter your budget'
        if (!form.accommodation) newErrors.accommodation = 'Please select where you will stay'

        if (!form.startDate) {
            newErrors.startDate = 'Please select a departure date'
        } else if (form.startDate < today) {
            newErrors.startDate = 'Departure date cannot be in the past'
        }

        if (!form.endDate) {
            newErrors.endDate = 'Please select a return date'
        } else if (form.endDate < form.startDate) {
            newErrors.endDate = 'Return date cannot be before departure'
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors)
            // Scroll to first error
            const firstError = Object.keys(newErrors)[0]
            document.getElementById(firstError)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            return
        }

        setSubmitted(true)
    }

    return (
        <motion.div
            className="plan"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
        >
            {/* Decorative orbs */}
            <div className="plan__bg-orb plan__bg-orb--1" />
            <div className="plan__bg-orb plan__bg-orb--2" />

            {/* Back navigation */}
            <motion.button
                className="plan__back"
                onClick={() => navigate('/')}
                variants={itemVariants}
                whileHover={{ x: -4 }}
                whileTap={{ scale: 0.97 }}
            >
                <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <path d="m12 19-7-7 7-7" />
                    <path d="M19 12H5" />
                </svg>
                <span>Back to vibes</span>
            </motion.button>

            {/* Header with mood context */}
            <motion.header className="plan__header" variants={itemVariants}>
                <div className="plan__mood-preview">
                    <img src={mood.image} alt={mood.title} className="plan__mood-image" />
                    <div className="plan__mood-info">
                        <span className="plan__mood-badge">{mood.vibe}</span>
                        <h1 className="plan__title">
                            Plan your trip to <span className="plan__destination">{destination}</span>
                        </h1>
                        <p className="plan__subtitle">
                            Let's dial in the details — we'll craft the perfect itinerary for your {mood.title.toLowerCase()} adventure.
                        </p>
                    </div>
                </div>
            </motion.header>

            {/* Form */}
            {!submitted ? (
                <motion.form className="plan__form" onSubmit={handleSubmit} variants={itemVariants}>
                    {/* Vibe */}
                    <div className="plan__section">
                        <div className="plan__label-row">
                            <h2 className="plan__section-title">Your vibe</h2>
                            <span className="plan__required-tag">required</span>
                        </div>
                        <input
                            id="vibe"
                            type="text"
                            name="vibe"
                            className={`plan__input ${errors.vibe ? 'plan__input--error' : ''}`}
                            placeholder="Describe the vibe you're looking for..."
                            value={form.vibe}
                            onChange={handleChange}
                        />
                        {errors.vibe && <span className="plan__error-text">{errors.vibe}</span>}
                    </div>

                    {/* Dates */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">When are you going?</h2>
                        <div className="plan__row">
                            <div className="plan__field">
                                <div className="plan__label-row">
                                    <label htmlFor="startDate" className="plan__label">Departure</label>
                                    <span className="plan__required-tag">required</span>
                                </div>
                                <input
                                    id="startDate"
                                    type="date"
                                    name="startDate"
                                    className={`plan__input ${errors.startDate ? 'plan__input--error' : ''}`}
                                    value={form.startDate}
                                    onChange={handleChange}
                                    min={today}
                                    required
                                />
                                {errors.startDate && <span className="plan__error-text">{errors.startDate}</span>}
                            </div>
                            <div className="plan__field">
                                <div className="plan__label-row">
                                    <label htmlFor="endDate" className="plan__label">Return</label>
                                    <span className="plan__required-tag">required</span>
                                </div>
                                <input
                                    id="endDate"
                                    type="date"
                                    name="endDate"
                                    className={`plan__input ${errors.endDate ? 'plan__input--error' : ''}`}
                                    value={form.endDate}
                                    onChange={handleChange}
                                    min={form.startDate || today}
                                    required
                                />
                                {errors.endDate && <span className="plan__error-text">{errors.endDate}</span>}
                            </div>
                        </div>
                    </div>

                    {/* Budget & Travelers */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">Budget & group</h2>
                        <div className="plan__row">
                            <div className="plan__field">
                                <div className="plan__label-row">
                                    <label htmlFor="budget" className="plan__label">Budget (per person)</label>
                                    <span className="plan__required-tag">required</span>
                                </div>
                                <div className="plan__input-wrap plan__input-wrap--prefix">
                                    <span className="plan__input-prefix">$</span>
                                    <input
                                        id="budget"
                                        type="number"
                                        name="budget"
                                        className={`plan__input plan__input--prefixed ${errors.budget ? 'plan__input--error' : ''}`}
                                        placeholder="2,000"
                                        value={form.budget}
                                        onChange={handleChange}
                                        min="0"
                                    />
                                </div>
                                {errors.budget && <span className="plan__error-text">{errors.budget}</span>}
                            </div>
                            <div className="plan__field">
                                <label htmlFor="travelers" className="plan__label">Travelers</label>
                                <select
                                    id="travelers"
                                    name="travelers"
                                    className="plan__input plan__select"
                                    value={form.travelers}
                                    onChange={handleChange}
                                >
                                    {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                                        <option key={n} value={n}>{n} {n === 1 ? 'person' : 'people'}</option>
                                    ))}
                                    <option value="9+">9+ people</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Accommodation */}
                    <div className="plan__section" id="accommodation">
                        <div className="plan__label-row">
                            <h2 className="plan__section-title">Where will you stay?</h2>
                            <span className="plan__required-tag">required</span>
                        </div>
                        <div className="plan__chips">
                            {ACCOMMODATION_TYPES.map((type) => (
                                <button
                                    key={type}
                                    type="button"
                                    className={`plan__chip ${form.accommodation === type ? 'plan__chip--active' : ''} ${errors.accommodation ? 'plan__chip--error' : ''}`}
                                    onClick={() => {
                                        setForm((prev) => ({ ...prev, accommodation: type }))
                                        if (errors.accommodation) setErrors(prev => ({ ...prev, accommodation: '' }))
                                    }}
                                >
                                    {type}
                                </button>
                            ))}
                        </div>
                        {errors.accommodation && <span className="plan__error-text">{errors.accommodation}</span>}
                    </div>

                    {/* Food */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">Dietary needs?</h2>
                        <div className="plan__chips">
                            {FOOD_OPTIONS.map((opt) => (
                                <button
                                    key={opt}
                                    type="button"
                                    className={`plan__chip ${form.foodRequirements === opt ? 'plan__chip--active' : ''}`}
                                    onClick={() => setForm((prev) => ({ ...prev, foodRequirements: opt }))}
                                >
                                    {opt}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Notes */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">Anything else?</h2>
                        <textarea
                            id="notes"
                            name="notes"
                            className="plan__input plan__textarea"
                            placeholder="Special requests, must-see spots, travel style preferences..."
                            value={form.notes}
                            onChange={handleChange}
                            rows={4}
                        />
                    </div>

                    {/* Submit */}
                    <motion.button
                        type="submit"
                        className="plan__submit"
                        whileHover={{ scale: 1.02, y: -2 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <span>Craft my itinerary</span>
                        <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M5 12h14" />
                            <path d="m12 5 7 7-7 7" />
                        </svg>
                    </motion.button>
                </motion.form>
            ) : (
                <motion.div
                    className="plan__success"
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
                >
                    <div className="plan__success-icon">✨</div>
                    <h2 className="plan__success-title">You're all set!</h2>
                    <p className="plan__success-text">
                        We're crafting the perfect {mood.title.toLowerCase()} itinerary for your trip to {destination}.
                        Sit tight — magic takes a moment.
                    </p>
                    <motion.button
                        className="plan__submit plan__submit--secondary"
                        onClick={() => navigate('/')}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <span>Plan another trip</span>
                    </motion.button>
                </motion.div>
            )}
        </motion.div>
    )
}
