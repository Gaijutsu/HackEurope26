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

export default function MoodBoardCard({ mood, onClick }) {
    return (
        <motion.button
            className="mood-card"
            variants={cardVariants}
            whileHover={{ y: -6, scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onClick}
            aria-label={`Select ${mood.title} mood board`}
        >
            <div className="mood-card__image-wrap">
                <img
                    src={mood.image}
                    alt={mood.title}
                    className="mood-card__image"
                    loading="lazy"
                />
                <div className="mood-card__overlay" />
            </div>
            <div className="mood-card__info">
                <h3 className="mood-card__title">{mood.title}</h3>
                <p className="mood-card__subtitle">{mood.subtitle}</p>
            </div>
            <div className="mood-card__select-hint">
                <span>Select this vibe</span>
                <svg
                    width="14"
                    height="14"
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
            </div>
        </motion.button>
    )
}
