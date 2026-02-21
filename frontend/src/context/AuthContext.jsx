import { createContext, useContext, useState, useCallback } from 'react'

const API_URL = 'http://localhost:8000'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        try {
            const stored = localStorage.getItem('auth_user')
            return stored ? JSON.parse(stored) : null
        } catch {
            return null
        }
    })
    const [token, setToken] = useState(() => localStorage.getItem('auth_token') || null)

    const _persist = (userData, tokenData) => {
        setUser(userData)
        setToken(tokenData)
        if (userData && tokenData) {
            localStorage.setItem('auth_user', JSON.stringify(userData))
            localStorage.setItem('auth_token', tokenData)
        } else {
            localStorage.removeItem('auth_user')
            localStorage.removeItem('auth_token')
        }
    }

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
        _persist(data.user, data.access_token)
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
        _persist(data.user, data.access_token)
        return data.user
    }, [])

    const logout = useCallback(() => {
        _persist(null, null)
    }, [])

    return (
        <AuthContext.Provider value={{ user, token, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
}
