import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import MoodBoardCard from '../components/MoodBoardCard'
import './Landing.css'

const MOOD_BOARDS = [
    {
        id: 1,
        title: 'Café Culture',
        subtitle: 'Cobblestones & croissants',
        image: '/images/mood-european-cafe.png',
        vibe: 'romantic',
    },
    {
        id: 2,
        title: 'Paradise Found',
        subtitle: 'Turquoise waters & sunsets',
        image: '/images/mood-tropical-beach.png',
        vibe: 'tropical',
    },
    {
        id: 3,
        title: 'Alpine Escape',
        subtitle: 'Peaks, lakes & fresh air',
        image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=800&fit=crop&q=80',
        vibe: 'adventure',
    },
    {
        id: 4,
        title: 'City Lights',
        subtitle: 'Neon glow & rooftop views',
        image: 'https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&h=800&fit=crop&q=80',
        vibe: 'urban',
    },
]

const containerVariants = {
    hidden: {},
    visible: {
        transition: {
            staggerChildren: 0.12,
            delayChildren: 0.2,
        },
    },
}

const pageVariants = {
    initial: { opacity: 0, y: 20 },
    animate: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.6,
            ease: [0.4, 0, 0.2, 1],
        },
    },
    exit: {
        opacity: 0,
        y: -30,
        transition: {
            duration: 0.4,
            ease: [0.4, 0, 0.2, 1],
        },
    },
}

export default function Landing() {
    const [destination, setDestination] = useState('')
    const [searched, setSearched] = useState(false)
    const [isSearching, setIsSearching] = useState(false)
    const navigate = useNavigate()

    const handleSearch = (e) => {
        e.preventDefault()
        if (!destination.trim()) return
        setIsSearching(true)
        // Simulate search delay for smooth animation
        setTimeout(() => {
            setIsSearching(false)
            setSearched(true)
        }, 800)
    }

    const handleSelectMood = (mood) => {
        navigate(`/plan?destination=${encodeURIComponent(destination)}&mood=${mood.id}&vibe=${mood.vibe}`)
    }

    return (
        <motion.div
            className="landing"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
        >
            {/* Decorative background elements */}
            <div className="landing__bg-orb landing__bg-orb--1" />
            <div className="landing__bg-orb landing__bg-orb--2" />
            <div className="landing__bg-orb landing__bg-orb--3" />

            <header className="landing__header">
                <motion.h1
                    className="landing__logo"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.1, ease: [0.4, 0, 0.2, 1] }}
                >
                    precise.ly
                </motion.h1>
                <motion.p
                    className="landing__tagline"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.3, ease: [0.4, 0, 0.2, 1] }}
                >
                    Travel, curated to your vibe.
                </motion.p>
            </header>

            <motion.form
                className="landing__search"
                onSubmit={handleSearch}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.7, delay: 0.5, ease: [0.4, 0, 0.2, 1] }}
            >
                <div className={`landing__search-bar ${isSearching ? 'landing__search-bar--loading' : ''}`}>
                    <svg
                        className="landing__search-icon"
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.35-4.35" />
                    </svg>
                    <input
                        id="destination-input"
                        type="text"
                        className="landing__input"
                        placeholder="Where do you want to go?"
                        value={destination}
                        onChange={(e) => setDestination(e.target.value)}
                        autoComplete="off"
                    />
                    <button
                        type="submit"
                        className="landing__search-btn"
                        disabled={!destination.trim() || isSearching}
                    >
                        {isSearching ? (
                            <span className="landing__spinner" />
                        ) : (
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
                        )}
                    </button>
                </div>
            </motion.form>

            <AnimatePresence>
                {searched && (
                    <motion.section
                        className="landing__results"
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
                    >
                        <motion.p
                            className="landing__results-label"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.1 }}
                        >
                            Pick the vibe that speaks to you
                        </motion.p>
                        <motion.div
                            className="landing__grid"
                            variants={containerVariants}
                            initial="hidden"
                            animate="visible"
                        >
                            {MOOD_BOARDS.map((mood) => (
                                <MoodBoardCard
                                    key={mood.id}
                                    mood={mood}
                                    onClick={() => handleSelectMood(mood)}
                                />
                            ))}
                        </motion.div>
                    </motion.section>
                )}
            </AnimatePresence>

            <footer className="landing__footer">
                <p>© 2026 precise.ly — Travel, curated.</p>
            </footer>
        </motion.div>
    )
}
