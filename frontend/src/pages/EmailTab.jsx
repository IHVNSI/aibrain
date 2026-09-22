import React, { useState, useEffect } from 'react'
import api from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import {
  Mail, Search, Inbox, Trash2, CheckCircle2, XCircle, Loader,
  Eye, EyeOff, Copy, RefreshCw, AlertCircle, Download, Settings, Lock, Wifi, WifiOff,
  ChevronRight, X, Send, MessageSquare, Paperclip, Clock, User, FileText
} from 'lucide-react'
import Swal from 'sweetalert2'

export default function EmailTab() {
  // ========================================================================
  // STATE - CONFIG
  // ========================================================================
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

  // ========================================================================
  // STATE - EMAIL LIST & DISPLAY
  // ========================================================================
  const [emails, setEmails] = useState([])
  const [filteredEmails, setFilteredEmails] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [limit, setLimit] = useState(20)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalEmails, setTotalEmails] = useState(0)
  const [folder, setFolder] = useState('INBOX')
  const [folders, setFolders] = useState([])
  const [msg, setMsg] = useState(null)
  const [viewMode, setViewMode] = useState('inbox') // inbox, drafts, sent, compose
  const [lastRefresh, setLastRefresh] = useState(null)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [sortOrder, setSortOrder] = useState('desc')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // ========================================================================
  // STATE - AUTO-REPLY
  // ========================================================================
  const [showAutoReply, setShowAutoReply] = useState(false)
  const [autoReplySettings, setAutoReplySettings] = useState({
    enabled: false,
    mode: 'review',
    ai_instructions: 'Be professional and concise.',
    use_database: true,
    reply_template: ''
  })
  const [autoReplyLoading, setAutoReplyLoading] = useState(false)

  // ========================================================================
  // STATE - COMPOSE/DRAFT
  // ========================================================================
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
  const [sentEmails, setSentEmails] = useState([])
  const [sentPage, setSentPage] = useState(1)
  const [sentTotalPages, setSentTotalPages] = useState(1)
  const [sentLoading, setSentLoading] = useState(false)
  const [sentFilter, setSentFilter] = useState('all') // all, ai_only, replies, failed, pending
  const [sentStats, setSentStats] = useState({ total: 0, ai: 0, replies: 0, failed: 0, pending: 0 })

  // ========================================================================
  // EFFECTS
  // ========================================================================
  
  // Initialize WebSocket for real-time email updates
  const { connected, subscribeEmails, unsubscribeEmails, lastEvent } = useWebSocket()

  useEffect(() => {
    loadConfig()
    loadFolders()
    loadEmails('first-load')
    loadAutoReplySettings()
    loadDrafts()
  }, [])

  // Subscribe to email updates when WebSocket connects
  useEffect(() => {
    if (connected) {
      subscribeEmails()
      console.log('📧 Subscribed to real-time email updates')
    }

    return () => {
      // Optionally unsubscribe when component unmounts
      // unsubscribeEmails()
    }
  }, [connected, subscribeEmails, unsubscribeEmails])

  // Handle incoming email events from WebSocket
  useEffect(() => {
    if (lastEvent && lastEvent.type === 'email') {
      const data = lastEvent.data
      
      if (data.event_type === 'new_email') {
        console.log('📧 New email received:', data.email)
        // Refresh emails to show the new one
        loadEmails('socket-update')
      } else if (data.event_type === 'emails_checked') {
        console.log(`✓ Email check completed: ${data.total_checked} emails`)
        // Optionally refresh the list
        if (data.new_emails > 0) {
          loadEmails('socket-check')
        }
      }
    }
  }, [lastEvent])

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

  // ========================================================================
  // API FUNCTIONS
  // ========================================================================
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
        setSelectedEmail(null)
      } else {
        setMsg({ type: 'error', text: response.data.error || 'Failed to load emails' })
      }
    } catch (error) {
      console.error('Error loading emails:', error)
      setMsg({ type: 'error', text: `Error: ${error.response?.data?.error || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const handleSelectEmail = (email) => {
    setSelectedEmail(email)
    setShowEmailModal(true)
    // Mark as read
    if (!email.is_read) {
      markAsRead(email.id)
    }
  }

  const markAsRead = async (emailId) => {
    try {
      const response = await api.put(`/api/email/storage/${emailId}/mark-read`)
      if (response.data.success) {
        setEmails(emails.map(e => e.id === emailId ? { ...e, is_read: true } : e))
        setFilteredEmails(filteredEmails.map(e => e.id === emailId ? { ...e, is_read: true } : e))
        if (selectedEmail?.id === emailId) {
          setSelectedEmail({ ...selectedEmail, is_read: true })
        }
      }
    } catch (error) {
      console.error('Error marking email as read:', error)
    }
  }

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

  const loadSentEmails = async (page = 1, filter = 'all') => {
    setSentLoading(true)
    try {
      const params = {
        page,
        per_page: 20,
        ai_only: filter === 'ai_only' ? 'true' : 'false'
      }
      const { data } = await api.get('/api/email/storage/sent', { params })
      if (data.success) {
        // Filter client-side for replies, failed, pending
        let filtered = data.emails || []
        
        if (filter === 'replies') {
          filtered = filtered.filter(e => e.in_reply_to !== null)
        } else if (filter === 'failed') {
          filtered = filtered.filter(e => e.status === 'failed')
        } else if (filter === 'pending') {
          filtered = filtered.filter(e => e.status === 'pending')
        }
        
        setSentEmails(filtered)
        setSentPage(page)
        setSentTotalPages(data.pagination?.total_pages || 1)
        
        // Calculate stats
        const allEmails = data.emails || []
        setSentStats({
          total: data.pagination?.total || 0,
          ai: allEmails.filter(e => e.ai_generated).length,
          replies: allEmails.filter(e => e.in_reply_to !== null).length,
          failed: allEmails.filter(e => e.status === 'failed').length,
          pending: allEmails.filter(e => e.status === 'pending').length
        })
      }
    } catch (error) {
      console.error('Error loading sent emails:', error)
    } finally {
      setSentLoading(false)
    }
  }

  const saveConfig = async () => {
    setConfigLoading(true)
    try {
      const { data } = await api.post('/api/email/config', {
        ...config,
        test_connection: false
      })

      if (data.success) {
        setMsg({ type: 'success', text: '✓ Email configuration updated successfully' })
        setShowConfig(false)
        // Reload config to ensure it's applied
        setTimeout(() => loadConfig(), 500)
      } else {
        setMsg({ type: 'error', text: data.error || 'Failed to save configuration' })
      }
    } catch (error) {
      console.error('Error saving config:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Error saving configuration' })
    } finally {
      setConfigLoading(false)
    }
  }

  const testConnection = async () => {
    setTestingConnection(true)
    try {
      const { data } = await api.post('/api/email/config', {
        ...config,
        test_connection: true
      })

      if (data.test_result) {
        setTestResult(data.test_result)
      }
    } catch (error) {
      setTestResult(`✗ Error: ${error.response?.data?.error || error.message}`)
    } finally {
      setTestingConnection(false)
    }
  }

  const startCompose = (replyTo = null) => {
    setReplyingTo(replyTo)
    if (replyTo) {
      setDraftForm({
        to_address: replyTo.from_address,
        cc_address: '',
        bcc_address: '',
        subject: `Re: ${replyTo.subject}`,
        body: ''
      })
    } else {
      setDraftForm({
        to_address: '',
        cc_address: '',
        bcc_address: '',
        subject: '',
        body: ''
      })
    }
    setShowCompose(true)
  }

  const saveDraft = async () => {
    if (!draftForm.to_address.trim()) {
      Swal.fire('Error', 'Please enter a recipient email address', 'error')
      return
    }

    try {
      const response = await api.post('/api/email/drafts', {
        ...draftForm,
        in_reply_to: replyingTo?.id || null
      })

      if (response.data.success) {
        Swal.fire('Success', 'Draft saved', 'success')
        loadDrafts()
        setShowCompose(false)
        setDraftForm({
          to_address: '',
          cc_address: '',
          bcc_address: '',
          subject: '',
          body: ''
        })
      } else {
        Swal.fire('Error', response.data.error || 'Failed to save draft', 'error')
      }
    } catch (error) {
      Swal.fire('Error', error.response?.data?.error || error.message, 'error')
    }
  }

  const sendDirectEmail = async () => {
    if (!draftForm.to_address.trim()) {
      Swal.fire('Error', 'Please enter a recipient email address', 'error')
      return
    }

    if (!draftForm.subject.trim()) {
      Swal.fire('Error', 'Please enter a subject', 'error')
      return
    }

    setComposing(true)
    try {
      const response = await api.post('/api/email/send', {
        ...draftForm,
        in_reply_to: replyingTo?.id || null
      })

      if (response.data.success) {
        Swal.fire('Success', 'Email sent successfully', 'success')
        loadSentEmails(1, sentFilter)
        setShowCompose(false)
        setDraftForm({
          to_address: '',
          cc_address: '',
          bcc_address: '',
          subject: '',
          body: ''
        })
      } else {
        Swal.fire('Error', response.data.error || 'Failed to send email', 'error')
      }
    } catch (error) {
      Swal.fire('Error', error.response?.data?.error || error.message, 'error')
    } finally {
      setComposing(false)
    }
  }

  const generateAutoReply = async (emailId) => {
    setComposing(true)
    try {
      const response = await api.post('/api/email/auto-reply/generate', {
        email_id: emailId
      })

      if (response.data.success) {
        Swal.fire('Success', 'Auto-reply draft created with AI context', 'success')
        loadDrafts()
      } else {
        Swal.fire('Error', response.data.error || 'Failed to generate auto-reply', 'error')
      }
    } catch (error) {
      Swal.fire('Error', error.response?.data?.error || error.message, 'error')
    } finally {
      setComposing(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    Swal.fire({ title: 'Copied!', icon: 'success', timer: 1500, showConfirmButton: false })
  }

  // ========================================================================
  // RENDER - EMAIL MODAL
  // ========================================================================
  const EmailModal = () => {
    if (!showEmailModal || !selectedEmail) return null

    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Modal Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 truncate flex-1">
              {selectedEmail.subject || '(no subject)'}
            </h2>
            <button
              onClick={() => setShowEmailModal(false)}
              className="ml-4 text-gray-500 hover:text-gray-700"
            >
              <X size={24} />
            </button>
          </div>

          {/* Modal Body */}
          <div className="px-6 py-4 space-y-4">
            {/* From */}
            <div className="flex items-start gap-3 pb-3 border-b border-gray-100">
              <User size={20} className="text-gray-400 flex-shrink-0 mt-1" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">{selectedEmail.from_address}</p>
                <p className="text-xs text-gray-500">{selectedEmail.from_name || 'Sender'}</p>
              </div>
            </div>

            {/* Date */}
            <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
              <Clock size={20} className="text-gray-400" />
              <p className="text-sm text-gray-700">
                {new Date(selectedEmail.received_date).toLocaleString()}
              </p>
            </div>

            {/* Folder */}
            <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
              <Inbox size={20} className="text-gray-400" />
              <p className="text-sm text-gray-700">{selectedEmail.folder || 'INBOX'}</p>
            </div>

            {/* Email Body - Main Content */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 min-h-[200px]">
              {selectedEmail.body ? (
                <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {selectedEmail.body}
                </p>
              ) : selectedEmail.html_body ? (
                <div
                  className="text-sm text-gray-800 prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: selectedEmail.html_body }}
                />
              ) : (
                <p className="text-sm text-gray-500 italic">(no content)</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2 pt-4">
              <button
                onClick={() => {
                  startCompose(selectedEmail)
                  setShowEmailModal(false)
                }}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
              >
                <Mail size={16} /> Reply
              </button>

              {autoReplySettings.enabled && !selectedEmail.is_read && (
                <button
                  onClick={() => {
                    generateAutoReply(selectedEmail.id)
                    setShowEmailModal(false)
                  }}
                  disabled={composing}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
                >
                  {composing ? <Loader size={16} className="animate-spin" /> : <MessageSquare size={16} />}
                  AI Reply
                </button>
              )}

              <button
                onClick={() => copyToClipboard(selectedEmail.from_address)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition"
              >
                <Copy size={16} /> Copy Email
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ========================================================================
  // RENDER - MAIN LAYOUT
  // ========================================================================
  return (
    <div className="h-full flex flex-col bg-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Mail size={24} className="text-blue-600" />
          <h1 className="text-lg font-bold text-gray-900">Email</h1>
          {config.email_address && (
            <span className="text-xs text-gray-500">({config.email_address})</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadFolders().then(() => loadEmails())}
            disabled={loading}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
            title="Refresh"
          >
            {loading ? <Loader size={20} className="animate-spin text-blue-600" /> : <RefreshCw size={20} className="text-gray-600" />}
          </button>
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
            title="Settings"
          >
            <Settings size={20} className="text-gray-600" />
          </button>
        </div>
      </div>

      {/* Messages */}
      {msg && (
        <div className={`mx-4 mt-3 p-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {msg.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {msg.text}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Folders */}
        {sidebarOpen && (
          <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto">
            <div className="p-4 space-y-2">
              {/* Compose Button */}
              <button
                onClick={() => startCompose()}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition flex items-center justify-center gap-2 mb-4"
              >
                <Mail size={18} /> Compose
              </button>

              {/* Folders List */}
              <p className="text-xs font-semibold text-gray-500 uppercase px-2 mt-4 mb-2">Folders</p>
              {folders.map(f => (
                <button
                  key={f}
                  onClick={() => {
                    setFolder(f)
                    setCurrentPage(1)
                    setViewMode('inbox')
                  }}
                  className={`w-full text-left px-4 py-2 rounded-lg transition flex items-center justify-between ${
                    folder === f && viewMode === 'inbox'
                      ? 'bg-blue-100 text-blue-700 font-semibold'
                      : 'hover:bg-gray-100 text-gray-700'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Inbox size={16} />
                    {f}
                  </span>
                  <ChevronRight size={16} className={folder === f ? 'opacity-100' : 'opacity-0'} />
                </button>
              ))}

              {/* View Modes */}
              <p className="text-xs font-semibold text-gray-500 uppercase px-2 mt-6 mb-2">Views</p>
              
              <button
                onClick={() => setViewMode('drafts')}
                className={`w-full text-left px-4 py-2 rounded-lg transition flex items-center justify-between ${
                  viewMode === 'drafts'
                    ? 'bg-blue-100 text-blue-700 font-semibold'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <span className="flex items-center gap-2">
                  <FileText size={16} />
                  Drafts ({drafts.length})
                </span>
                <ChevronRight size={16} className={viewMode === 'drafts' ? 'opacity-100' : 'opacity-0'} />
              </button>

              <button
                onClick={() => { setViewMode('sent'); setSentFilter('all'); loadSentEmails(1, 'all') }}
                className={`w-full text-left px-4 py-2 rounded-lg transition flex items-center justify-between ${
                  viewMode === 'sent'
                    ? 'bg-blue-100 text-blue-700 font-semibold'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Send size={16} />
                  Sent
                </span>
                <ChevronRight size={16} className={viewMode === 'sent' ? 'opacity-100' : 'opacity-0'} />
              </button>
            </div>
          </div>
        )}

        {/* Right Side - Email List or Detail */}
        <div className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
          {/* Toolbar */}
          {viewMode === 'inbox' && (
            <div className="bg-white border-b border-gray-200 p-4 space-y-3">
              {/* Search Bar */}
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search emails..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value)
                      setCurrentPage(1)
                    }}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Per Page</label>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sort</label>
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
                </div>

                <div className="flex items-end">
                  <button
                    onClick={() => { setCurrentPage(1); loadEmails() }}
                    disabled={loading}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
                  >
                    {loading ? <Loader size={16} className="animate-spin" /> : null}
                    Load
                  </button>
                </div>
              </div>

              {lastRefresh && (
                <p className="text-xs text-gray-500">
                  Last refreshed: {lastRefresh} • Total: {totalEmails} emails
                </p>
              )}
            </div>
          )}

          {/* Email List View */}
          {viewMode === 'inbox' && (
            <div className="flex-1 overflow-y-auto">
              {loading && filteredEmails.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <Loader size={48} className="animate-spin mb-3 text-blue-600" />
                  <p>Loading emails...</p>
                </div>
              ) : filteredEmails.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <Mail size={48} className="mb-3 text-gray-300" />
                  <p>No emails found</p>
                </div>
              ) : (
                <div className="bg-white">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 w-12"></th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">From</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Subject</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Date</th>
                        <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 w-12">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEmails.map((email, idx) => (
                        <tr
                          key={email.id}
                          onClick={() => handleSelectEmail(email)}
                          className={`border-b border-gray-100 hover:bg-blue-50 cursor-pointer transition ${
                            !email.is_read ? 'bg-blue-50 font-semibold' : ''
                          }`}
                        >
                          <td className="px-4 py-3 text-center">
                            {!email.is_read && <div className="w-2 h-2 bg-blue-600 rounded-full mx-auto"></div>}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                            {email.from_address}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-800 max-w-lg truncate">
                            {email.subject || '(no subject)'}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                            {new Date(email.received_date).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {!email.is_read && (
                              <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded font-medium">
                                Unread
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="bg-white border-t border-gray-200 p-4 flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    Page <span className="font-semibold">{currentPage}</span> of <span className="font-semibold">{totalPages}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1 || loading}
                      className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                    >
                      First
                    </button>
                    <button
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1 || loading}
                      className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === totalPages || loading}
                      className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                    >
                      Next
                    </button>
                    <button
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages || loading}
                      className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded transition"
                    >
                      Last
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Drafts View */}
          {viewMode === 'drafts' && (
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Drafts</h2>
                <button
                  onClick={() => startCompose()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition flex items-center gap-2"
                >
                  <Mail size={16} /> New Draft
                </button>
              </div>

              {draftsLoading ? (
                <div className="flex justify-center py-12">
                  <Loader size={32} className="animate-spin text-blue-600" />
                </div>
              ) : drafts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <FileText size={48} className="text-gray-300 mx-auto mb-3" />
                  <p>No drafts</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {drafts.map(draft => (
                    <div key={draft.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900">To: {draft.to_address}</p>
                          {draft.cc_address && <p className="text-xs text-gray-600">CC: {draft.cc_address}</p>}
                          {draft.bcc_address && <p className="text-xs text-gray-600">BCC: {draft.bcc_address}</p>}
                          <p className="text-sm text-gray-700 font-semibold">{draft.subject}</p>
                        </div>
                        <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded font-medium">
                          DRAFT
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 line-clamp-2 mb-3">{draft.body}</p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setDraftForm(draft)
                            setShowCompose(true)
                          }}
                          className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => {
                            setDraftForm(draft)
                            sendDirectEmail()
                          }}
                          className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 text-white rounded transition flex items-center gap-1"
                        >
                          <Send size={12} /> Send
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Sent View */}
          {viewMode === 'sent' && (
            <div className="flex-1 overflow-y-auto p-4">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Sent Emails</h2>
                
                {/* Filter Buttons */}
                <div className="flex gap-2 flex-wrap mb-4">
                  <button
                    onClick={() => { setSentFilter('all'); loadSentEmails(1, 'all') }}
                    className={`px-4 py-2 rounded-lg font-medium transition ${
                      sentFilter === 'all'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    All ({sentStats.total})
                  </button>
                  <button
                    onClick={() => { setSentFilter('ai_only'); loadSentEmails(1, 'ai_only') }}
                    className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                      sentFilter === 'ai_only'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    🤖 AI Auto-Replies ({sentStats.ai})
                  </button>
                  <button
                    onClick={() => { setSentFilter('replies'); loadSentEmails(1, 'replies') }}
                    className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                      sentFilter === 'replies'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    ↩️ Manual Replies ({sentStats.replies})
                  </button>
                  <button
                    onClick={() => { setSentFilter('pending'); loadSentEmails(1, 'pending') }}
                    className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                      sentFilter === 'pending'
                        ? 'bg-yellow-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    📤 Outbox ({sentStats.pending})
                  </button>
                  <button
                    onClick={() => { setSentFilter('failed'); loadSentEmails(1, 'failed') }}
                    className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                      sentFilter === 'failed'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    ❌ Failed ({sentStats.failed})
                  </button>
                </div>
              </div>

              {sentLoading ? (
                <div className="flex justify-center py-12">
                  <Loader size={32} className="animate-spin text-blue-600" />
                </div>
              ) : sentEmails.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Send size={48} className="text-gray-300 mx-auto mb-3" />
                  <p>No {sentFilter !== 'all' ? sentFilter + ' ' : ''}sent emails</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sentEmails.map(email => (
                    <div key={email.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1 min-w-0">
                          {/* Recipients */}
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-sm font-medium text-gray-900">To: {email.to_address}</p>
                            {/* Status Badge */}
                            {email.status === 'sent' && (
                              <span className="inline-block text-xs bg-green-100 text-green-800 px-2 py-1 rounded font-medium">
                                ✓ Sent
                              </span>
                            )}
                            {email.status === 'failed' && (
                              <span className="inline-block text-xs bg-red-100 text-red-800 px-2 py-1 rounded font-medium">
                                ✗ Failed
                              </span>
                            )}
                            {email.status === 'pending' && (
                              <span className="inline-block text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded font-medium">
                                ⏳ Pending
                              </span>
                            )}
                          </div>

                          {/* CC/BCC */}
                          {email.cc_address && <p className="text-xs text-gray-600">CC: {email.cc_address}</p>}
                          {email.bcc_address && <p className="text-xs text-gray-600">BCC: {email.bcc_address}</p>}

                          {/* Subject */}
                          <p className="text-sm text-gray-700 font-semibold">{email.subject}</p>

                          {/* Metadata */}
                          <div className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                            <span>Sent: {new Date(email.sent_at).toLocaleString()}</span>
                            {email.ai_generated && (
                              <span className="inline-block bg-purple-100 text-purple-800 px-2 py-1 rounded font-medium">
                                🤖 AI Generated
                              </span>
                            )}
                            {email.in_reply_to && (
                              <span className="inline-block bg-green-100 text-green-800 px-2 py-1 rounded font-medium">
                                ↩️ Reply to Email #{email.in_reply_to}
                              </span>
                            )}
                            {email.from_draft && (
                              <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium">
                                📝 From Draft #{email.from_draft}
                              </span>
                            )}
                          </div>

                          {/* Error Message */}
                          {email.error_message && (
                            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                              <p className="font-medium">Error:</p>
                              <p>{email.error_message}</p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Email Body Preview */}
                      <p className="text-sm text-gray-700 line-clamp-3 bg-gray-50 p-2 rounded">{email.body}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {sentTotalPages > 1 && (
                <div className="mt-4 flex gap-2 justify-center">
                  <button
                    onClick={() => loadSentEmails(1, sentFilter)}
                    disabled={sentPage === 1 || sentLoading}
                    className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded"
                  >
                    First
                  </button>
                  <button
                    onClick={() => loadSentEmails(sentPage - 1, sentFilter)}
                    disabled={sentPage === 1 || sentLoading}
                    className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1 text-sm">Page {sentPage} of {sentTotalPages}</span>
                  <button
                    onClick={() => loadSentEmails(sentPage + 1, sentFilter)}
                    disabled={sentPage === sentTotalPages || sentLoading}
                    className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded"
                  >
                    Next
                  </button>
                  <button
                    onClick={() => loadSentEmails(sentTotalPages, sentFilter)}
                    disabled={sentPage === sentTotalPages || sentLoading}
                    className="px-3 py-1 text-sm bg-gray-300 hover:bg-gray-400 disabled:opacity-50 text-gray-800 rounded"
                  >
                    Last
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Compose Modal */}
      {showCompose && (
        <div className="fixed inset-0 bg-black/50 z-40 flex items-end">
          <div className="bg-white w-full rounded-t-lg shadow-xl">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                {replyingTo ? `Reply to ${replyingTo.from_address}` : 'New Email'}
              </h2>
              <button
                onClick={() => setShowCompose(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={24} />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
                <input
                  type="email"
                  value={draftForm.to_address}
                  onChange={(e) => setDraftForm({ ...draftForm, to_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="recipient@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CC (optional)</label>
                <input
                  type="email"
                  value={draftForm.cc_address}
                  onChange={(e) => setDraftForm({ ...draftForm, cc_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="cc@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">BCC (optional)</label>
                <input
                  type="email"
                  value={draftForm.bcc_address}
                  onChange={(e) => setDraftForm({ ...draftForm, bcc_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="bcc@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                <input
                  type="text"
                  value={draftForm.subject}
                  onChange={(e) => setDraftForm({ ...draftForm, subject: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Email subject"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
                <textarea
                  value={draftForm.body}
                  onChange={(e) => setDraftForm({ ...draftForm, body: e.target.value })}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  placeholder="Write your message..."
                />
              </div>
            </div>

            <div className="border-t border-gray-200 px-6 py-4 flex gap-2 justify-end">
              <button
                onClick={() => setShowCompose(false)}
                className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition"
              >
                Cancel
              </button>
              <button
                onClick={saveDraft}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition"
              >
                Save Draft
              </button>
              <button
                onClick={sendDirectEmail}
                disabled={composing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {composing ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Email Modal */}
      <EmailModal />

      {/* Settings Modal */}
      {showConfig && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="text-lg font-semibold text-gray-900">Email Configuration</h2>
              <button
                onClick={() => setShowConfig(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={24} />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={config.email_address}
                  onChange={(e) => setConfig({ ...config, email_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="your-email@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div className="flex gap-2">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={config.email_password}
                    onChange={(e) => setConfig({ ...config, email_password: e.target.value })}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Email password or app password"
                  />
                  <button
                    onClick={() => setShowPassword(!showPassword)}
                    className="p-2 hover:bg-gray-100 rounded"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email Provider</label>
                <select
                  value={config.email_provider}
                  onChange={(e) => {
                    const provider = e.target.value
                    setConfig({ ...config, email_provider: provider })
                    if (providers[provider]) {
                      const p = providers[provider]
                      setConfig(prev => ({
                        ...prev,
                        email_provider: provider,
                        imap_server: p.imap_server || prev.imap_server,
                        imap_port: p.imap_port || prev.imap_port,
                        smtp_server: p.smtp_server || prev.smtp_server,
                        smtp_port: p.smtp_port || prev.smtp_port,
                      }))
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.keys(providers).map(p => (
                    <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">IMAP Server</label>
                  <input
                    type="text"
                    value={config.imap_server}
                    onChange={(e) => setConfig({ ...config, imap_server: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">IMAP Port</label>
                  <input
                    type="number"
                    value={config.imap_port}
                    onChange={(e) => setConfig({ ...config, imap_port: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Server</label>
                  <input
                    type="text"
                    value={config.smtp_server}
                    onChange={(e) => setConfig({ ...config, smtp_server: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Port</label>
                  <input
                    type="number"
                    value={config.smtp_port}
                    onChange={(e) => setConfig({ ...config, smtp_port: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {testResult && (
                <div className={`p-3 rounded-lg text-sm ${
                  testResult.includes('✓')
                    ? 'bg-green-50 text-green-800 border border-green-200'
                    : 'bg-red-50 text-red-800 border border-red-200'
                }`}>
                  {testResult}
                </div>
              )}
            </div>

            <div className="border-t border-gray-200 px-6 py-4 flex gap-2 justify-end sticky bottom-0 bg-white">
              <button
                onClick={() => setShowConfig(false)}
                className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition"
              >
                Cancel
              </button>
              <button
                onClick={testConnection}
                disabled={testingConnection || configLoading}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition"
              >
                {testingConnection ? <Loader size={16} className="animate-spin" /> : <Wifi size={16} />}
                Test Connection
              </button>
              <button
                onClick={saveConfig}
                disabled={configLoading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {configLoading ? <Loader size={16} className="animate-spin" /> : null}
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
