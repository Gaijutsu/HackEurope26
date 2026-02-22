import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API_URL = 'http://localhost:8000'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const [token, setToken] = useState(() => localStorage.getItem('token') || null)
  const [credits, setCredits] = useState(() => {
    try {
      const stored = localStorage.getItem('user')
      const parsed = stored ? JSON.parse(stored) : null
      return parsed?.credits ?? 0
    } catch {
      return 0
    }
  })

  // Persist to localStorage when changed
  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
  }, [token])

  useEffect(() => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    } else {
      localStorage.removeItem('user')
    }
  }, [user])

  const refreshCredits = useCallback(async () => {
    if (!user?.id) return
    try {
      const res = await fetch(`${API_URL}/credits?user_id=${encodeURIComponent(user.id)}`)
      if (res.ok) {
        const data = await res.json()
        setCredits(data.credits)
        // Also update user object so localStorage stays in sync
        setUser((prev) => prev ? { ...prev, credits: data.credits } : prev)
      } else if (res.status === 404) {
        // User no longer exists in DB (e.g. DB was recreated) — force logout
        setToken(null)
        setUser(null)
        setCredits(0)
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    } catch {
      // silently ignore
    }
  }, [user?.id])

  // Refresh credits on mount and when user changes
  useEffect(() => {
    if (user?.id) refreshCredits()
  }, [user?.id, refreshCredits])

  const loginUser = useCallback((authData) => {
    setToken(authData.access_token)
    setUser(authData.user)
    setCredits(authData.user?.credits ?? 0)
  }, [])

  const login = useCallback(async (email, password) => {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'Invalid email or password')
    }
    setToken(data.access_token)
    setUser(data.user)
    setCredits(data.user?.credits ?? 0)
    return data.user
  }, [])

  const register = useCallback(async (name, email, password) => {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed')
    }
    setToken(data.access_token)
    setUser(data.user)
    setCredits(data.user?.credits ?? 0)
    return data.user
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setCredits(0)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }, [])

  const isAuthenticated = !!user && !!token

  return (
    <AuthContext.Provider value={{ user, token, credits, isAuthenticated, loginUser, login, register, logout, refreshCredits }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
