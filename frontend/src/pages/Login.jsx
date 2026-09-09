import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Database, Loader, AlertCircle, ChevronRight, Key } from 'lucide-react'
import api from '../api/client'

export default function Login() {
  const { login, loginWithSourceToken, register } = useAuth()
  const navigate = useNavigate()

  const [loginMode, setLoginMode] = useState('email') // email | token
  const [step, setStep] = useState(1) // 1=email, 2=password, 3=company
  const [isRegistering, setIsRegistering] = useState(false)
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tempUsername, setTempUsername] = useState('')
  const [token, setToken] = useState('')

  const [availableCompanies, setAvailableCompanies] = useState([])
  const [selectedCompanyId, setSelectedCompanyId] = useState('')

  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    company_name: ''
  })

  const handleEmailSubmit = async (e) => {
    e.preventDefault()
    setFormError('')

    if (!email.trim()) {
      setFormError('Email is required')
      return
    }

    // Move to password step
    setStep(2)
  }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault()
    setFormError('')

    if (!password) {
      setFormError('Password is required')
      return
    }

    try {
      setBusy(true)
      const normalizedEmail = email.trim().toLowerCase()
      
      // Attempt login with provided credentials
      try {
        const result = await login(email, password)
        if (result?.success === false) {
          setFormError(result.error || 'Login failed')
          return
        }
        navigate('/chat')
        return
      } catch (innerErr) {
        // If admin/direct login fails, fall through to source DB login
        console.log('[LOGIN] Direct login failed, attempting source DB login:', innerErr.message)
      }
      
      // For all other users, use source database login
      console.log('[LOGIN] Attempting source DB login with email:', normalizedEmail)
      
      // Authenticate against SOURCE database
      const response = await api.post('/api/auth/source-db-login', {
        email: normalizedEmail,
        password: password
      })

      console.log('[LOGIN] Response received:', response.data)

      if (!response.data.success) {
        setFormError(response.data.error || 'Authentication failed')
        return
      }

      const { username, parent_companies, needs_company_selection } = response.data
      console.log('[LOGIN] Auth successful:', { username, companies: parent_companies?.length })
      
      setTempUsername(username)
      setAvailableCompanies(parent_companies || [])

      if (needs_company_selection && parent_companies && parent_companies.length > 1) {
        console.log('[LOGIN] Multiple companies found, showing selection step')
        setStep(3)
      } else if (parent_companies && parent_companies.length === 1) {
        // Auto-select single company and login
        console.log('[LOGIN] Single company found, auto-selecting')
        await loginWithCompany(username, parent_companies[0].id)
      } else {
        // No company selection needed
        console.log('[LOGIN] No companies, proceeding with login')
        await loginWithCompany(username, null)
      }
    } catch (err) {
      console.error('[LOGIN] Error:', err)
      setFormError(err.response?.data?.error || err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  const loginWithCompany = async (username, companyId) => {
    try {
      setBusy(true)
      console.log('[LOGIN] Finalizing login with username:', username, 'company_id:', companyId)
      
      // Call the new finalize-source-login endpoint to get JWT token
      const response = await api.post('/api/auth/finalize-source-login', {
        username: username,
        company_id: companyId
      })
      
      console.log('[LOGIN] Finalize response:', response.data)
      
      if (!response.data.success) {
        setFormError(response.data.error || 'Login failed')
        return
      }
      
      // Use the token directly from the finalize endpoint
      const result = await loginWithSourceToken(response.data.token, response.data.user)
      if (result?.success === false) {
        setFormError(result.error || 'Login failed')
        return
      }
      navigate('/chat')
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  const handleCompanySelect = async (e) => {
    e.preventDefault()
    setFormError('')

    if (!selectedCompanyId) {
      setFormError('Please select a company')
      return
    }

    await loginWithCompany(tempUsername, selectedCompanyId)
  }

  const handleTokenSubmit = async (e) => {
    e.preventDefault()
    setFormError('')

    if (!token.trim()) {
      setFormError('Token is required')
      return
    }

    try {
      setBusy(true)
      console.log('[TOKEN-LOGIN] Submitting token...')
      
      // Send token to backend for validation and user extraction
      const response = await api.post('/api/auth/token-login', {
        token: token.trim()
      })

      console.log('[TOKEN-LOGIN] Response:', response.data)

      if (!response.data.success) {
        setFormError(response.data.error || 'Token login failed')
        return
      }

      // Use the returned token and user data
      const result = await loginWithSourceToken(response.data.token, response.data.user)
      if (result?.success === false) {
        setFormError(result.error || 'Login failed')
        return
      }
      
      console.log('[TOKEN-LOGIN] Success! Navigating to chat...')
      navigate('/chat')
    } catch (err) {
      console.error('[TOKEN-LOGIN] Error:', err)
      setFormError(err.response?.data?.error || err.message || 'Token login failed')
    } finally {
      setBusy(false)
    }
  }

  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    setFormError('')

    if (!registerForm.username.trim() || !registerForm.email.trim() || !registerForm.password.trim()) {
      setFormError('Username, email, and password are required')
      return
    }

    try {
      setBusy(true)
      await register({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        company_name: registerForm.company_name || undefined,
      })
      navigate('/chat')
    } catch (err) {
      setFormError(err.response?.data?.error || err.message || 'Registration failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-2 text-brand-700 font-semibold mb-1">
          <Database size={22} /> AI Assistant
        </div>
        <p className="text-xs text-gray-400 mb-5">
          AI Assistant — {isRegistering ? 'create account' : 'sign in'}
        </p>

        {formError && (
          <div className="flex items-center gap-2 bg-red-50 text-red-700 text-sm rounded-lg p-2 mb-3">
            <AlertCircle size={15} /> {formError}
          </div>
        )}

        {isRegistering ? (
          <form onSubmit={handleRegisterSubmit} className="space-y-3">
            <input
              className="input"
              placeholder="Username"
              value={registerForm.username}
              onChange={(e) => setRegisterForm((f) => ({ ...f, username: e.target.value }))}
            />
            <input
              className="input"
              type="email"
              placeholder="Email"
              value={registerForm.email}
              onChange={(e) => setRegisterForm((f) => ({ ...f, email: e.target.value }))}
            />
            <input
              className="input"
              placeholder="Company name (optional)"
              value={registerForm.company_name}
              onChange={(e) => setRegisterForm((f) => ({ ...f, company_name: e.target.value }))}
            />
            <input
              className="input"
              type="password"
              placeholder="Password"
              value={registerForm.password}
              onChange={(e) => setRegisterForm((f) => ({ ...f, password: e.target.value }))}
            />
            <button type="submit" disabled={busy} className="btn-primary w-full flex items-center justify-center gap-1">
              {busy ? <Loader size={16} className="animate-spin" /> : null}
              Create account
            </button>
          </form>
        ) : (
          <>
            {/* Login Mode Tabs */}
            {!isRegistering && step === 1 && (
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => {
                    setLoginMode('email')
                    setFormError('')
                    setToken('')
                  }}
                  className={`flex-1 py-2 px-3 text-sm rounded-lg font-medium transition ${
                    loginMode === 'email'
                      ? 'bg-brand-100 text-brand-700 border border-brand-300'
                      : 'bg-gray-100 text-gray-600 border border-gray-200'
                  }`}
                >
                  Email
                </button>
                <button
                  onClick={() => {
                    setLoginMode('token')
                    setFormError('')
                    setEmail('')
                    setPassword('')
                  }}
                  className={`flex-1 py-2 px-3 text-sm rounded-lg font-medium transition flex items-center justify-center gap-1 ${
                    loginMode === 'token'
                      ? 'bg-brand-100 text-brand-700 border border-brand-300'
                      : 'bg-gray-100 text-gray-600 border border-gray-200'
                  }`}
                >
                  <Key size={14} /> Token
                </button>
              </div>
            )}

            {/* Email Login Mode */}
            {loginMode === 'email' && (
              <>
                {step === 1 && (
                  <form onSubmit={handleEmailSubmit} className="space-y-3">
                    <input
                      className="input"
                      type="email"
                      placeholder="Email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                    <button type="submit" disabled={busy} className="btn-primary w-full flex items-center justify-center gap-1">
                      {busy ? <Loader size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                      Continue
                    </button>
                  </form>
                )}

                {step === 2 && (
                  <form onSubmit={handlePasswordSubmit} className="space-y-3">
                    <input
                      className="input"
                      type="password"
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button type="submit" disabled={busy} className="btn-primary w-full flex items-center justify-center gap-1">
                      {busy ? <Loader size={16} className="animate-spin" /> : null}
                      Sign in
                    </button>
                  </form>
                )}

                {step === 3 && (
                  <form onSubmit={handleCompanySelect} className="space-y-3">
                    <label className="text-xs text-gray-500">Select parent company</label>
                    <select
                      className="input"
                      value={selectedCompanyId}
                      onChange={(e) => setSelectedCompanyId(e.target.value)}
                    >
                      <option value="">Choose a company...</option>
                      {availableCompanies.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                    <button type="submit" disabled={busy} className="btn-primary w-full flex items-center justify-center gap-1">
                      {busy ? <Loader size={16} className="animate-spin" /> : null}
                      Continue
                    </button>
                  </form>
                )}
              </>
            )}

            {/* Token Login Mode */}
            {loginMode === 'token' && (
              <form onSubmit={handleTokenSubmit} className="space-y-3">
                <textarea
                  className="input font-mono text-xs"
                  placeholder="Paste your JWT token here..."
                  rows="6"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  spellCheck="false"
                />
                <button type="submit" disabled={busy} className="btn-primary w-full flex items-center justify-center gap-1">
                  {busy ? <Loader size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                  Login with Token
                </button>
                <p className="text-xs text-gray-500 text-center">
                  Your token will be validated and company data will be filtered accordingly.
                </p>
              </form>
            )}
          </>
        )}

        <button
          onClick={() => {
            setIsRegistering(!isRegistering)
            setFormError('')
            setStep(1)
            setLoginMode('email')
          }}
          className="mt-4 text-xs text-brand-600 hover:underline"
        >
          {isRegistering ? 'Have an account? Sign in' : "Don't have an account? Register"}
        </button>

      </div>
    </div>
  )
}
