import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import MoodBoardCard from '../components/MoodBoardCard'
import CityAutocomplete from '../components/CityAutocomplete'
import LoginBanner from '../components/LoginBanner'
import './Landing.css'

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

const skeletonVariants = {
    pulse: {
        opacity: [0.4, 0.7, 0.4],
        transition: {
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
        },
    },
}

export default function Landing() {
    const [destination, setDestination] = useState('')
    const [selectedCity, setSelectedCity] = useState(null)
    const [cityValid, setCityValid] = useState(false)
    const [searched, setSearched] = useState(false)
    const [isLoadingImages, setIsLoadingImages] = useState(false)
    const [isGeneratingVibe, setIsGeneratingVibe] = useState(false)
    const [moodBoards, setMoodBoards] = useState([])
    // Map of index -> 'upvoted' | 'downvoted' | 'neither'
    const [votes, setVotes] = useState({})
    const navigate = useNavigate()

    const handleDestinationChange = useCallback((val) => {
        setDestination(val)
        // Any manual typing invalidates — must re-select from dropdown
        setCityValid(false)
        setSelectedCity(null)
        // Reset mood boards if destination changes after a search
        if (searched) {
            setSearched(false)
            setMoodBoards([])
        }
    }, [searched])

    const handleCitySelect = useCallback((entry) => {
        setCityValid(true)
        setSelectedCity(entry)
        setDestination(entry.city)
    }, [])

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!destination.trim() || !cityValid || !selectedCity) return

        setSearched(true)
        setIsLoadingImages(true)
        setMoodBoards([])
        setVotes({})

        try {
            const url = `http://localhost:8000/pinterest?city=${encodeURIComponent(selectedCity.city)}&country=${encodeURIComponent(selectedCity.country)}`
            const response = await fetch(url)
            const data = await response.json()
            setMoodBoards(data.map((imageUrl, index) => ({ id: index, image: imageUrl })))
        } catch (error) {
            console.error('Failed to fetch mood boards:', error)
            setMoodBoards([])
        } finally {
            setIsLoadingImages(false)
        }
    }

    const handleUpvote = (id) => {
        setVotes((prev) => ({
            ...prev,
            [id]: prev[id] === 'upvoted' ? 'neither' : 'upvoted',
        }))
    }

    const handleDownvote = (id) => {
        setVotes((prev) => ({
            ...prev,
            [id]: prev[id] === 'downvoted' ? 'neither' : 'downvoted',
        }))
    }

    const getUpvotedCards = () =>
        moodBoards.filter((mood) => votes[mood.id] === 'upvoted')

    const getDownvotedCards = () =>
        moodBoards.filter((mood) => votes[mood.id] === 'downvoted')

    const getVoteState = (id) => votes[id] || 'neither'

    const handleSubmit = async () => {
        const upvotedCards = getUpvotedCards()
        const downvotedCards = getDownvotedCards()

        setIsGeneratingVibe(true)
        let vibe = ''
        try {
            const response = await fetch('http://localhost:8000/vibe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upvoted: upvotedCards.map((m) => m.image),
                    downvoted: downvotedCards.map((m) => m.image),
                }),
            })
            const data = await response.json()
            vibe = data.vibe || ''
        } catch (err) {
            console.error('Failed to generate vibe:', err)
        } finally {
            setIsGeneratingVibe(false)
        }

        const params = new URLSearchParams({ destination })
        if (vibe) params.set('vibe', vibe)
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
            <LoginBanner />

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
                <div className={`landing__search-bar ${isLoadingImages ? 'landing__search-bar--loading' : ''}`}>
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
                        disabled={isLoadingImages}
                    />
                    <button
                        type="submit"
                        className="landing__search-btn"
                        disabled={!cityValid || isLoadingImages}
                    >
                        {isLoadingImages ? (
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
                        {isLoadingImages ? 'Finding your perfect vibes...' : 'Pick the vibe that speaks to you'}
                    </motion.p>
                    <motion.div
                        className="landing__grid"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                    >
                        {isLoadingImages ? (
                            // Skeleton loading cards
                            [...Array(4)].map((_, i) => (
                                <motion.div
                                    key={`skeleton-${i}`}
                                    className="landing__skeleton-card"
                                    variants={skeletonVariants}
                                    animate="pulse"
                                    style={{ animationDelay: `${i * 0.15}s` }}
                                >
                                    <div className="landing__skeleton-shimmer" />
                                    <div className="landing__skeleton-icon">
                                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                                            <rect x="3" y="3" width="18" height="18" rx="2" />
                                            <circle cx="8.5" cy="8.5" r="1.5" />
                                            <path d="M21 15l-5-5L5 21" />
                                        </svg>
                                    </div>
                                </motion.div>
                            ))
                        ) : (
                            moodBoards.map((mood) => (
                                <MoodBoardCard
                                    key={mood.id}
                                    mood={mood}
                                    voteState={getVoteState(mood.id)}
                                    onUpvote={() => handleUpvote(mood.id)}
                                    onDownvote={() => handleDownvote(mood.id)}
                                />
                            ))
                        )}
                    </motion.div>
                    <AnimatePresence>
                        {!isLoadingImages && (
                            <motion.div
                                className="landing__submit-wrap"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 10 }}
                                transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                            >
                                <button
                                    type="button"
                                    className="landing__submit-btn"
                                    onClick={handleSubmit}
                                    disabled={!hasVotes || isGeneratingVibe}
                                >
                                    {isGeneratingVibe ? (
                                        <>
                                            <span className="landing__spinner" />
                                            <span>Reading your vibe...</span>
                                        </>
                                    ) : (
                                        <>
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
                                        </>
                                    )}
                                </button>
                                <button
                                    type="button"
                                    className="landing__skip-btn"
                                    onClick={handleSkipToNext}
                                    disabled={isGeneratingVibe}
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
                        )}
                    </AnimatePresence>
                </motion.section>
            )}
        </motion.div>
    )
}
