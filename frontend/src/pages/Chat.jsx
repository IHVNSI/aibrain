import React, { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import api, { handleApiError } from '../api/client'
import {
  Send, Plus, Trash2, RotateCcw, Loader, Code, AlertCircle, Sparkles,
  TrendingUp, TrendingDown, Minus, Lightbulb, BarChart3, Table as TableIcon,
  Copy, Mic, MicOff, Eye, RefreshCw, Pencil, Volume2, Download, Share2, Square,
  Menu, X
} from 'lucide-react'
import { useReactTable, getCoreRowModel, getPaginationRowModel, flexRender, createColumnHelper } from '@tanstack/react-table'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Swal from 'sweetalert2'
import ChartRenderer from '../components/ChartRenderer'
import { formatColumnName, copyToClipboard, exportAsImage, speakText } from '../utils/formatters'
import { useAuth } from '../contexts/AuthContext'
import { useSidebar } from '../contexts/SidebarContext'

async function confirmDeleteAction(text) {
  const result = await Swal.fire({
    title: 'Confirm delete',
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    confirmButtonColor: '#dc2626',
  })
  return result.isConfirmed
}

export default function Chat() {
  const { user } = useAuth()
  const { sidebarOpen, setSidebarOpen } = useSidebar()
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [interimText, setInterimText] = useState('')
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [shareCopied, setShareCopied] = useState(false)
  const [voiceError, setVoiceError] = useState('')
  const [autoSpeak, setAutoSpeak] = useState(() => {
    try { return localStorage.getItem('chatAutoSpeak') === '1' } catch (_) { return false }
  })
  const [editingConvId, setEditingConvId] = useState(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [audioSettings, setAudioSettings] = useState({
    voiceGender: 'female',
    pitch: 1,
    rate: 1,
    volume: 1,
    voiceInputLanguage: 'english',
    sttModel: 'whisper',
  })
  const [voiceInputOriginal, setVoiceInputOriginal] = useState('')
  const [voiceInputTranslated, setVoiceInputTranslated] = useState('')
  const [showTranslation, setShowTranslation] = useState(false)
  
  const VOICE_INPUT_LANGUAGES = [
    { code: 'english', label: 'English' },
    { code: 'igbo', label: 'Igbo' },
    { code: 'hausa', label: 'Hausa' },
    { code: 'yoruba', label: 'Yoruba' },
    { code: 'pidgin', label: 'Nigerian Pidgin' },
  ]
  const canVoice = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  const endRef = useRef(null)
  const recognitionRef = useRef(null)
  const sharedConversationRef = useRef(false)
  const voiceRetryRef = useRef(0)
  const listeningRef = useRef(false)
  const sendAfterStopRef = useRef(false)
  const baseInputRef = useRef('')
  const finalTranscriptRef = useRef('')
  const composedInputRef = useRef('')
  const historyIndexRef = useRef(-1)
  const draftInputRef = useRef('')
  const manualEditRef = useRef(false)
  const inputAtListeningStartRef = useRef('')

  const composeVoiceText = (interim = '') => {
    const text = [baseInputRef.current, finalTranscriptRef.current, interim]
      .map((part) => String(part || '').trim())
      .filter(Boolean)
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
    composedInputRef.current = text
    return text
  }

  useEffect(() => { loadConversations() }, [])
  useEffect(() => {
    listeningRef.current = listening
  }, [listening])
  useEffect(() => {
    const handleResize = () => {
      if (typeof window !== 'undefined' && window.innerWidth >= 768) {
        setSidebarOpen(true)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  useEffect(() => {
    try {
      localStorage.setItem('chatAutoSpeak', autoSpeak ? '1' : '0')
    } catch (_) {
      // no-op
    }
  }, [autoSpeak])
  
  // Load user audio settings from API
  useEffect(() => {
    const loadAudioSettings = async () => {
      try {
        const { data } = await api.get('/api/settings/user')
        if (data.settings && data.settings.audio_settings) {
          setAudioSettings(data.settings.audio_settings)
        }
      } catch (e) {
        console.error('Failed to load audio settings:', e)
      }
    }
    loadAudioSettings()
  }, [])
  
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    if (sharedConversationRef.current) return
    const params = new URLSearchParams(window.location.search)
    const sharedId = params.get('conversation_id')
    if (sharedId) {
      sharedConversationRef.current = true
      openConversation(sharedId)
    } else {
      // Load last conversation from localStorage on page reload
      const lastConvId = localStorage.getItem('lastConversationId')
      if (lastConvId) {
        openConversation(lastConvId)
      }
    }
  }, [])
  useEffect(() => {
    if (!canVoice || recognitionRef.current) return
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    
    // Map audio settings language to browser language code
    const langMap = {
      'english': 'en-US',
      'igbo': 'ig-NG',
      'hausa': 'ha-NG',
      'yoruba': 'yo-NG',
    }
    recognition.lang = langMap[audioSettings.voiceInputLanguage] || 'en-US'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.maxAlternatives = 1
    recognition.onstart = () => setVoiceError('')
    recognition.onresult = (event) => {
      voiceRetryRef.current = 0
      let interim = ''
      let finalChunk = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalChunk += transcript + ' '
        } else {
          interim += transcript + ' '
        }
      }
      
      // Handle "Clear Text" command
      if (finalChunk) {
        const clearTextMatch = finalChunk.toLowerCase().match(/\bclear\s+text\b/i)
        if (clearTextMatch) {
          // Remove "clear text" from the transcript
          finalChunk = finalChunk.replace(/\bclear\s+text\b/i, '').trim()
          // Clear all input and refs
          baseInputRef.current = ''
          finalTranscriptRef.current = finalChunk
          manualEditRef.current = false
          setInput('')
          setInterimText('')
          return
        }
        finalTranscriptRef.current = [finalTranscriptRef.current, finalChunk.trim()].filter(Boolean).join(' ').trim()
      }
      
      const composed = composeVoiceText(interim)
      setInput(composed)
      setInterimText(interim.trim())
    }
    recognition.onend = () => {
      setInterimText('')
      if (sendAfterStopRef.current) {
        sendAfterStopRef.current = false
        setListening(false)
        
        // If user manually edited the input, use current value instead of reverting
        const textToSend = manualEditRef.current ? input : (composedInputRef.current || composeVoiceText(''))
        manualEditRef.current = false
        
        if (textToSend) {
          send(textToSend)
          setInput('')
        }
        return
      }
      if (listeningRef.current && recognitionRef.current) {
        try {
          recognitionRef.current.start()
        } catch (err) {
          setListening(false)
        }
        return
      }
      setListening(false)
    }
    recognition.onerror = (event) => {
      const err = event?.error || 'Voice input failed'
      if (err === 'no-speech' && listeningRef.current && voiceRetryRef.current < 2) {
        voiceRetryRef.current += 1
        setVoiceError('Listening... speak a little louder')
        try {
          recognition.stop()
          recognition.start()
        } catch (e) {
          setListening(false)
        }
        return
      }
      setListening(false)
      setVoiceError(err)
    }
    recognitionRef.current = recognition
  }, [canVoice])

  const loadConversations = async () => {
    try {
      const { data } = await api.get('/api/conversations')
      setConversations(data.conversations || [])
    } catch (e) { /* ignore */ }
  }

  const openConversation = async (id) => {
    try {
      const { data } = await api.get(`/api/conversations/${id}`)
      setConversationId(id)
      setMessages(data.conversation?.messages || [])
      localStorage.setItem('lastConversationId', id)
      if (window.innerWidth < 768) setSidebarOpen(false)
    } catch (e) {
      localStorage.removeItem('lastConversationId')
    }
  }

  const newConversation = () => {
    setConversationId(null)
    setMessages([])
    setInput('')
    localStorage.removeItem('lastConversationId')
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const deleteConversation = async (id, e) => {
    e.stopPropagation()
    if (!(await confirmDeleteAction('Delete this conversation?'))) return
    await api.delete(`/api/conversations/${id}`)
    if (id === conversationId) newConversation()
    loadConversations()
  }

  const renameConversation = async (id, newTitle) => {
    if (!newTitle.trim()) return
    try {
      await api.post(`/api/conversations/${id}/rename`, { title: newTitle.trim() })
      setEditingConvId(null)
      setEditingTitle('')
      loadConversations()
    } catch (e) {
      console.error('Rename failed:', e)
    }
  }

  const startEditingTitle = (e, id, currentTitle) => {
    e.stopPropagation()
    setEditingConvId(id)
    setEditingTitle(currentTitle)
  }

  const send = async (text) => {
    const q = (text ?? input).trim()
    if (!q || loading) return
    historyIndexRef.current = -1
    draftInputRef.current = ''
    setMessages((prev) => [...prev, { type: 'user', content: q }])
    setInput('')
    setLoading(true)
    try {
      const isGuest = (user?.username || '').toLowerCase() === 'guest'
      const endpoint = isGuest ? '/api/chat/query/guest' : '/api/chat/query'
      // Determine if this is the first message in the conversation
      const isFirstMessage = messages.length === 0 || (!conversationId)
      const { data } = await api.post(endpoint, {
        query: q,
        conversation_id: conversationId,
        is_first_message: isFirstMessage,
      })
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id)
        localStorage.setItem('lastConversationId', data.conversation_id)
        loadConversations()
      }
      setMessages((prev) => [...prev, {
        type: 'ai',
        content: data.message,
        source_query: q,
        sql_query: data.sql_query,
        columns: data.columns,
        data: data.data,
        row_count: data.row_count,
        rewritten_query: data.rewritten_query,
        rewrite_info: data.rewrite_info,
        success: data.success,
        error: data.error,
        visualization: data.visualization,
        trend: data.trend,
        insights: data.insights,
        corrections: data.corrections,
        llm_provider: data.llm_provider,
        llm_model: data.llm_model,
        is_first_message: data.is_first_message,
        message_position: data.message_position,
      }])
      if (autoSpeak && data.message) {
        speakText(data.message, audioSettings)
      }
      loadConversations()
    } catch (error) {
      const err = handleApiError(error)
      setMessages((prev) => [...prev, { type: 'error', content: err.message, failedQuery: q, canRetry: true }])
    } finally {
      setLoading(false)
    }
  }

  const updateConversationMessages = async (nextMessages) => {
    setMessages(nextMessages)
    if (!conversationId) return
    try {
      await api.patch(`/api/conversations/${conversationId}/messages`, { messages: nextMessages })
    } catch (e) {
      // Ignore persistence errors to avoid blocking UI edits.
    }
  }

  const deleteMessage = async (index) => {
    const next = messages.filter((_, i) => i !== index)
    await updateConversationMessages(next)
  }

  const editMessage = async (index, nextContent) => {
    if (!nextContent) return
    const next = messages.map((m, i) => (i === index ? { ...m, content: nextContent } : m))
    await updateConversationMessages(next)
  }

  const refreshMessage = async (index) => {
    const msg = messages[index]
    if (!msg?.sql_query) return
    try {
      const { data } = await api.post('/api/chat/refresh', { sql_query: msg.sql_query })
      const next = messages.map((m, i) => (i === index ? {
        ...m,
        columns: data.columns,
        data: data.data,
        row_count: data.row_count,
        visualization: data.visualization,
        trend: data.trend,
        insights: data.insights,
        error: data.error,
      } : m))
      await updateConversationMessages(next)
    } catch (error) {
      // ignore refresh failures
    }
  }

  const refreshAll = async () => {
    const targets = messages
      .map((m, i) => ({ m, i }))
      .filter(({ m }) => m?.sql_query)
    if (!targets.length || refreshing) return
    setRefreshing(true)
    try {
      const updates = await Promise.all(targets.map(async ({ m, i }) => {
        const { data } = await api.post('/api/chat/refresh', { sql_query: m.sql_query })
        return { i, data }
      }))
      const next = messages.map((m, i) => {
        const found = updates.find((u) => u.i === i)
        if (!found) return m
        return {
          ...m,
          columns: found.data.columns,
          data: found.data.data,
          row_count: found.data.row_count,
          visualization: found.data.visualization,
          trend: found.data.trend,
          insights: found.data.insights,
          error: found.data.error,
        }
      })
      await updateConversationMessages(next)
    } catch (e) {
      // ignore refresh failures
    } finally {
      setRefreshing(false)
    }
  }

  const shareConversation = async () => {
    if (!conversationId) return
    const url = `${window.location.origin}/chat?conversation_id=${conversationId}`
    if (await copyToClipboard(url)) {
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 1200)
    }
  }

  const toggleListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return
    if (listening && recognitionRef.current) {
      sendAfterStopRef.current = true
      recognitionRef.current.stop()
      setInterimText('')
      return
    }
    const recognition = recognitionRef.current || new SpeechRecognition()
    recognitionRef.current = recognition
    try {
      setVoiceError('')
      baseInputRef.current = (input || '').trim()
      finalTranscriptRef.current = ''
      composedInputRef.current = baseInputRef.current
      inputAtListeningStartRef.current = input.trim()
      manualEditRef.current = false
      sendAfterStopRef.current = false
      setListening(true)
      recognition.start()
    } catch (err) {
      setListening(false)
      const reason = String(err?.message || '').toLowerCase().includes('not-allowed')
        ? 'Microphone permission denied'
        : 'Voice input failed to start'
      setVoiceError(reason)
    }
  }

  const changeVoiceInputLanguage = async (newLanguage) => {
    const newSettings = { ...audioSettings, voiceInputLanguage: newLanguage }
    setAudioSettings(newSettings)
    
    // Save to localStorage
    try {
      localStorage.setItem('voiceInputLanguage', newLanguage)
    } catch (_) {
      // no-op
    }
    
    // Save to backend
    try {
      await api.post('/api/settings/user', { audio_settings: newSettings })
    } catch (e) {
      console.error('Failed to save voice language preference:', e)
    }
  }

  const retry = (msg) => {
    setMessages((prev) => prev.filter((m) => m !== msg))
    send(msg.failedQuery)
  }

  const history = useMemo(
    () => messages.filter((m) => m.type === 'user').map((m) => m.content).filter(Boolean),
    [messages]
  )

  const handleInputHistory = (e) => {
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return
    if (e.shiftKey) return
    if (!history.length) return
    e.preventDefault()
    const direction = e.key === 'ArrowUp' ? -1 : 1
    let idx = historyIndexRef.current
    if (idx === -1) {
      draftInputRef.current = input
      idx = history.length
    }
    idx += direction
    if (idx < 0) idx = 0
    if (idx > history.length) idx = history.length
    historyIndexRef.current = idx
    if (idx === history.length) {
      setInput(draftInputRef.current)
    } else {
      setInput(history[idx])
    }
  }

  return (
    <div className="flex h-[calc(100dvh-57px)] min-h-[520px] relative overflow-hidden">
      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(false)}
          className="md:hidden fixed inset-0 bg-black/30 z-30"
          aria-label="Close sidebar overlay"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-[84vw] max-w-xs md:w-64 border-r border-gray-200 bg-white flex flex-col transition-transform duration-200 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Toggle Button - Top Left */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <button onClick={newConversation} className="btn-primary flex-1 flex items-center justify-center gap-1 text-sm">
            <Plus size={16} /> New chat
          </button>
          <button
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="md:hidden ml-2 p-2 rounded transition"
            title={sidebarOpen ? 'Hide history' : 'Show history'}
          >
            <X size={16} className="text-gray-600" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
          {conversations.map((c) => (
            <div key={c.id}>
              {editingConvId === c.id ? (
                <div className="px-3 py-2 rounded-lg bg-brand-50 space-y-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        renameConversation(c.id, editingTitle)
                      } else if (e.key === 'Escape') {
                        setEditingConvId(null)
                        setEditingTitle('')
                      }
                    }}
                    className="w-full px-2 py-1 text-xs rounded border border-brand-200 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    autoFocus
                  />
                  <div className="flex gap-1 justify-end">
                    <button
                      onClick={() => renameConversation(c.id, editingTitle)}
                      className="text-xs px-2 py-1 rounded bg-brand-600 text-white hover:bg-brand-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingConvId(null)
                        setEditingTitle('')
                      }}
                      className="text-xs px-2 py-1 rounded text-gray-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onClick={() => openConversation(c.id)}
                  className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm ${
                    c.id === conversationId ? 'bg-brand-50 text-brand-700' : 'text-gray-700'
                  }`}
                >
                  <span className="truncate flex-1">{c.title}</span>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100">
                    <button
                      onClick={(e) => startEditingTitle(e, c.id, c.title)}
                      className="text-gray-400 hover:text-brand-600"
                      title="Rename"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={(e) => deleteConversation(c.id, e)}
                      className="text-gray-400 hover:text-red-500"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-xs text-gray-400 px-3 py-2">No conversations yet.</p>
          )}
        </div>
      </aside>

      {/* Main */}
      <section className="flex-1 flex flex-col min-w-0">
        {/* Menu Toggle */}
        <div className="bg-white border-b border-gray-200 px-3 py-2">
          <button
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="p-2 rounded transition hidden md:block"
            title={sidebarOpen ? 'Hide history' : 'Show history'}
          >
            {sidebarOpen ? <Minus size={16} className="text-gray-600" /> : <Menu size={16} className="text-gray-600" />}
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-4">
          {messages.some((m) => m.sql_query) && (
            <div className="flex justify-end items-center gap-3">
              <label className="inline-flex items-center gap-2 text-xs text-gray-600 select-none">
                <input
                  type="checkbox"
                  checked={autoSpeak}
                  onChange={(e) => setAutoSpeak(e.target.checked)}
                />
                Auto-voice response
              </label>
              <div className="flex items-center gap-2">
                {conversationId && (
                  <button
                    onClick={shareConversation}
                    className="btn-secondary text-xs flex items-center gap-1"
                  >
                    <Share2 size={12} /> Share page
                  </button>
                )}
                <button
                  onClick={refreshAll}
                  disabled={refreshing}
                  className="btn-secondary text-xs flex items-center gap-1"
                >
                  <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
                  Update all data
                </button>
                {shareCopied && <span className="text-[11px] text-green-600">Link copied</span>}
              </div>
            </div>
          )}
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <Sparkles size={36} className="mb-3 text-brand-300" />
              <p className="text-sm">Ask a question about your data. Follow-ups are understood as continuations.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              index={i}
              m={m}
              onRetry={() => retry(m)}
              onDelete={deleteMessage}
              onEdit={editMessage}
              onRefresh={refreshMessage}
              onResend={send}
              loading={loading}
              audioSettings={audioSettings}
            />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Loader size={16} className="animate-spin" /> Generating Response…
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-gray-200 bg-white p-2 sm:p-3">
          <div className="flex items-end gap-2 max-w-4xl mx-auto">
            <div className="flex-1">
              <div className="space-y-2">
                {/* Voice input language selector */}
                {canVoice && (
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-medium text-gray-600">Voice Language:</label>
                    <select
                      value={audioSettings.voiceInputLanguage}
                      onChange={(e) => changeVoiceInputLanguage(e.target.value)}
                      className="text-xs px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {VOICE_INPUT_LANGUAGES.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                          {lang.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                {/* Main input textarea */}
                <textarea
                  value={input}
                  onChange={(e) => {
                    const newValue = e.target.value
                    setInput(newValue)
                    // Track if user is manually editing during voice listening
                    if (listeningRef.current && newValue !== composedInputRef.current) {
                      manualEditRef.current = true
                    }
                  }}
                  onKeyDown={(e) => {
                    handleInputHistory(e)
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
                  }}
                  rows={1}
                  placeholder="Ask about your data… (e.g. how many orders last month)"
                  className="input resize-none w-full"
                />
                
                {/* Voice input language indicator */}
                {audioSettings.voiceInputLanguage && audioSettings.voiceInputLanguage !== 'english' && (
                  <div className="flex items-center gap-2 text-xs text-gray-500 px-2">
                    <span className="inline-block px-2 py-1 bg-purple-100 text-purple-700 rounded">
                      🎙️ Voice input: {audioSettings.voiceInputLanguage.charAt(0).toUpperCase() + audioSettings.voiceInputLanguage.slice(1)}
                    </span>
                  </div>
                )}
                
                {/* Interim text display */}
                {interimText && (
                  <div className="text-xs text-gray-400 italic px-2">
                    Listening: {interimText}
                  </div>
                )}
                
                {/* Translation toggle and display */}
                {audioSettings.voiceInputLanguage && audioSettings.voiceInputLanguage !== 'english' && input.trim() && (
                  <div className="space-y-2">
                    <button
                      onClick={async () => {
                        if (!showTranslation) {
                          // Translate the input
                          try {
                            const { data } = await api.post('/api/chat/translate-text', {
                              text: input,
                              source_language: audioSettings.voiceInputLanguage,
                              target_language: 'english'
                            })
                            if (data.success) {
                              setVoiceInputTranslated(data.translated_text)
                              setVoiceInputOriginal(input)
                            }
                          } catch (e) {
                            console.error('Translation error:', e)
                          }
                        }
                        setShowTranslation(!showTranslation)
                      }}
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded border border-blue-200"
                    >
                      {showTranslation ? '▼ Hide English translation' : '▶ Show English translation'}
                    </button>
                    
                    {showTranslation && voiceInputTranslated && (
                      <div className="bg-blue-50 border border-blue-200 rounded p-2">
                        <p className="text-xs font-medium text-blue-900 mb-1">English Translation:</p>
                        <p className="text-xs text-blue-800">{voiceInputTranslated}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={toggleListening}
              disabled={!canVoice}
              className="btn-secondary flex items-center gap-1 flex-shrink-0"
              title={canVoice ? (listening ? 'Click to stop listening and send' : 'Voice prompt') : 'Voice input not supported'}
            >
              {listening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
            <button onClick={() => send()} disabled={loading || !input.trim()} className="btn-primary flex items-center gap-1 flex-shrink-0">
              <Send size={16} /> Send
            </button>
          </div>
          {voiceError && (
            <p className="mt-2 text-[11px] text-amber-600">Voice input error: {voiceError}</p>
          )}
        </div>
      </section>
    </div>
  )
}

function MessageBubble({ m, index, onRetry, onDelete, onEdit, onRefresh, onResend, loading, audioSettings }) {
  const [editingPrompt, setEditingPrompt] = useState(false)
  const [editText, setEditText] = useState(m.content || '')
  const [copied, setCopied] = useState(false)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)

  const handleCopy = async () => {
    if (await copyToClipboard(m.content)) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    }
  }

  const handleDelete = async () => {
    if (!(await confirmDeleteAction('Delete this message?'))) return
    onDelete(index)
  }

  const handleEditSubmit = async () => {
    await onEdit(index, editText.trim())
    setEditingPrompt(false)
    // Resend the edited prompt to regenerate response
    onResend?.(editText.trim())
  }

  const handleVoice = () => {
    const synth = window.speechSynthesis
    if (isAudioPlaying) {
      synth.cancel()
      setIsAudioPlaying(false)
    } else {
      speakText(m.content, audioSettings)
      setIsAudioPlaying(true)
      
      // Listen for when speech ends
      const checkSpeechEnd = setInterval(() => {
        if (!synth.speaking) {
          setIsAudioPlaying(false)
          clearInterval(checkSpeechEnd)
        }
      }, 100)
    }
  }

  const handleStopAudio = () => {
    const synth = window.speechSynthesis
    synth.cancel()
    setIsAudioPlaying(false)
  }

  const followUpOptions = useMemo(() => {
    if (m.type !== 'ai') return []
    const options = []

    if (m.rewrite_info?.modified && m.rewritten_query) {
      options.push(m.rewritten_query)
    }
    if (Array.isArray(m.insights)) {
      m.insights.slice(0, 2).forEach((insight) => {
        const text = String(insight || '').replace(/[.\s]+$/, '')
        if (!text) return
        options.push(text.endsWith('?') ? text : `Can you explain: ${text}?`)
      })
    }
    if (Array.isArray(m.columns) && m.columns.length > 0) {
      options.push(`Break this down by ${formatColumnName(m.columns[0])}`)
      if (m.columns.length > 1) {
        options.push(`Compare by ${formatColumnName(m.columns[1])}`)
      }
    }
    if (m.trend?.direction && m.trend.direction !== 'flat') {
      options.push(`What caused this ${m.trend.direction === 'up' ? 'increase' : 'decrease'}?`)
    }

    const deduped = []
    for (const opt of options) {
      const key = String(opt || '').trim()
      if (!key) continue
      if (!deduped.some((v) => v.toLowerCase() === key.toLowerCase())) deduped.push(key)
      if (deduped.length >= 4) break
    }
    return deduped
  }, [m])

  if (m.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-brand-600 text-white rounded-lg px-4 py-2 max-w-2xl w-full">
          {!editingPrompt ? (
            <div className="flex items-start gap-2">
              <div className="flex-1">{m.content}</div>
              <div className="flex items-center gap-2">
                <button onClick={() => setEditingPrompt(true)} className="text-white/70 hover:text-white" title="Edit prompt">
                  <Pencil size={14} />
                </button>
                <button onClick={handleDelete} className="text-white/70 hover:text-white" title="Delete prompt">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={2}
                className="w-full rounded-md text-gray-900 px-2 py-1 text-sm"
              />
              <div className="flex items-center gap-2">
                <button onClick={handleEditSubmit} className="btn-secondary text-xs">Save</button>
                <button onClick={() => setEditingPrompt(false)} className="btn-secondary text-xs">Cancel</button>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }
  if (m.type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="bg-red-50 text-red-700 rounded-lg px-4 py-3 max-w-2xl">
          <div className="flex items-center gap-2"><AlertCircle size={16} /> {m.content}</div>
          {m.canRetry && m.failedQuery && (
            <button onClick={onRetry} disabled={loading}
              className="mt-3 inline-flex items-center gap-2 px-3 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50">
              <RotateCcw size={16} className={loading ? 'animate-spin' : ''} /> Retry
            </button>
          )}
        </div>
      </div>
    )
  }
  // AI
  return (
    <div className="flex justify-start gap-2">
      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 max-w-3xl w-full min-h-12">
        {m.content ? (
          <Markdown className="text-sm text-gray-800">{m.content}</Markdown>
        ) : (
          <div className="text-sm text-gray-400 italic">
            {m.error ? `Error: ${m.error}` : 'No response generated'}
          </div>
        )}

        {/* Trend badge */}
        {m.trend && (
          <div className={`mt-2 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
            m.trend.direction === 'up' ? 'bg-green-100 text-green-700'
              : m.trend.direction === 'down' ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-600'}`}>
            {m.trend.direction === 'up' ? <TrendingUp size={12} />
              : m.trend.direction === 'down' ? <TrendingDown size={12} /> : <Minus size={12} />}
            {m.trend.direction === 'flat'
              ? 'No significant change'
              : `${m.trend.direction === 'up' ? '+' : ''}${m.trend.percent_change}% (${m.trend.start} → ${m.trend.end})`}
          </div>
        )}

        {/* Insights */}
        {Array.isArray(m.insights) && m.insights.length > 0 && (
          <div className="mt-3 bg-brand-50 border border-brand-100 rounded-lg p-3">
            <div className="flex items-center gap-1 text-xs font-medium text-brand-700 mb-1">
              <Lightbulb size={13} /> Insights
            </div>
            <ul className="list-disc list-inside text-xs text-gray-700 space-y-0.5">
              {m.insights.map((it, i) => <li key={i}>{it}</li>)}
            </ul>
          </div>
        )}

        {/* Result views: Chart / Table switcher */}
        {Array.isArray(m.data) && m.data.length > 0 && (
          <ResultViews
            viz={m.visualization}
            columns={m.columns}
            rows={m.data}
            rowCount={m.row_count}
          />
        )}

        {/* Self-correction note */}
        {Array.isArray(m.corrections) && m.corrections.length > 0 && (
          <p className="mt-2 text-[11px] text-amber-600">
            🔁 Auto-corrected the query after {m.corrections.length} failed attempt(s).
          </p>
        )}



        {m.sql_query && (
          <details className="mt-3">
            <summary className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
              <Code size={14} /> Generated SQL
            </summary>
            <pre className="mt-2 bg-gray-900 text-green-300 text-xs rounded-lg p-3 overflow-x-auto">{m.sql_query}</pre>
          </details>
        )}
        {/* Action buttons */}
        <div className="mt-3 flex items-center gap-2 border-t border-gray-100 pt-2">
          <button onClick={handleCopy} className="text-gray-400 hover:text-gray-600" title="Copy response">
            <Copy size={14} />
          </button>
          <div className="relative">
            <button onClick={handleVoice} className="text-gray-400 hover:text-gray-600" title="Speak response">
              <Volume2 size={14} />
            </button>
            {isAudioPlaying && (
              <button 
                onClick={handleStopAudio} 
                className="absolute -top-5 -right-1 text-red-500 hover:text-red-700 bg-white rounded-full p-0.5 border border-red-200"
                title="Stop audio"
              >
                <Square size={12} fill="currentColor" />
              </button>
            )}
          </div>
          <button onClick={handleDelete} className="text-gray-400 hover:text-red-600" title="Delete message">
            <Trash2 size={14} />
          </button>
          {m.sql_query && (
            <button
              onClick={() => onRefresh(index)}
              className="text-gray-400 hover:text-brand-600 text-xs flex items-center gap-1"
              title="Refresh data"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          )}
          {copied && <span className="text-[11px] text-green-600">Copied</span>}
        </div>
      </div>
    </div>
  )
}

