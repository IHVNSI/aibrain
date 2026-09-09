import axios from 'axios'

// All requests go through the Vite proxy to the Flask backend.
const api = axios.create({ baseURL: '/' })

// Attach the JWT (from localStorage) to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  console.log('[API] Request:', config.method.toUpperCase(), config.url, 'with token:', !!token)
  return config
})

// On 401, clear the token and bounce to login.
api.interceptors.response.use(
  (resp) => {
    console.log('[API] Response:', resp.status, resp.config.url)
    return resp
  },
  (error) => {
    console.error('[API] Error response:', error.response?.status, error.response?.config?.url, error.response?.data)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

export const handleApiError = (error) => {
  if (!error.response) {
    return { type: 'network', message: 'Unable to connect to server. Check your internet connection.' }
  }
  const data = error.response.data || {}
  return { type: 'server', message: data.error || `Request failed (${error.response.status})` }
}
