import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './Navbar.css'

export default function Navbar() {
  const { user, credits, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="navbar__inner">
        <NavLink to={isAuthenticated ? '/dashboard' : '/'} className="navbar__logo">
          precise.ly
        </NavLink>

        <div className="navbar__links">
          {isAuthenticated ? (
            <>
              <NavLink to="/dashboard" className="navbar__link">
                My Trips
              </NavLink>
              <NavLink to="/" className="navbar__link">
                New Trip
              </NavLink>
              <button className="navbar__credits" onClick={() => navigate('/credits')}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v12M6 12h12" />
                </svg>
                {credits} credit{credits !== 1 ? 's' : ''}
              </button>
              <div className="navbar__divider" />
              <span className="navbar__user">{user?.name}</span>
              <button className="navbar__logout" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="navbar__link">
                Login
              </NavLink>
              <NavLink to="/register" className="navbar__link navbar__link--cta">
                Sign Up
              </NavLink>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
