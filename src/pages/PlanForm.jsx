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

export default function PlanForm() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const destination = searchParams.get('destination') || 'Your destination'
    const moodId = searchParams.get('mood') || '1'
    const mood = MOOD_DATA[moodId] || MOOD_DATA[1]

    const [form, setForm] = useState({
        startDate: '',
        endDate: '',
        budget: '',
        accommodation: '',
        foodRequirements: '',
        travelers: '1',
        notes: '',
    })

    const [submitted, setSubmitted] = useState(false)

    const handleChange = (e) => {
        const { name, value } = e.target
        setForm((prev) => ({ ...prev, [name]: value }))
    }

    const handleSubmit = (e) => {
        e.preventDefault()
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
                    {/* Dates */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">When are you going?</h2>
                        <div className="plan__row">
                            <div className="plan__field">
                                <label htmlFor="startDate" className="plan__label">Departure</label>
                                <input
                                    id="startDate"
                                    type="date"
                                    name="startDate"
                                    className="plan__input"
                                    value={form.startDate}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                            <div className="plan__field">
                                <label htmlFor="endDate" className="plan__label">Return</label>
                                <input
                                    id="endDate"
                                    type="date"
                                    name="endDate"
                                    className="plan__input"
                                    value={form.endDate}
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                        </div>
                    </div>

                    {/* Budget & Travelers */}
                    <div className="plan__section">
                        <h2 className="plan__section-title">Budget & group</h2>
                        <div className="plan__row">
                            <div className="plan__field">
                                <label htmlFor="budget" className="plan__label">Budget (per person)</label>
                                <div className="plan__input-wrap plan__input-wrap--prefix">
                                    <span className="plan__input-prefix">$</span>
                                    <input
                                        id="budget"
                                        type="number"
                                        name="budget"
                                        className="plan__input plan__input--prefixed"
                                        placeholder="2,000"
                                        value={form.budget}
                                        onChange={handleChange}
                                        min="0"
                                    />
                                </div>
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
                    <div className="plan__section">
                        <h2 className="plan__section-title">Where will you stay?</h2>
                        <div className="plan__chips">
                            {ACCOMMODATION_TYPES.map((type) => (
                                <button
                                    key={type}
                                    type="button"
                                    className={`plan__chip ${form.accommodation === type ? 'plan__chip--active' : ''}`}
                                    onClick={() => setForm((prev) => ({ ...prev, accommodation: type }))}
                                >
                                    {type}
                                </button>
                            ))}
                        </div>
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