function Markdown({ children, className = '' }) {
  return (
    <div className={`chat-md ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children || ''}</ReactMarkdown>
    </div>
  )
}

function ResultViews({ viz, columns, rows, rowCount }) {
  const canChart = viz && viz.type === 'chart'
  const [view, setView] = useState(canChart ? 'chart' : 'table')
  const chartRef = useRef(null)

  if (viz && viz.type === 'metric') {
    return (
      <div className="mt-3 inline-block bg-brand-50 border border-brand-100 rounded-xl px-5 py-3">
        <div className="text-xs text-gray-500">{viz.label}</div>
        <div className="text-2xl font-semibold text-brand-700">{String(viz.value)}</div>
      </div>
    )
  }

  return (
    <div className="mt-3">
      {canChart && (
        <div className="flex items-center gap-1 mb-2">
          <button onClick={() => setView('chart')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs ${view === 'chart' ? 'bg-brand-600 text-white' : 'text-gray-600'}`}>
            <BarChart3 size={13} /> Chart
          </button>
          <button onClick={() => setView('table')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs ${view === 'table' ? 'bg-brand-600 text-white' : 'text-gray-600'}`}>
            <TableIcon size={13} /> Table
          </button>
          {view === 'chart' && (
            <div className="ml-auto flex items-center gap-1">
              <button
                onClick={() => chartRef.current && exportAsImage(chartRef.current, 'chart', 'png')}
                className="btn-secondary text-[11px] flex items-center gap-1"
              >
                <Download size={12} /> PNG
              </button>
              <button
                onClick={() => chartRef.current && exportAsImage(chartRef.current, 'chart', 'jpg')}
                className="btn-secondary text-[11px] flex items-center gap-1"
              >
                <Download size={12} /> JPG
              </button>
            </div>
          )}
        </div>
      )}
      {view === 'chart' && canChart
        ? <div ref={chartRef}><ChartRenderer viz={viz} rows={rows} /></div>
        : (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-gray-600">
              Table results ({rowCount || rows.length} row(s))
            </summary>
            <div className="mt-2">
              <DataTable columns={columns} rows={rows} rowCount={rowCount} />
            </div>
          </details>
        )}
    </div>
  )
}

function DataTable({ columns, rows, rowCount }) {
  const cols = useMemo(
    () => (columns && columns.length ? columns : Object.keys(rows[0] || {})),
    [columns, rows]
  )
  const [columnVisibility, setColumnVisibility] = useState(Object.fromEntries(cols.map((c) => [c, true])))
  const [globalFilter, setGlobalFilter] = useState('')
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
  const [columnFilters, setColumnFilters] = useState({})
  const [copied, setCopied] = useState(false)
  const [chartOpen, setChartOpen] = useState(false)
  const [chartType, setChartType] = useState('bar')
  const [xAxis, setXAxis] = useState('')
  const [ySeries, setYSeries] = useState([])
  const [aggregations, setAggregations] = useState([])
  const tableRef = useRef(null)
  const chartRef = useRef(null)
  const deferredGlobal = useDeferredValue(globalFilter)
  const deferredColumnFilters = useDeferredValue(columnFilters)

  useEffect(() => {
    setColumnVisibility((prev) => {
      const next = { ...prev }
      cols.forEach((col) => {
        if (next[col] === undefined) next[col] = true
      })
      return next
    })
  }, [cols.join('|')])

  const numericCols = useMemo(() => {
    if (!cols.length) return []
    return cols.filter((c) => rows.some((r) => {
      const v = r[c]
      return v !== null && v !== undefined && v !== '' && !isNaN(Number(String(v).replace(/,/g, '')))
    }))
  }, [cols, rows])

  useEffect(() => {
    if (!cols.length) return
    setXAxis((prev) => prev || cols[0])
    setYSeries((prev) => (prev.length ? prev : (numericCols.length ? [numericCols[0]] : cols.slice(1, 2))))
  }, [cols, numericCols])

  // Create column definitions
  const columnHelper = createColumnHelper()
  const tableColumns = useMemo(() => (
    cols.map((col) =>
      columnHelper.accessor(col, {
        header: () => (
          <div className="flex flex-col gap-1">
            <div className="font-medium text-xs">{formatColumnName(col)}</div>
            <input
              type="text"
              placeholder="Filter..."
              value={columnFilters[col] || ''}
              onChange={(e) => setColumnFilters((prev) => ({ ...prev, [col]: e.target.value }))}
              className="w-full px-1 py-0.5 text-xs border border-gray-200 rounded"
            />
          </div>
        ),
        cell: (info) => String(info.getValue() || ''),
      })
    )
  ), [cols, columnFilters])

  // Filter data
  const filtered = useMemo(() => (
    rows.filter((row) => {
      if (deferredGlobal) {
        const matches = Object.values(row).some((v) =>
          String(v).toLowerCase().includes(deferredGlobal.toLowerCase())
        )
        if (!matches) return false
      }
      for (const [col, value] of Object.entries(deferredColumnFilters)) {
        if (value && !String(row[col]).toLowerCase().includes(String(value).toLowerCase())) return false
      }
      return true
    })
  ), [rows, deferredGlobal, deferredColumnFilters])

  const table = useReactTable({
    data: filtered,
    columns: tableColumns,
    state: { columnVisibility, pagination },
    onPaginationChange: setPagination,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const handleExport = async () => {
    if (tableRef.current) {
      await exportAsImage(tableRef.current, 'table', 'png')
    }
  }

  const handleCopyTable = async () => {
    const text = [
      cols.map((c) => formatColumnName(c)).join('\t'),
      ...filtered.map((row) => cols.map((c) => row[c]).join('\t')),
    ].join('\n')
    if (await copyToClipboard(text)) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    }
  }

  // Aggregation functions
  const computeAggregation = (data, groupByCol, aggregateCol, aggType) => {
    const groups = {}
    data.forEach((row) => {
      const key = String(row[groupByCol])
      if (!groups[key]) groups[key] = []
      const val = row[aggregateCol]
      if (val !== null && val !== undefined && val !== '') {
        groups[key].push(Number(String(val).replace(/,/g, '')))
      }
    })

    const result = []
    Object.entries(groups).forEach(([key, values]) => {
      let aggValue = 0
      if (aggType === 'sum') aggValue = values.reduce((a, b) => a + b, 0)
      else if (aggType === 'avg') aggValue = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0
      else if (aggType === 'count') aggValue = values.length
      else if (aggType === 'min') aggValue = Math.min(...values)
      else if (aggType === 'max') aggValue = Math.max(...values)
      result.push({ [groupByCol]: key, [aggregateCol]: Math.round(aggValue * 100) / 100 })
    })
    return result
  }

  const chartViz = useMemo(() => {
    if (!chartOpen || !xAxis || !ySeries.length) return null
    
    let dataForChart = filtered
    const appliedAggregations = aggregations.filter((a) => ySeries.includes(a.column))
    if (appliedAggregations.length > 0) {
      // Use aggregated data
      const agg = appliedAggregations[0]
      dataForChart = computeAggregation(filtered, xAxis, agg.column, agg.type)
    }

    return {
      type: 'chart',
      chart_type: chartType,
      xAxis,
      yAxis: ySeries[0],
      series: ySeries,
      columns: cols,
    }
  }, [chartOpen, xAxis, ySeries, chartType, cols, filtered, aggregations])

  return (
    <div className="mt-3 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 border-b border-gray-200 px-3 py-2 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2">
          <button onClick={handleCopyTable} className="btn-secondary text-[11px] flex items-center gap-1">
            <Copy size={12} /> Copy
          </button>
          <button onClick={handleExport} className="btn-secondary text-[11px] flex items-center gap-1">
            <Download size={12} /> Export
          </button>
          <button
            onClick={() => setChartOpen((prev) => !prev)}
            className="btn-secondary text-[11px] flex items-center gap-1"
          >
            <BarChart3 size={12} /> Convert to chart
          </button>
          <details className="text-[11px] relative">
            <summary className="cursor-pointer px-2 py-1 rounded">
              <Eye size={12} className="inline mr-1" /> Columns
            </summary>
            <div className="absolute mt-1 bg-white border border-gray-200 rounded-lg p-3 shadow-lg space-y-2 z-10 max-h-48 overflow-y-auto">
              {cols.map((col) => (
                <label key={col} className="flex items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={columnVisibility[col] ?? true}
                    onChange={(e) => setColumnVisibility((prev) => ({ ...prev, [col]: e.target.checked }))}
                  />
                  {formatColumnName(col)}
                </label>
              ))}
            </div>
          </details>
          {copied && <span className="text-green-600">Copied</span>}
        </div>
      </div>

      {/* Table */}
      <div ref={tableRef} className="overflow-x-auto">
        <table className="w-full text-xs bg-white">
          <thead className="bg-gray-100 border-b border-gray-200">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) =>
                  h.isPlaceholder ? null : (
                    <th key={h.id} className="px-3 py-2 text-left font-medium text-gray-700">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                    </th>
                  )
                )}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr className="border-t border-gray-100">
                <td colSpan={cols.length} className="px-3 py-3 text-center text-gray-400">
                  No rows match your filters.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-1.5 text-gray-700 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {chartOpen && (
        <div className="border-t border-gray-200 bg-white p-3">
          <div className="flex items-center gap-3 flex-wrap text-xs mb-3">
            <label className="flex items-center gap-2">
              Type
              <select
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                className="h-7 px-2 text-xs border border-gray-200 rounded"
              >
                <option value="bar">Bar</option>
                <option value="line">Line</option>
                <option value="area">Area</option>
                <option value="pie">Pie</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              X-Axis / Group By
              <select
                value={xAxis}
                onChange={(e) => setXAxis(e.target.value)}
                className="h-7 px-2 text-xs border border-gray-200 rounded"
              >
                {cols.map((col) => (
                  <option key={col} value={col}>{formatColumnName(col)}</option>
                ))}
              </select>
            </label>
            <div className="flex items-center gap-2">
              Y-Series / Values
              <div className="flex items-center gap-2 flex-wrap">
                {cols.map((col) => (
                  <label key={col} className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      checked={ySeries.includes(col)}
                      onChange={(e) => {
                        setYSeries((prev) => e.target.checked
                          ? [...prev, col]
                          : prev.filter((c) => c !== col)
                        )
                      }}
                    />
                    {formatColumnName(col)}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Aggregation Section */}
          <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-xs font-medium mb-2 text-blue-900">Calculated Values (Optional)</div>
            <div className="space-y-2">
              {ySeries.map((col) => (
                <div key={col} className="flex items-center gap-2 text-xs">
                  <label className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={aggregations.some((a) => a.column === col)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setAggregations((prev) => [...prev, { column: col, type: 'sum' }])
                        } else {
                          setAggregations((prev) => prev.filter((a) => a.column !== col))
                        }
                      }}
                    />
                    <span className="text-gray-600">{formatColumnName(col)}</span>
                  </label>
                  {aggregations.some((a) => a.column === col) && (
                    <select
                      value={aggregations.find((a) => a.column === col)?.type || 'sum'}
                      onChange={(e) => {
                        setAggregations((prev) =>
                          prev.map((a) => a.column === col ? { ...a, type: e.target.value } : a)
                        )
                      }}
                      className="h-6 px-1.5 text-xs border border-blue-200 rounded bg-white"
                    >
                      <option value="sum">Sum</option>
                      <option value="avg">Average</option>
                      <option value="count">Count</option>
                      <option value="min">Min</option>
                      <option value="max">Max</option>
                    </select>
                  )}
                </div>
              ))}
            </div>
          </div>

          {chartViz && (
            <div className="mt-3" ref={chartRef}>
              <ChartRenderer 
                viz={chartViz} 
                rows={aggregations.length && ySeries.length ? computeAggregation(filtered, xAxis, ySeries[0], aggregations[0]?.type || 'sum') : filtered} 
              />
            </div>
          )}
          {chartViz && (
            <div className="mt-2 flex items-center gap-2 text-[11px]">
              <button
                onClick={() => chartRef.current && exportAsImage(chartRef.current, 'table-chart', 'png')}
                className="btn-secondary text-[11px] flex items-center gap-1"
              >
                <Download size={12} /> PNG
              </button>
              <button
                onClick={() => chartRef.current && exportAsImage(chartRef.current, 'table-chart', 'jpg')}
                className="btn-secondary text-[11px] flex items-center gap-1"
              >
                <Download size={12} /> JPG
              </button>
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      <div className="bg-gray-50 border-t border-gray-200 px-3 py-2 flex items-center justify-between text-[11px] text-gray-600">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1">
            Search
            <input
              type="text"
              placeholder="Global"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="h-6 px-2 text-[11px] border border-gray-200 rounded"
            />
          </label>
          <label className="flex items-center gap-1">
            Rows
            <select
              value={pagination.pageSize}
              onChange={(e) => setPagination({ pageIndex: 0, pageSize: Number(e.target.value) })}
              className="h-6 px-1 text-[11px] border border-gray-200 rounded"
            >
              {[5, 10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
          </label>
          <span>
            Showing {pagination.pageIndex * pagination.pageSize + 1} to{' '}
            {Math.min((pagination.pageIndex + 1) * pagination.pageSize, filtered.length)} of {filtered.length}{' '}
            (Total: {rowCount || filtered.length})
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 rounded border border-gray-300 disabled:opacity-50"
          >
            Prev
          </button>
          <span className="text-xs text-gray-500">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 rounded border border-gray-300 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
