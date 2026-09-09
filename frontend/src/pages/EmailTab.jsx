import React, { useState, useEffect } from 'react'
import api from '../api/client'
import {
  Mail, Search, Inbox, Trash2, CheckCircle2, XCircle, Loader,
  Eye, EyeOff, Copy, RefreshCw, AlertCircle, Download, Settings, Lock, Wifi, WifiOff
} from 'lucide-react'
import Swal from 'sweetalert2'

export default function EmailTab() {
  // Config state
  const [showConfig, setShowConfig] = useState(false)
  const [configLoading, setConfigLoading] = useState(false)
  const [config, setConfig] = useState({
    email_address: '',
    email_password: '',
    email_provider: 'gmail',
    imap_server: '',
    imap_port: 993,
    imap_tls: true,
    smtp_server: '',
    smtp_port: 587,
    smtp_tls: true,
    check_interval: 5,
    fetch_limit: 10,
  })
  const [providers, setProviders] = useState({})
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [showPassword, setShowPassword] = useState(false)

  // Email list state
  const [emails, setEmails] = useState([])
  const [filteredEmails, setFilteredEmails] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [limit, setLimit] = useState(10)
  const [folder, setFolder] = useState('INBOX')
  const [folders, setFolders] = useState([])
  const [msg, setMsg] = useState(null)
  const [viewMode, setViewMode] = useState('list') // list or detail
  const [lastRefresh, setLastRefresh] = useState(null)

  // Load config and folders on mount
  useEffect(() => {
    loadConfig()
    loadFolders()
    loadEmails()
  }, [])

  // Load email configuration
  const loadConfig = async () => {
    try {
      const { data } = await api.get('/api/email/config')
      if (data.success) {
        setConfig(data.config)
        setProviders(data.providers)
      }
    } catch (error) {
      console.error('Error loading email config:', error)
    }
  }

  // Handle provider change - auto-populate servers
  const handleProviderChange = (provider) => {
    setConfig({ ...config, email_provider: provider })
    
    if (providers[provider]) {
      const preset = providers[provider]
      setConfig(prev => ({
        ...prev,
        email_provider: provider,
        imap_server: preset.imap_server,
        imap_port: preset.imap_port,
        smtp_server: preset.smtp_server,
        smtp_port: preset.smtp_port,
      }))
    }
  }

  // Save configuration
  const saveConfig = async () => {
    if (!config.email_address || !config.email_password) {
      setMsg({ type: 'error', text: 'Email address and password are required' })
      return
    }

    setConfigLoading(true)
    setTestResult(null)
    
    try {
      const { data } = await api.post('/api/email/config', config)
      if (data.success) {
        setMsg({ type: 'success', text: '✓ Email configuration saved successfully' })
        setTimeout(() => {
          setMsg(null)
          setShowConfig(false)
          loadFolders()
          loadEmails()
        }, 2000)
      }
    } catch (error) {
      console.error('Error saving config:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Failed to save configuration' })
    } finally {
      setConfigLoading(false)
    }
  }

  // Test connection
  const testConnection = async () => {
    if (!config.email_address || !config.email_password) {
      setTestResult({ type: 'error', text: 'Email address and password required' })
      return
    }

    setTestingConnection(true)
    
    try {
      const { data } = await api.post('/api/email/config', {
        ...config,
        test_connection: true
      })
      if (data.success) {
        setTestResult({
          type: 'success',
          text: data.test_result || '✓ Connection successful'
        })
      }
    } catch (error) {
      setTestResult({
        type: 'error',
        text: error.response?.data?.error || 'Connection test failed'
      })
    } finally {
      setTestingConnection(false)
    }
  }

  // Load folders on mount
  // useEffect(() => {
  //   loadFolders()
  //   loadEmails()
  // }, [])

  // Filter emails based on search
  useEffect(() => {
    if (searchQuery.trim()) {
      const filtered = emails.filter(email =>
        email.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
        email.from.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (email.text && email.text.toLowerCase().includes(searchQuery.toLowerCase()))
      )
      setFilteredEmails(filtered)
    } else {
      setFilteredEmails(emails)
    }
  }, [searchQuery, emails])

  const loadFolders = async () => {
    try {
      const { data } = await api.get('/api/email/folders')
      if (data.success) {
        setFolders(data.folders || [])
      }
    } catch (error) {
      console.error('Error loading folders:', error)
    }
  }

  const loadEmails = async (mode = 'unread') => {
    setLoading(true)
    setMsg(null)
    try {
      let response
      if (mode === 'unread') {
        response = await api.get(`/api/email/unread?limit=${limit}&folder=${folder}`)
      } else if (mode === 'search') {
        if (!searchQuery.trim()) {
          setMsg({ type: 'error', text: 'Enter a search query' })
          setLoading(false)
          return
        }
        response = await api.get(`/api/email/search?q=${searchQuery}&limit=${limit}`)
      }

      if (response.data.success) {
        setEmails(response.data.emails || [])
        setMsg({ type: 'success', text: `✓ Loaded ${response.data.emails.length} email(s)` })
        setLastRefresh(new Date().toLocaleTimeString())
        setViewMode('list')
        setSelectedEmail(null)
      } else {
        setMsg({ type: 'error', text: response.data.error || 'Failed to load emails' })
      }
    } catch (error) {
      console.error('Error loading emails:', error)
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error'
      setMsg({ type: 'error', text: `Error: ${errorMsg}` })
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (emailId) => {
    try {
      const { data } = await api.post(`/api/email/mark-read/${emailId}`)
      if (data.success) {
        setEmails(emails.map(e => e.id === emailId ? { ...e, is_unread: false } : e))
        setMsg({ type: 'success', text: 'Email marked as read' })
        setTimeout(() => setMsg(null), 2000)
      }
    } catch (error) {
      console.error('Error marking email:', error)
      setMsg({ type: 'error', text: 'Failed to mark email as read' })
    }
  }

  const refreshEmails = () => {
    loadEmails('unread')
  }

  const handleSelectEmail = (email) => {
    setSelectedEmail(email)
    setViewMode('detail')
    if (email.is_unread) {
      markAsRead(email.id)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setMsg({ type: 'success', text: 'Copied to clipboard!' })
    setTimeout(() => setMsg(null), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Mail size={28} className="text-blue-600" />
          Email Manager
        </h2>
        <button
          onClick={refreshEmails}
          disabled={loading}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Messages */}
      {msg && (
        <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {msg.type === 'success' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
          {msg.text}
        </div>
      )}

      {/* Email Configuration Section */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-4">
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="w-full flex items-center justify-between font-semibold text-blue-900 hover:bg-blue-100 p-3 rounded-lg transition"
        >
          <span className="flex items-center gap-2">
            <Settings size={20} className="text-blue-600" />
            Email Configuration
          </span>
          <span className="text-sm text-blue-600">{showConfig ? '▼' : '▶'}</span>
        </button>

        {showConfig && (
          <div className="mt-4 space-y-4 p-4 bg-white rounded-lg border border-blue-100">
            {/* Email Provider Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Mail size={16} className="inline mr-2" />
                  Email Address
                </label>
                <input
                  type="email"
                  value={config.email_address}
                  onChange={(e) => setConfig({ ...config, email_address: e.target.value })}
                  placeholder="your.email@gmail.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Lock size={16} className="inline mr-2" />
                  Email Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={config.email_password}
                    onChange={(e) => setConfig({ ...config, email_password: e.target.value })}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-700"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">💡 For Gmail: use App Password, not your regular password</p>
              </div>
            </div>

            {/* Email Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email Provider</label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {['gmail', 'outlook', 'yahoo', 'icloud', 'custom'].map(provider => (
                  <button
                    key={provider}
                    onClick={() => handleProviderChange(provider)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                      config.email_provider === provider
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {provider.charAt(0).toUpperCase() + provider.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* IMAP Configuration */}
            <div className="border-t pt-4">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Wifi size={16} className="text-blue-600" />
                IMAP Settings (Reading Emails)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">IMAP Server</label>
                  <input
                    type="text"
                    value={config.imap_server}
                    onChange={(e) => setConfig({ ...config, imap_server: e.target.value })}
                    placeholder="imap.gmail.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">IMAP Port</label>
                  <input
                    type="number"
                    value={config.imap_port}
                    onChange={(e) => setConfig({ ...config, imap_port: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.imap_tls}
                      onChange={(e) => setConfig({ ...config, imap_tls: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                    Use TLS/SSL
                  </label>
                </div>
              </div>
            </div>

            {/* SMTP Configuration */}
            <div className="border-t pt-4">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Wifi size={16} className="text-blue-600" />
                SMTP Settings (Sending Emails)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">SMTP Server</label>
                  <input
                    type="text"
                    value={config.smtp_server}
                    onChange={(e) => setConfig({ ...config, smtp_server: e.target.value })}
                    placeholder="smtp.gmail.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">SMTP Port</label>
                  <input
                    type="number"
                    value={config.smtp_port}
                    onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.smtp_tls}
                      onChange={(e) => setConfig({ ...config, smtp_tls: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                    Use TLS/SSL
                  </label>
                </div>
              </div>
            </div>

            {/* Advanced Settings */}
            <div className="border-t pt-4">
              <h4 className="font-semibold text-gray-900 mb-3">Advanced Settings</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Check Interval (minutes)</label>
                  <input
                    type="number"
                    value={config.check_interval}
                    onChange={(e) => setConfig({ ...config, check_interval: parseInt(e.target.value) })}
                    min="1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Fetch Limit (emails per check)</label>
                  <input
                    type="number"
                    value={config.fetch_limit}
                    onChange={(e) => setConfig({ ...config, fetch_limit: parseInt(e.target.value) })}
                    min="1"
                    max="100"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Test Connection Result */}
            {testResult && (
              <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
                testResult.type === 'success'
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-red-50 text-red-700 border border-red-200'
              }`}>
                {testResult.type === 'success' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                {testResult.text}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <button
                onClick={testConnection}
                disabled={testingConnection || configLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {testingConnection ? <Loader size={18} className="animate-spin" /> : <Wifi size={18} />}
                Test Connection
              </button>
              <button
                onClick={saveConfig}
                disabled={configLoading || testingConnection}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {configLoading ? <Loader size={18} className="inline animate-spin mr-2" /> : null}
                Save Configuration
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        {/* Folder and Limit Selector */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Inbox size={16} className="inline mr-2" />
              Folder
            </label>
            <select
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              {folders.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Load Limit
            </label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 10)}
              min="1"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">&nbsp;</label>
            <button
              onClick={() => loadEmails('unread')}
              disabled={loading}
              className="w-full btn-primary"
            >
              {loading ? <Loader size={16} className="animate-spin inline mr-2" /> : null}
              Load Unread
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Search emails by subject, from, or content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <button
            onClick={() => loadEmails('search')}
            disabled={loading || !searchQuery.trim()}
            className="btn-primary"
          >
            Search
          </button>
        </div>

        {/* Status Info */}
        {lastRefresh && (
          <p className="text-xs text-gray-500">
            Last refreshed: {lastRefresh} • Showing {filteredEmails.length} email(s)
          </p>
        )}
      </div>

      {/* Email List or Detail View */}
      {viewMode === 'list' ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading && (
            <div className="flex justify-center items-center py-12">
              <Loader size={32} className="animate-spin text-blue-600" />
            </div>
          )}

          {!loading && filteredEmails.length === 0 && (
            <div className="text-center py-12">
              <Mail size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No emails found</p>
            </div>
          )}

          {!loading && filteredEmails.length > 0 && (
            <div className="divide-y divide-gray-200">
              {filteredEmails.map((email) => (
                <div
                  key={email.id}
                  onClick={() => handleSelectEmail(email)}
                  className="p-4 hover:bg-gray-50 cursor-pointer transition border-l-4 border-transparent hover:border-blue-500"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {email.is_unread ? (
                          <span className="w-3 h-3 bg-blue-600 rounded-full flex-shrink-0"></span>
                        ) : (
                          <span className="w-3 h-3 bg-gray-300 rounded-full flex-shrink-0"></span>
                        )}
                        <h3 className={`font-semibold text-sm truncate ${
                          email.is_unread ? 'text-gray-900' : 'text-gray-600'
                        }`}>
                          {email.subject || '(no subject)'}
                        </h3>
                      </div>

                      <p className="text-xs text-gray-600 mb-1">
                        From: <span className="font-medium">{email.from}</span>
                      </p>

                      <p className="text-sm text-gray-700 line-clamp-2">
                        {email.text || '(no content)'}
                      </p>

                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(email.date).toLocaleString()}
                      </p>
                    </div>

                    <div className="flex-shrink-0 ml-2">
                      {email.is_unread && (
                        <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                          Unread
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : selectedEmail ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          {/* Detail Header */}
          <div className="flex items-center justify-between pb-4 border-b">
            <button
              onClick={() => setViewMode('list')}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
            >
              ← Back to List
            </button>
            <div className="flex gap-2">
              <button
                onClick={() => copyToClipboard(selectedEmail.from)}
                className="p-2 hover:bg-gray-100 rounded"
                title="Copy email address"
              >
                <Copy size={18} className="text-gray-600" />
              </button>
            </div>
          </div>

          {/* Email Details */}
          <div className="space-y-3">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">From</p>
              <p className="text-sm text-gray-800 break-all">{selectedEmail.from}</p>
            </div>

            {selectedEmail.to && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">To</p>
                <p className="text-sm text-gray-800">{selectedEmail.to}</p>
              </div>
            )}

            {selectedEmail.cc && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">CC</p>
                <p className="text-sm text-gray-800">{selectedEmail.cc}</p>
              </div>
            )}

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Subject</p>
              <p className="text-base font-semibold text-gray-900">{selectedEmail.subject || '(no subject)'}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Date</p>
              <p className="text-sm text-gray-700">{new Date(selectedEmail.date).toLocaleString()}</p>
            </div>

            {selectedEmail.text && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">Message</p>
                <div className="bg-gray-50 rounded border border-gray-200 p-4 max-h-96 overflow-y-auto">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{selectedEmail.text}</p>
                </div>
              </div>
            )}

            {selectedEmail.html && !selectedEmail.text && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">Message (HTML)</p>
                <div className="bg-gray-50 rounded border border-gray-200 p-4 max-h-96 overflow-y-auto">
                  <div
                    className="text-sm text-gray-800"
                    dangerouslySetInnerHTML={{ __html: selectedEmail.html }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4 border-t">
            {selectedEmail.is_unread ? (
              <button
                onClick={() => markAsRead(selectedEmail.id)}
                className="btn-secondary flex items-center gap-2"
              >
                <Eye size={16} /> Mark as Read
              </button>
            ) : (
              <span className="text-xs text-gray-500 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-green-600" />
                Already read
              </span>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}
