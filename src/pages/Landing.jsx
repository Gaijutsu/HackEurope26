import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import MoodBoardCard from '../components/MoodBoardCard'
import CityAutocomplete from '../components/CityAutocomplete'
import './Landing.css'

const MOOD_BOARDS = [
    {
        id: 1,
        image: '/images/mood-european-cafe.png',
    },
    {
        id: 2,
        image: '/images/mood-tropical-beach.png',
    },
    {
        id: 3,
        image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=800&fit=crop&q=80',
    },
    {
        id: 4,
        image: 'https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&h=800&fit=crop&q=80',
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
    const [cityValid, setCityValid] = useState(false)
    const [searched, setSearched] = useState(false)
    const [isSearching, setIsSearching] = useState(false)
    // Map of mood.id -> 'upvoted' | 'downvoted' | 'neither'
    const [votes, setVotes] = useState({})
    const navigate = useNavigate()

    const handleDestinationChange = useCallback((val) => {
        setDestination(val)
        // Any manual typing invalidates — must re-select from dropdown
        setCityValid(false)
        // Reset mood boards if destination changes after a search
        if (searched) setSearched(false)
    }, [searched])

    const handleCitySelect = useCallback((entry) => {
        setCityValid(true)
        setDestination(entry.city)
    }, [])

    const handleSearch = (e) => {
        e.preventDefault()
        if (!destination.trim() || !cityValid) return
        setIsSearching(true)
        setTimeout(() => {
            setIsSearching(false)
            setSearched(true)
        }, 800)
    }

    const handleUpvote = (mood) => {
        setVotes((prev) => ({
            ...prev,
            [mood.id]: prev[mood.id] === 'upvoted' ? 'neither' : 'upvoted',
        }))
    }

    const handleDownvote = (mood) => {
        setVotes((prev) => ({
            ...prev,
            [mood.id]: prev[mood.id] === 'downvoted' ? 'neither' : 'downvoted',
        }))
    }

    const getUpvotedCards = () =>
        MOOD_BOARDS.filter((m) => votes[m.id] === 'upvoted')

    const getDownvotedCards = () =>
        MOOD_BOARDS.filter((m) => votes[m.id] === 'downvoted')

    const getVoteState = (mood) => votes[mood.id] || 'neither'

    const handleSubmit = () => {
        const upvoted = getUpvotedCards().map((m) => m.id)
        const downvoted = getDownvotedCards().map((m) => m.id)
        const params = new URLSearchParams({ destination })
        if (upvoted.length) params.set('upvoted', upvoted.join(','))
        if (downvoted.length) params.set('downvoted', downvoted.join(','))
        navigate(`/plan?${params.toString()}`)
    }

    const handleSkipToNext = () => {
        navigate(`/plan?destination=${encodeURIComponent(destination)}`)
    }

    const hasVotes = Object.values(votes).some((v) => v !== 'neither')

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
                    <CityAutocomplete
                        value={destination}
                        onChange={handleDestinationChange}
                        onValidSelect={handleCitySelect}
                        disabled={isSearching}
                    />
                    <button
                        type="submit"
                        className="landing__search-btn"
                        disabled={!cityValid || isSearching}
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
                                    voteState={getVoteState(mood)}
                                    onUpvote={() => handleUpvote(mood)}
                                    onDownvote={() => handleDownvote(mood)}
                                />
                            ))}
                        </motion.div>
                        <motion.div
                            className="landing__submit-wrap"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                        >
                            <button
                                type="button"
                                className="landing__submit-btn"
                                onClick={handleSubmit}
                                disabled={!hasVotes}
                            >
                                <span>Continue with your vibes</span>
                                <svg
                                    width="20"
                                    height="20"
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
                            </button>
                            <button
                                type="button"
                                className="landing__skip-btn"
                                onClick={handleSkipToNext}
                            >
                                <span>I already know my vibe</span>
                                <svg
                                    width="20"
                                    height="20"
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
                            </button>
                        </motion.div>
                    </motion.section>
                )}
            </AnimatePresence>


        </motion.div>
    )
}
