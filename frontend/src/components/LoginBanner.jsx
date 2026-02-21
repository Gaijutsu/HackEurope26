import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import './LoginBanner.css'

const overlayVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, transition: { duration: 0.15 } },
}

const modalVariants = {
    hidden: { opacity: 0, y: -12, scale: 0.97 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] } },
    exit: { opacity: 0, y: -8, scale: 0.97, transition: { duration: 0.18, ease: [0.4, 0, 0.2, 1] } },
}

function LoginForm({ onSuccess }) {
    const { login } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!email || !password) { setError('Please fill in all fields'); return }
        setLoading(true)
        setError('')
        try {
            await login(email, password)
            onSuccess()
        } catch (err) {
            setError(err.message || 'Login failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <form className="login-modal__form" onSubmit={handleSubmit}>
            <div className="login-modal__field">
                <label className="login-modal__label">Email</label>
                <div className="login-modal__input-wrap">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                    <input
                        className="login-modal__input"
                        type="email"
                        placeholder="your@email.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                    />
                </div>
            </div>

            <div className="login-modal__field">
                <label className="login-modal__label">Password</label>
                <div className="login-modal__input-wrap">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <input
                        className="login-modal__input"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                    />
                </div>
            </div>

            {error && <p className="login-modal__error">{error}</p>}

            <button className="login-modal__submit" type="submit" disabled={loading}>
                {loading ? <span className="login-modal__spinner" /> : 'Sign in'}
            </button>
        </form>
    )
}

function RegisterForm({ onSuccess }) {
    const { register } = useAuth()
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!name || !email || !password) { setError('Please fill in all fields'); return }
        setLoading(true)
        setError('')
        try {
            await register(name, email, password)
            onSuccess()
        } catch (err) {
            setError(err.message || 'Registration failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <form className="login-modal__form" onSubmit={handleSubmit}>
            <div className="login-modal__field">
                <label className="login-modal__label">Name</label>
                <div className="login-modal__input-wrap">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="8" r="4" />
                        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                    </svg>
                    <input
                        className="login-modal__input"
                        type="text"
                        placeholder="Jane Doe"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        autoComplete="name"
                    />
                </div>
            </div>

            <div className="login-modal__field">
                <label className="login-modal__label">Email</label>
                <div className="login-modal__input-wrap">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                    <input
                        className="login-modal__input"
                        type="email"
                        placeholder="jane@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                    />
                </div>
            </div>

            <div className="login-modal__field">
                <label className="login-modal__label">Password</label>
                <div className="login-modal__input-wrap">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <input
                        className="login-modal__input"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="new-password"
                    />
                </div>
            </div>

            {error && <p className="login-modal__error">{error}</p>}

            <button className="login-modal__submit" type="submit" disabled={loading}>
                {loading ? <span className="login-modal__spinner" /> : 'Create account'}
            </button>
        </form>
    )
}

export default function LoginBanner() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const [open, setOpen] = useState(false)
    const [tab, setTab] = useState('login') // 'login' | 'register'

    const close = () => setOpen(false)

    return (
        <>
            <div className="login-banner">
                {user ? (
                    <div className="login-banner__user">
                        <span>
                            ✈️ Hi, <span className="login-banner__user-name">{user.name}</span>
                        </span>
                        <div className="login-banner__nav">
                            <button className="login-banner__nav-btn" onClick={() => navigate('/dashboard')}>
                                My Trips
                            </button>
                            <button className="login-banner__nav-btn" onClick={() => navigate('/')}>
                                New Trip
                            </button>
                        </div>
                        <button className="login-banner__logout-btn" onClick={logout}>
                            Sign out
                        </button>
                    </div>
                ) : (
                    <button
                        className="login-banner__trigger"
                        onClick={() => { setTab('login'); setOpen(true) }}
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="8" r="4" />
                            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                        </svg>
                        Sign in to save your trips
                    </button>
                )}
            </div>

            <AnimatePresence>
                {open && (
                    <motion.div
                        className="login-modal-overlay"
                        variants={overlayVariants}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        onClick={(e) => { if (e.target === e.currentTarget) close() }}
                    >
                        <motion.div
                            className="login-modal"
                            variants={modalVariants}
                            initial="hidden"
                            animate="visible"
                            exit="exit"
                        >
                            {/* Close */}
                            <button className="login-modal__close" onClick={close} aria-label="Close">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M18 6 6 18M6 6l12 12" />
                                </svg>
                            </button>

                            {/* Tabs */}
                            <div className="login-modal__tabs">
                                <button
                                    className={`login-modal__tab${tab === 'login' ? ' login-modal__tab--active' : ''}`}
                                    onClick={() => setTab('login')}
                                >
                                    Sign in
                                </button>
                                <button
                                    className={`login-modal__tab${tab === 'register' ? ' login-modal__tab--active' : ''}`}
                                    onClick={() => setTab('register')}
                                >
                                    Register
                                </button>
                            </div>

                            {/* Form */}
                            {tab === 'login' ? (
                                <>
                                    <LoginForm onSuccess={close} />
                                    <p className="login-modal__switch">
                                        Don't have an account?
                                        <button onClick={() => setTab('register')}>Register</button>
                                    </p>
                                </>
                            ) : (
                                <>
                                    <RegisterForm onSuccess={close} />
                                    <p className="login-modal__switch">
                                        Already have an account?
                                        <button onClick={() => setTab('login')}>Sign in</button>
                                    </p>
                                </>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    )
}
