import React, { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) { setLoading(false); return }
    api.get('/api/auth/me')
      .then(({ data }) => setUser(data.user))
      .catch(() => { localStorage.removeItem('auth_token') })
      .finally(() => setLoading(false))
  }, [])

  const login = async (identifier, password, companyId = null) => {
    const payload = { username: identifier, password }
    if (companyId) payload.company_id = companyId

    const { data } = await api.post('/api/auth/login', payload)
    if (data.needs_company_selection) {
      return data
    }

    localStorage.setItem('auth_token', data.token)
    setUser(data.user)
    return data
  }

  // New function for source database logins - uses token directly
  const loginWithSourceToken = async (token, userData) => {
    localStorage.setItem('auth_token', token)
    setUser(userData)
    return { success: true, token, user: userData }
  }

  const register = async (payload) => {
    const { data } = await api.post('/api/auth/register', payload)
    localStorage.setItem('auth_token', data.token)
    setUser(data.user)
    return data.user
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    window.location.href = '/login'
  }

  const isCentralAdmin = user?.roles?.includes('CENTRAL_ADMIN')

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithSourceToken, register, logout, isAdmin: !!user?.is_admin, isCentralAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
