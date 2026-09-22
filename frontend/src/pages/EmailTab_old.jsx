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

  // Email list state - UPDATED for database-driven pagination
  const [emails, setEmails] = useState([])
  const [filteredEmails, setFilteredEmails] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [limit, setLimit] = useState(20)  // Items per page
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalEmails, setTotalEmails] = useState(0)
  const [folder, setFolder] = useState('INBOX')
  const [folders, setFolders] = useState([])
  const [msg, setMsg] = useState(null)
  const [viewMode, setViewMode] = useState('list') // list, detail, compose, drafts, sent
  const [lastRefresh, setLastRefresh] = useState(null)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [sortOrder, setSortOrder] = useState('desc')

  // Auto-reply state
  const [showAutoReply, setShowAutoReply] = useState(false)
  const [autoReplySettings, setAutoReplySettings] = useState({
    enabled: false,
    mode: 'review', // 'auto' or 'review'
    ai_instructions: 'Be professional and concise.',
    use_database: true,
    reply_template: ''
  })
  const [autoReplyLoading, setAutoReplyLoading] = useState(false)

  // Compose/Draft state
  const [showCompose, setShowCompose] = useState(false)
  const [draftForm, setDraftForm] = useState({
    to_address: '',
    cc_address: '',
    bcc_address: '',
    subject: '',
    body: ''
  })
  const [drafts, setDrafts] = useState([])
  const [draftsLoading, setDraftsLoading] = useState(false)
  const [composing, setComposing] = useState(false)
  const [replyingTo, setReplyingTo] = useState(null)

  // Load config and folders on mount
  useEffect(() => {
    loadConfig()
    loadFolders()
    loadEmails('first-load') // Load first page
    loadAutoReplySettings()
    loadDrafts()
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

  const loadEmails = async (mode = 'page-change') => {
    setLoading(true)
    setMsg(null)
    try {
      let response
      
      if (searchQuery.trim()) {
        // Search mode
        response = await api.get('/api/email/storage/search', {
          params: {
            q: searchQuery,
            page: currentPage,
            per_page: limit,
            folder: folder !== 'INBOX' ? folder : undefined,
            sort_order: sortOrder
          }
        })
      } else {
        // Browse mode - fetch from database
        if (folder === 'INBOX') {
          response = await api.get('/api/email/storage/inbox', {
            params: {
              page: currentPage,
              per_page: limit,
              unread_only: unreadOnly,
              sort_order: sortOrder
            }
          })
        } else {
          response = await api.get(`/api/email/storage/folder/${encodeURIComponent(folder)}`, {
            params: {
              page: currentPage,
              per_page: limit,
              unread_only: unreadOnly,
              sort_order: sortOrder
            }
          })
        }
      }

      if (response.data.success) {
        setEmails(response.data.emails || [])
        setFilteredEmails(response.data.emails || [])
        setTotalEmails(response.data.pagination?.total || 0)
        setTotalPages(response.data.pagination?.total_pages || 1)
        
        if (mode === 'first-load') {
          setMsg({ type: 'success', text: `✓ Loaded ${response.data.emails.length} email(s)` })
        }
        
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

  // Auto-Reply Functions
  const loadAutoReplySettings = async () => {
    try {
      const { data } = await api.get('/api/email/auto-reply/settings')
      if (data.success) {
        setAutoReplySettings(data.settings)
      }
    } catch (error) {
      console.error('Error loading auto-reply settings:', error)
    }
  }

  const updateAutoReplySettings = async () => {
    setAutoReplyLoading(true)
    try {
      const { data } = await api.post('/api/email/auto-reply/settings', autoReplySettings)
      if (data.success) {
        setMsg({ type: 'success', text: 'Auto-reply settings updated' })
        setTimeout(() => setMsg(null), 2000)
      }
    } catch (error) {
      console.error('Error updating auto-reply settings:', error)
      setMsg({ type: 'error', text: 'Failed to update auto-reply settings' })
    } finally {
      setAutoReplyLoading(false)
    }
  }

  const generateAutoReply = async (emailId) => {
    try {
      setComposing(true)
      const { data } = await api.post('/api/email/auto-reply/generate', {
        email_id: emailId,
        custom_prompt: ''
      })
      if (data.success) {
        setMsg({ type: 'success', text: 'Auto-reply generated! Check drafts to review and send.' })
        loadDrafts()
        setViewMode('list')
      }
    } catch (error) {
      console.error('Error generating auto-reply:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Failed to generate auto-reply' })
    } finally {
      setComposing(false)
    }
  }

  // Compose & Drafts Functions
  const loadDrafts = async () => {
    setDraftsLoading(true)
    try {
      const { data } = await api.get('/api/email/drafts')
      if (data.success) {
        setDrafts(data.drafts || [])
      }
    } catch (error) {
      console.error('Error loading drafts:', error)
    } finally {
      setDraftsLoading(false)
    }
  }

  const startCompose = (replyTo = null) => {
    setReplyingTo(replyTo)
    if (replyTo) {
      setDraftForm({
        to_address: replyTo.from,
        cc_address: '',
        bcc_address: '',
        subject: `Re: ${replyTo.subject}`,
        body: ''
      })
    } else {
      setDraftForm({ to_address: '', cc_address: '', bcc_address: '', subject: '', body: '' })
    }
    setShowCompose(true)
    setViewMode('compose')
  }

  const saveDraft = async () => {
    if (!draftForm.to_address || !draftForm.subject || !draftForm.body) {
      setMsg({ type: 'error', text: 'Please fill in all fields' })
      return
    }

    try {
      setComposing(true)
      const { data } = await api.post('/api/email/drafts', {
        ...draftForm,
        in_reply_to: replyingTo?.id
      })
      if (data.success) {
        setMsg({ type: 'success', text: 'Draft saved!' })
        loadDrafts()
        setShowCompose(false)
        setDraftForm({ to_address: '', cc_address: '', bcc_address: '', subject: '', body: '' })
        setReplyingTo(null)
      }
    } catch (error) {
      console.error('Error saving draft:', error)
      setMsg({ type: 'error', text: 'Failed to save draft' })
    } finally {
      setComposing(false)
    }
  }

  const sendDraft = async (draftId) => {
    try {
      setComposing(true)
      const { data } = await api.post(`/api/email/drafts/${draftId}/send`)
      if (data.success) {
        setMsg({ type: 'success', text: `Email sent to ${data.draft.to_address}` })
        loadDrafts()
      }
    } catch (error) {
      console.error('Error sending draft:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Failed to send email' })
    } finally {
      setComposing(false)
    }
  }

  const sendDirectEmail = async () => {
    if (!draftForm.to_address || !draftForm.subject || !draftForm.body) {
      setMsg({ type: 'error', text: 'Please fill in all fields' })
      return
    }

    try {
      setComposing(true)
      const { data } = await api.post('/api/email/send', draftForm)
      if (data.success) {
        setMsg({ type: 'success', text: data.message })
        setShowCompose(false)
        setDraftForm({ to_address: '', cc_address: '', bcc_address: '', subject: '', body: '' })
        setReplyingTo(null)
        setViewMode('list')
      }
    } catch (error) {
      console.error('Error sending email:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Failed to send email' })
    } finally {
      setComposing(false)
    }
  }

  const deleteDraft = async (draftId) => {
    if (!window.confirm('Delete this draft?')) return

    try {
      const { data } = await api.delete(`/api/email/drafts/${draftId}`)
      if (data.success) {
        setMsg({ type: 'success', text: 'Draft deleted' })
        loadDrafts()
      }
    } catch (error) {
      console.error('Error deleting draft:', error)
      setMsg({ type: 'error', text: 'Failed to delete draft' })
    }
  }

  // Pagination Functions
  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  const goToPreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const goToFirstPage = () => {
    setCurrentPage(1)
  }

  const goToLastPage = () => {
    setCurrentPage(totalPages)
  }

  // When folder, limit, or filter changes, reset to page 1
  useEffect(() => {
    setCurrentPage(1)
  }, [folder, limit, unreadOnly, sortOrder])

  // Load emails when page changes
  useEffect(() => {
    if (currentPage > 0) {
      loadEmails('page-change')
    }
  }, [currentPage])

  // Sent Emails Functions
  const [sentEmails, setSentEmails] = useState([])
  const [sentLoading, setSentLoading] = useState(false)
  const [sentPage, setSentPage] = useState(1)
  const [sentTotalPages, setSentTotalPages] = useState(1)

  const loadSentEmails = async (page = 1) => {
    setSentLoading(true)
    try {
      const { data } = await api.get('/api/email/storage/sent', {
        params: {
          page,
          per_page: limit,
          sort_order: 'desc'
        }
      })
      if (data.success) {
        setSentEmails(data.emails || [])
        setSentPage(page)
        setSentTotalPages(data.pagination?.total_pages || 1)
      }
    } catch (error) {
      console.error('Error loading sent emails:', error)
      setMsg({ type: 'error', text: 'Failed to load sent emails' })
    } finally {
      setSentLoading(false)
    }
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
        {/* Auto-Reply and Compose Buttons */}
        <div className="flex gap-2 mb-4 flex-wrap">
          <button
            onClick={() => setShowAutoReply(!showAutoReply)}
            className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
              autoReplySettings.enabled
                ? 'bg-green-100 text-green-700 border border-green-300'
                : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
            }`}
          >
            <Mail size={16} />
            {autoReplySettings.enabled ? 'Auto-Reply ON' : 'Auto-Reply OFF'}
          </button>

          <button
            onClick={() => startCompose()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition flex items-center gap-2"
          >
            <Mail size={16} />
            Compose Email
          </button>

          <button
            onClick={() => { setViewMode('drafts'); loadDrafts() }}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition flex items-center gap-2 relative"
          >
            <Mail size={16} />
            Outbox
            {drafts.length > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                {drafts.length}
              </span>
            )}
          </button>

          <button
            onClick={() => { setViewMode('sent'); loadSentEmails() }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition flex items-center gap-2"
          >
            <Mail size={16} />
            Sent Mail
          </button>
        </div>

        {/* Auto-Reply Settings */}
        {showAutoReply && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
            <h4 className="font-semibold text-green-900">Auto-Reply Configuration</h4>
            
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={autoReplySettings.enabled}
                onChange={(e) => setAutoReplySettings({
                  ...autoReplySettings,
                  enabled: e.target.checked
                })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Enable Auto-Reply</span>
            </label>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Reply Mode</label>
              <select
                value={autoReplySettings.mode}
                onChange={(e) => setAutoReplySettings({
                  ...autoReplySettings,
                  mode: e.target.value
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="review">Review Before Sending (Drafts)</option>
                <option value="auto">Auto-Send (Immediate)</option>
              </select>
              <p className="text-xs text-gray-600 mt-1">
                {autoReplySettings.mode === 'review'
                  ? 'Generated replies will be saved as drafts for you to review'
                  : 'Generated replies will be sent automatically'}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">AI Instructions</label>
              <textarea
                value={autoReplySettings.ai_instructions}
                onChange={(e) => setAutoReplySettings({
                  ...autoReplySettings,
                  ai_instructions: e.target.value
                })}
                placeholder="e.g., Be professional and concise. Focus on customer satisfaction."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm h-20"
              />
            </div>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={autoReplySettings.use_database}
                onChange={(e) => setAutoReplySettings({
                  ...autoReplySettings,
                  use_database: e.target.checked
                })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Include Database Context in Replies</span>
            </label>

            <div className="flex gap-2 pt-2 border-t">
              <button
                onClick={updateAutoReplySettings}
                disabled={autoReplyLoading}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {autoReplyLoading ? <Loader size={16} className="inline animate-spin mr-2" /> : null}
                Save Settings
              </button>
              <button
                onClick={() => setShowAutoReply(false)}
                className="flex-1 px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 rounded-lg font-medium transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Folder Selection and Filters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Inbox size={16} className="inline mr-2" />
              Folder
            </label>
            <select
              value={folder}
              onChange={(e) => { setFolder(e.target.value); setCurrentPage(1) }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              {folders.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Per Page
            </label>
            <select
              value={limit}
              onChange={(e) => { setLimit(parseInt(e.target.value)); setCurrentPage(1) }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sort Order
            </label>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>

          <div className="flex items-end gap-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer flex-1">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => { setUnreadOnly(e.target.checked); setCurrentPage(1) }}
                className="w-4 h-4 rounded border-gray-300"
              />
              Unread Only
            </label>
            <button
              onClick={() => { setCurrentPage(1); loadEmails() }}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition flex items-center gap-2"
            >
              {loading ? <Loader size={16} className="animate-spin" /> : null}
              Load Emails
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
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1) }}
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

        {/* Pagination Controls */}
        {totalPages > 1 && viewMode === 'list' && (
          <div className="flex items-center justify-between bg-gray-50 rounded p-3">
            <div className="text-sm text-gray-700">
              Page <span className="font-semibold">{currentPage}</span> of <span className="font-semibold">{totalPages}</span> ({totalEmails} total emails)
            </div>
            <div className="flex gap-2">
              <button
                onClick={goToFirstPage}
                disabled={currentPage === 1 || loading}
                className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
              >
                First
              </button>
              <button
                onClick={goToPreviousPage}
                disabled={currentPage === 1 || loading}
                className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
              >
                Previous
              </button>
              <button
                onClick={goToNextPage}
                disabled={currentPage === totalPages || loading}
                className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
              >
                Next
              </button>
              <button
                onClick={goToLastPage}
                disabled={currentPage === totalPages || loading}
                className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
              >
                Last
              </button>
            </div>
          </div>
        )}

        {/* Status Info */}
        {lastRefresh && (
          <p className="text-xs text-gray-500">
            Last refreshed: {lastRefresh} • Showing {filteredEmails.length} email(s) • {unreadOnly ? 'Unread only' : 'All emails'}
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
                        {!email.is_read ? (
                          <span className="w-3 h-3 bg-blue-600 rounded-full flex-shrink-0"></span>
                        ) : (
                          <span className="w-3 h-3 bg-gray-300 rounded-full flex-shrink-0"></span>
                        )}
                        <h3 className={`font-semibold text-sm truncate ${
                          !email.is_read ? 'text-gray-900' : 'text-gray-600'
                        }`}>
                          {email.subject || '(no subject)'}
                        </h3>
                      </div>

                      <p className="text-xs text-gray-600 mb-1">
                        From: <span className="font-medium">{email.from_address}</span>
                      </p>

                      <p className="text-sm text-gray-700 line-clamp-2">
                        {email.body || '(no content)'}
                      </p>

                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(email.received_date).toLocaleString()}
                      </p>
                    </div>

                    <div className="flex-shrink-0 ml-2">
                      {!email.is_read && (
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
                onClick={() => copyToClipboard(selectedEmail.from_address)}
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
              <p className="text-sm text-gray-800 break-all">{selectedEmail.from_address}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Subject</p>
              <p className="text-base font-semibold text-gray-900">{selectedEmail.subject || '(no subject)'}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Date</p>
              <p className="text-sm text-gray-700">{new Date(selectedEmail.received_date).toLocaleString()}</p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Folder</p>
              <p className="text-sm text-gray-700">{selectedEmail.folder}</p>
            </div>

            {selectedEmail.body && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">Message</p>
                <div className="bg-gray-50 rounded border border-gray-200 p-4 max-h-96 overflow-y-auto">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{selectedEmail.body}</p>
                </div>
              </div>
            )}

            {selectedEmail.html_body && !selectedEmail.body && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">Message (HTML)</p>
                <div className="bg-gray-50 rounded border border-gray-200 p-4 max-h-96 overflow-y-auto">
                  <div
                    className="text-sm text-gray-800"
                    dangerouslySetInnerHTML={{ __html: selectedEmail.html_body }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4 border-t flex-wrap">
            {!selectedEmail.is_read ? (
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

            <button
              onClick={() => startCompose(selectedEmail)}
              className="btn-primary flex items-center gap-2"
            >
              <Mail size={16} /> Reply
            </button>

            {autoReplySettings.enabled && (
              <button
                onClick={() => generateAutoReply(selectedEmail.id)}
                disabled={composing}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {composing ? <Loader size={16} className="animate-spin" /> : <Mail size={16} />}
                Generate Auto-Reply (AI + Database Context)
              </button>
            )}
          </div>
        </div>
      ) : viewMode === 'compose' ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          {/* Compose Header */}
          <div className="flex items-center justify-between pb-4 border-b">
            <h3 className="text-lg font-semibold">
              {replyingTo ? `Reply to: ${replyingTo.from}` : 'Compose Email'}
            </h3>
            <button
              onClick={() => {
                setShowCompose(false)
                setViewMode('list')
                setReplyingTo(null)
                setDraftForm({ to_address: '', subject: '', body: '' })
              }}
              className="text-gray-500 hover:text-gray-700 text-xl"
            >
              ✕
            </button>
          </div>

          {/* Compose Form */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">To</label>
              <input
                type="email"
                value={draftForm.to_address}
                onChange={(e) => setDraftForm({ ...draftForm, to_address: e.target.value })}
                placeholder="recipient@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">CC</label>
              <input
                type="text"
                value={draftForm.cc_address}
                onChange={(e) => setDraftForm({ ...draftForm, cc_address: e.target.value })}
                placeholder="cc@example.com, another@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">Separate multiple addresses with commas</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">BCC</label>
              <input
                type="text"
                value={draftForm.bcc_address}
                onChange={(e) => setDraftForm({ ...draftForm, bcc_address: e.target.value })}
                placeholder="bcc@example.com, hidden@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">Recipients won't see BCC addresses</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
              <input
                type="text"
                value={draftForm.subject}
                onChange={(e) => setDraftForm({ ...draftForm, subject: e.target.value })}
                placeholder="Email subject..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
              <textarea
                value={draftForm.body}
                onChange={(e) => setDraftForm({ ...draftForm, body: e.target.value })}
                placeholder="Type your message here..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm h-64 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={saveDraft}
              disabled={composing}
              className="flex-1 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
            >
              {composing ? <Loader size={16} className="animate-spin" /> : <Mail size={16} />}
              Save as Draft
            </button>

            <button
              onClick={sendDirectEmail}
              disabled={composing}
              className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
            >
              {composing ? <Loader size={16} className="animate-spin" /> : <Mail size={16} />}
              Send Now
            </button>

            <button
              onClick={() => {
                setShowCompose(false)
                setViewMode('list')
                setReplyingTo(null)
                setDraftForm({ to_address: '', subject: '', body: '' })
              }}
              className="flex-1 px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 rounded-lg font-medium transition"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : viewMode === 'drafts' ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          {/* Drafts Header */}
          <div className="flex items-center justify-between pb-4 border-b">
            <h3 className="text-lg font-semibold">Email Outbox / Drafts</h3>
            <button
              onClick={() => setViewMode('list')}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
            >
              ← Back to Inbox
            </button>
          </div>

          {/* Drafts List */}
          {draftsLoading ? (
            <div className="flex justify-center py-8">
              <Loader size={32} className="animate-spin text-blue-600" />
            </div>
          ) : drafts.length === 0 ? (
            <div className="text-center py-8">
              <Mail size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No drafts yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {drafts.map(draft => (
                <div key={draft.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">To: {draft.to_address}</p>
                      {draft.cc_address && <p className="text-xs text-gray-600">CC: {draft.cc_address}</p>}
                      {draft.bcc_address && <p className="text-xs text-gray-600">BCC: {draft.bcc_address}</p>}
                      <p className="text-sm text-gray-700 font-semibold">{draft.subject}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(draft.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      <span className={`inline-block text-xs px-2 py-1 rounded font-medium ${
                        draft.status === 'draft'
                          ? 'bg-blue-100 text-blue-800'
                          : draft.status === 'pending_review'
                          ? 'bg-yellow-100 text-yellow-800'
                          : draft.status === 'sent'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {draft.status.toUpperCase()}
                      </span>
                      {draft.auto_generated && (
                        <span className="inline-block ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded font-medium">
                          AI Generated
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded p-3 mb-3 max-h-20 overflow-y-auto">
                    <p className="text-sm text-gray-700">{draft.body}</p>
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => {
                        setDraftForm({
                          to_address: draft.to_address,
                          cc_address: draft.cc_address || '',
                          bcc_address: draft.bcc_address || '',
                          subject: draft.subject,
                          body: draft.body
                        })
                        setReplyingTo(null)
                        setShowCompose(true)
                        setViewMode('compose')
                      }}
                      className="px-3 py-1 text-sm bg-blue-100 text-blue-700 hover:bg-blue-200 rounded transition"
                    >
                      Edit
                    </button>

                    <button
                      onClick={() => sendDraft(draft.id)}
                      disabled={composing}
                      className="px-3 py-1 text-sm bg-green-100 text-green-700 hover:bg-green-200 rounded transition flex items-center gap-1 disabled:opacity-50"
                    >
                      {composing && <Loader size={12} className="animate-spin" />}
                      Send
                    </button>

                    <button
                      onClick={() => deleteDraft(draft.id)}
                      className="px-3 py-1 text-sm bg-red-100 text-red-700 hover:bg-red-200 rounded transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : viewMode === 'sent' ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          {/* Sent Emails Header */}
          <div className="flex items-center justify-between pb-4 border-b">
            <h3 className="text-lg font-semibold">Sent Emails (AI Replies & Manual Sends)</h3>
            <button
              onClick={() => setViewMode('list')}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
            >
              ← Back to Inbox
            </button>
          </div>

          {/* Sent Emails List */}
          {sentLoading ? (
            <div className="flex justify-center py-8">
              <Loader size={32} className="animate-spin text-blue-600" />
            </div>
          ) : sentEmails.length === 0 ? (
            <div className="text-center py-8">
              <Mail size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No sent emails yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sentEmails.map(email => (
                <div key={email.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">To: {email.to_address}</p>
                      {email.cc_address && <p className="text-xs text-gray-600">CC: {email.cc_address}</p>}
                      {email.bcc_address && <p className="text-xs text-gray-600">BCC: {email.bcc_address}</p>}
                      <p className="text-sm text-gray-700 font-semibold">{email.subject}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Sent: {new Date(email.sent_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className="inline-flex gap-1">
                        {email.ai_generated && (
                          <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded font-medium">
                            AI Generated
                          </span>
                        )}
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded font-medium">
                          SENT
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded p-3 max-h-20 overflow-y-auto mb-2">
                    <p className="text-sm text-gray-700">{email.body}</p>
                  </div>

                  {email.in_reply_to && (
                    <p className="text-xs text-gray-500 italic">
                      This was a reply to a received email (ID: {email.in_reply_to})
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Pagination for Sent Emails */}
          {sentTotalPages > 1 && (
            <div className="flex items-center justify-between bg-gray-50 rounded p-3">
              <div className="text-sm text-gray-700">
                Page <span className="font-semibold">{sentPage}</span> of <span className="font-semibold">{sentTotalPages}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => loadSentEmails(1)}
                  disabled={sentPage === 1 || sentLoading}
                  className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                >
                  First
                </button>
                <button
                  onClick={() => loadSentEmails(sentPage - 1)}
                  disabled={sentPage === 1 || sentLoading}
                  className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => loadSentEmails(sentPage + 1)}
                  disabled={sentPage === sentTotalPages || sentLoading}
                  className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                >
                  Next
                </button>
                <button
                  onClick={() => loadSentEmails(sentTotalPages)}
                  disabled={sentPage === sentTotalPages || sentLoading}
                  className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
