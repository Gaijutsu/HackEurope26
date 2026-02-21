import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './Navbar.css'

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
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
