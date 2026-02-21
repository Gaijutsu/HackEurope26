import { motion } from 'framer-motion'
import './MoodBoardCard.css'

const cardVariants = {
    hidden: {
        opacity: 0,
        y: 30,
        scale: 0.95,
    },
    visible: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: {
            duration: 0.5,
            ease: [0.4, 0, 0.2, 1],
        },
    },
}

export default function MoodBoardCard({ mood, voteState, onUpvote, onDownvote, onClick, initial = "hidden", animate = "visible" }) {
    return (
        <motion.div
            className="mood-card"
            variants={cardVariants}
            initial={initial}
            animate={animate}
            whileHover={{ y: -6, scale: 1.02 }}
            aria-label={`Mood board ${mood.id}`}
        >
            <div className="mood-card__image-wrap">
                <img
                    src={mood.image}
                    alt={`Mood ${mood.id}`}
                    className="mood-card__image"
                    loading="lazy"
                />
                <div className="mood-card__overlay" />
            </div>
            <div className="mood-card__votes">
                <button
                    className={`mood-card__vote-btn mood-card__vote-btn--up ${voteState === 'upvoted' ? 'mood-card__vote-btn--active' : ''}`}
                    onClick={(e) => {
                        e.stopPropagation()
                        onUpvote()
                    }}
                    aria-label="Upvote"
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m18 15-6-6-6 6" />
                    </svg>
                </button>
                <button
                    className={`mood-card__vote-btn mood-card__vote-btn--down ${voteState === 'downvoted' ? 'mood-card__vote-btn--down-active' : ''}`}
                    onClick={(e) => {
                        e.stopPropagation()
                        onDownvote()
                    }}
                    aria-label="Downvote"
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m6 9 6 6 6-6" />
                    </svg>
                </button>
            </div>
        </motion.div>
    )
}
