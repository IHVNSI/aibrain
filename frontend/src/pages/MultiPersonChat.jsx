import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import {
  Send, Loader, CheckCircle2, XCircle, Trash2, Plus, Settings,
  Users, MessageCircle, Zap, AlertCircle, Eye, X, Copy, Mic, Square, Upload, Volume2
} from 'lucide-react'
import Swal from 'sweetalert2'

export default function MultiPersonChat() {
  const navigate = useNavigate()
  const { isAdmin, isCentralAdmin } = useAuth()
  const [mode, setMode] = useState('setup') // setup, listening, review, action
  const [participants, setParticipants] = useState([])
  const [currentParticipant, setCurrentParticipant] = useState('person1')
  const [conversations, setConversations] = useState([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [aiInstructions, setAiInstructions] = useState('')
  const [loading, setLoading] = useState(false)
  const [aiResponse, setAiResponse] = useState(null)
  const [approvalPending, setApprovalPending] = useState(false)
  const [msg, setMsg] = useState(null)
  const conversationEndRef = useRef(null)
  
  // Diarization feature
  const [useDiarization, setUseDiarization] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [audioLanguage, setAudioLanguage] = useState('english')
  const [showTranslations, setShowTranslations] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  
  // Live transcription states
  const [interimText, setInterimText] = useState('')
  const [finalTranscript, setFinalTranscript] = useState('')
  const recognitionRef = useRef(null)
  const [isWebSpeechActive, setIsWebSpeechActive] = useState(false)
  
  // Translation states
  const [statementTranslations, setStatementTranslations] = useState({})
  const [translatingId, setTranslatingId] = useState(null)
  const [targetLanguage, setTargetLanguage] = useState('english')
  
  // Language code mapping for Web Speech API
  const languageCodeMap = {
    'english': 'en-US',
    'igbo': 'ig-NG',
    'hausa': 'ha-NG',
    'yoruba': 'yo-NG'
  }

  // Auto-scroll to latest conversation
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversations])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      audioChunksRef.current = []
      
      // Check supported MIME types for MediaRecorder
      let options = { mimeType: 'audio/webm;codecs=opus' }
      
      // Try WAV first (best compatibility)
      if (!MediaRecorder.isTypeSupported('audio/wav')) {
        console.warn('⚠️  audio/wav not supported, trying audio/webm')
        if (!MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          console.warn('⚠️  audio/webm;codecs=opus not supported, trying audio/webm')
          if (!MediaRecorder.isTypeSupported('audio/webm')) {
            console.warn('⚠️  audio/webm not supported, using default')
            options = {}  // Use default MIME type
          } else {
            options = { mimeType: 'audio/webm' }
          }
        }
      } else {
        options = { mimeType: 'audio/wav' }
      }
      
      console.log('🎙️  MediaRecorder options:', options)
      
      const mediaRecorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mediaRecorder
      
      mediaRecorder.ondataavailable = (event) => {
        console.log('📦 Audio chunk received:', event.data.size, 'bytes, type:', event.data.type)
        audioChunksRef.current.push(event.data)
      }
      
      mediaRecorder.onstop = async () => {
        // Create blob with proper MIME type detection
        const mimeType = mediaRecorder.mimeType || 'audio/webm'
        console.log('🎵 Recording stopped, detected MIME type:', mimeType)
        
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        console.log('📊 Final audio blob:', {
          size: audioBlob.size,
          type: audioBlob.type,
          chunks: audioChunksRef.current.length
        })
        
        if (audioBlob.size === 0) {
          console.error('❌ Audio blob is empty!')
          setMsg({ type: 'error', text: 'No audio was recorded. Please try again.' })
          setIsRecording(false)
          setLoading(false)
          return
        }
        
        await processAudioDiarization(audioBlob)
        
        // Stop stream
        stream.getTracks().forEach(track => track.stop())
        
        // Stop Web Speech Recognition
        if (recognitionRef.current) {
          recognitionRef.current.stop()
          setIsWebSpeechActive(false)
        }
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      
      // Initialize Web Speech Recognition for live transcription
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition()
        recognitionRef.current = recognition
        
        recognition.continuous = true
        recognition.interimResults = true
        recognition.language = languageCodeMap[audioLanguage] || 'en-US'
        
        recognition.onstart = () => {
          console.log('🎤 Web Speech Recognition started')
          setIsWebSpeechActive(true)
          setInterimText('')
          setFinalTranscript('')
        }
        
        recognition.onresult = (event) => {
          let interim = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              setFinalTranscript(prev => prev + transcript + ' ')
            } else {
              interim += transcript
            }
          }
          if (interim) {
            setInterimText(interim)
          }
        }
        
        recognition.onerror = (event) => {
          console.error('Speech Recognition error:', event.error)
          if (event.error !== 'no-speech') {
            setMsg({ type: 'error', text: `Voice recognition issue: ${event.error}` })
          }
        }
        
        recognition.onend = () => {
          console.log('🎤 Web Speech Recognition ended')
          setIsWebSpeechActive(false)
        }
        
        recognition.start()
      } else {
        console.warn('Web Speech API not supported in this browser')
      }
      
      setMsg({ type: 'success', text: '🎤 Recording started... Speak naturally with all participants.' })
    } catch (error) {
      console.error('Error accessing microphone:', error)
      setMsg({ type: 'error', text: 'Unable to access microphone. Check permissions.' })
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      // Stop Web Speech Recognition
      if (recognitionRef.current) {
        recognitionRef.current.stop()
        setIsWebSpeechActive(false)
      }
    }
  }

  const processAudioDiarization = async (audioBlob) => {
    setLoading(true)
    setMsg(null)
    try {
      // DEBUG: Log audio blob details
      console.log('📊 Audio Blob Received:');
      console.log('   Size:', audioBlob.size, 'bytes');
      console.log('   Type:', audioBlob.type);
      console.log('   Is empty:', audioBlob.size === 0);
      
      if (audioBlob.size === 0) {
        setMsg({ type: 'error', text: '❌ No audio recorded. Please ensure microphone is working and you spoke clearly.' })
        setLoading(false)
        return
      }
      
      if (audioBlob.size < 1000) {
        console.warn('⚠️  Audio blob is very small', audioBlob.size, 'bytes - may contain insufficient audio')
      }
      
      const formData = new FormData()
      
      // Determine filename based on MIME type
      let filename = 'recording.webm'
      if (audioBlob.type.includes('wav')) {
        filename = 'recording.wav'
      } else if (audioBlob.type.includes('webm')) {
        filename = 'recording.webm'
      } else if (audioBlob.type.includes('mp3') || audioBlob.type.includes('mpeg')) {
        filename = 'recording.mp3'
      } else if (audioBlob.type.includes('mp4')) {
        filename = 'recording.m4a'
      }
      
      formData.append('audio', audioBlob, filename)
      formData.append('language', audioLanguage)
      
      console.log('📤 Sending diarization request:');
      console.log('   Language:', audioLanguage);
      console.log('   Audio blob type:', audioBlob.type);
      console.log('   Filename:', filename);
      console.log('   Audio size:', audioBlob.size, 'bytes');
      
      const { data } = await api.post('/api/multiperson/multiperson-diarize', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      console.log('📥 Diarization response:', data);
      
      if (data.success && data.conversations && data.conversations.length > 0) {
        // Auto-populate participants from detected speakers
        const speakers = [...new Set(data.conversations.map(c => c.participant))]
        setParticipants(speakers)
        
        // Auto-populate conversations
        const conversationsList = data.conversations.map((c, idx) => ({
          id: Date.now() + Math.random(),
          participant: c.participant,
          originalText: c.originalText || '',
          translatedText: c.translatedText || null,  // May be null (no auto-translation)
          language: c.language || audioLanguage,  // Track source language
          timestamp: c.timestamp || `${idx}:00`,
          reviewed: false
        }))
        
        setConversations(conversationsList)
        setMode('listening')
        
        // Show success message with details about what was detected
        const summary = `✓ Detected ${speakers.length} speaker(s) and ${conversationsList.length} statement(s)`
        setMsg({ type: 'success', text: summary })
        console.log('✅ ' + summary, conversationsList)
      } else if (data.conversations && data.conversations.length === 0) {
        setMsg({ type: 'error', text: 'No speech detected in the audio. Please speak more clearly or record a longer audio.' })
        console.error('No conversations detected in response')
      } else {
        setMsg({ type: 'error', text: `Diarization failed: ${data.error || 'Unknown error'}` })
        console.error('Diarization failed:', data)
      }
    } catch (error) {
      console.error('Diarization error:', error)
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error'
      setMsg({ type: 'error', text: `Diarization failed: ${errorMsg}` })
    } finally {
      setLoading(false)
    }
  }

  const handleAudioFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    
    setLoading(true)
    setMsg(null)
    try {
      const formData = new FormData()
      formData.append('audio', file)
      formData.append('language', audioLanguage)
      
      console.log('Uploading audio file with language:', audioLanguage)
      
      const { data } = await api.post('/api/multiperson/multiperson-diarize', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      console.log('Upload diarization response:', data)
      
      if (data.success && data.conversations && data.conversations.length > 0) {
        const speakers = [...new Set(data.conversations.map(c => c.participant))]
        setParticipants(speakers)
        
        const conversationsList = data.conversations.map((c, idx) => ({
          id: Date.now() + Math.random(),
          participant: c.participant,
          originalText: c.originalText || '',
          translatedText: c.translatedText || null,  // May be null (no auto-translation)
          language: c.language || audioLanguage,  // Track source language
          timestamp: c.timestamp || `${idx}:00`,
          reviewed: false
        }))
        
        setConversations(conversationsList)
        setMode('listening')
        
        const summary = `✓ Detected ${speakers.length} speaker(s) and ${conversationsList.length} statement(s)`
        setMsg({ type: 'success', text: summary })
        console.log(summary, conversationsList)
      } else if (data.conversations && data.conversations.length === 0) {
        setMsg({ type: 'error', text: 'No speech detected in the audio file. Ensure the file contains clear speech.' })
      } else {
        setMsg({ type: 'error', text: `Upload failed: ${data.error || 'Unknown error'}` })
      }
    } catch (error) {
      console.error('Upload error:', error)
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error'
      setMsg({ type: 'error', text: `Upload failed: ${errorMsg}` })
    } finally {
      setLoading(false)
      event.target.value = ''
    }
  }

  const addParticipant = () => {
    const newParticipant = `Person${participants.length + 1}`
    setParticipants([...participants, newParticipant])
    if (participants.length === 1) {
      setMode('listening')
    }
  }

  const addMessage = () => {
    if (!currentMessage.trim() || participants.length < 2) {
      setMsg({ type: 'error', text: 'Need at least 2 participants and a message' })
      return
    }

    const newConversation = {
      id: Date.now(),
      participant: currentParticipant,
      originalText: currentMessage,
      translatedText: currentMessage, // Will be translated by backend
      timestamp: new Date().toLocaleTimeString(),
      reviewed: false,
    }

    setConversations([...conversations, newConversation])
    setCurrentMessage('')
    setMsg({ type: 'success', text: 'Message added to conversation' })
    setTimeout(() => setMsg(null), 2000)
  }

  const removeMessage = (id) => {
    setConversations(conversations.filter((c) => c.id !== id))
  }

  const startEditingMessage = (id, text) => {
    setEditingId(id)
    setEditText(text)
  }

  const saveEditedMessage = (id) => {
    setConversations(conversations.map(c => 
      c.id === id ? { ...c, originalText: editText } : c
    ))
    setEditingId(null)
    setEditText('')
    setMsg({ type: 'success', text: 'Message updated' })
    setTimeout(() => setMsg(null), 2000)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditText('')
  }

  const translateStatement = async (statementId, text, sourceLanguage, targetLanguage) => {
    // Check if already translated to this language
    const translationKey = `translatedTo${targetLanguage}`
    if (statementTranslations[statementId]?.[translationKey]) {
      // Already translated, toggle showing it
      const showKey = `show${targetLanguage}`
      setStatementTranslations(prev => ({
        ...prev,
        [statementId]: {
          ...prev[statementId],
          [showKey]: !prev[statementId][showKey]
        }
      }))
      return
    }
    
    setTranslatingId(statementId)
    try {
      const { data } = await api.post('/api/multiperson/translate-statement', {
        text,
        sourceLanguage,
        targetLanguage
      })
      
      if (data.success) {
        setStatementTranslations(prev => ({
          ...prev,
          [statementId]: {
            ...prev[statementId],
            [translationKey]: data.translated,
            [`show${targetLanguage}`]: true
          }
        }))
        setMsg({ 
          type: 'success', 
          text: `✓ Translated to ${targetLanguage}` 
        })
        setTimeout(() => setMsg(null), 2000)
      } else {
        setMsg({ 
          type: 'error', 
          text: `Translation failed: ${data.error}` 
        })
      }
    } catch (error) {
      console.error('Translation error:', error)
      setMsg({ 
        type: 'error', 
        text: `Translation error: ${error.response?.data?.error || error.message}` 
      })
    } finally {
      setTranslatingId(null)
    }
  }

  const translateConversation = async () => {
    // Translate entire conversation from source language to English
    // This is a post-processing step that happens after recording is complete
    if (!audioLanguage || audioLanguage === 'english') {
      setMsg({ type: 'info', text: 'No translation needed (already English)' })
      return
    }
    
    if (conversations.length === 0) {
      setMsg({ type: 'error', text: 'No conversation to translate' })
      return
    }
    
    setLoading(true)
    try {
      const { data } = await api.post('/api/multiperson/translate-conversation', {
        conversations: conversations.map(c => ({
          participant: c.participant,
          originalText: c.originalText,
          language: audioLanguage,
          timestamp: c.timestamp
        })),
        sourceLanguage: audioLanguage
      })
      
      if (data.success) {
        // Update conversations with translations
        setConversations(prevConversations => 
          prevConversations.map((conv, idx) => {
            const translated = data.conversations[idx]
            return {
              ...conv,
              translatedText: translated?.translatedText || translated?.originalText || conv.originalText
            }
          })
        )
        setShowTranslations(true)
        setMsg({ 
          type: 'success', 
          text: `✓ Translated entire conversation to English` 
        })
        setTimeout(() => setMsg(null), 3000)
      } else {
        setMsg({ 
          type: 'error', 
          text: `Translation failed: ${data.error}` 
        })
      }
    } catch (error) {
      console.error('Conversation translation error:', error)
      setMsg({ 
        type: 'error', 
        text: `Translation error: ${error.response?.data?.error || error.message}` 
      })
    } finally {
      setLoading(false)
    }
  }

  const submitConversationForAnalysis = async () => {
    if (conversations.length === 0) {
      setMsg({ type: 'error', text: 'Add conversation messages first' })
      return
    }

    if (!aiInstructions.trim()) {
      setMsg({ type: 'error', text: 'Provide instructions for what the AI should do' })
      return
    }

    setLoading(true)
    try {
      const { data } = await api.post('/api/multiperson/multiperson-analyze', {
        conversations: conversations,
        instructions: aiInstructions,
        participants: participants,
      })

      setAiResponse(data.suggestion)
      setApprovalPending(true)
      setMode('review')
      setMsg({ type: 'success', text: 'Analysis complete. Review the AI suggestion below.' })
    } catch (error) {
      console.error('Analysis error:', error)
      setMsg({ type: 'error', text: `Analysis failed: ${error.response?.data?.error || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const approveAction = async () => {
    if (!aiResponse) return

    setLoading(true)
    try {
      const { data } = await api.post('/api/multiperson/multiperson-execute', {
        suggestion: aiResponse,
        conversations: conversations,
        approval: true,
      })

      setMsg({ type: 'success', text: 'Action executed successfully!' })
      setAiResponse(null)
      setApprovalPending(false)
      setMode('action')

      // Show result
      await Swal.fire({
        title: 'Action Completed',
        html: `<pre style="text-align: left; max-height: 400px; overflow-y: auto;">${data.result}</pre>`,
        icon: 'success',
        confirmButtonText: 'OK',
      })

      // Reset for next conversation
      doResetConversation()
    } catch (error) {
      console.error('Execution error:', error)
      setMsg({ type: 'error', text: `Execution failed: ${error.response?.data?.error || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const rejectAction = async () => {
    const { value: feedback } = await Swal.fire({
      title: 'Provide Feedback',
      input: 'textarea',
      inputLabel: 'What would you like the AI to do differently?',
      inputPlaceholder: 'Enter your feedback here...',
      showCancelButton: true,
      confirmButtonText: 'Submit Feedback',
    })

    if (feedback) {
      setLoading(true)
      try {
        const { data } = await api.post('/api/multiperson/multiperson-refine', {
          currentSuggestion: aiResponse,
          feedback: feedback,
          conversations: conversations,
          instructions: aiInstructions,
        })

        setAiResponse(data.refinedSuggestion)
        setMsg({ type: 'success', text: 'AI has refined its suggestion based on your feedback' })
      } catch (error) {
        console.error('Refinement error:', error)
        setMsg({ type: 'error', text: `Refinement failed: ${error.response?.data?.error || error.message}` })
      } finally {
        setLoading(false)
      }
    }
  }

  const doResetConversation = () => {
    setConversations([])
    setAiInstructions('')
    setAiResponse(null)
    setApprovalPending(false)
    setMode('listening')
  }

  return (
    <>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users size={24} className="text-brand-600" />
            <div>
              <h1 className="text-2xl font-bold">Multi-Person Chat Analysis</h1>
              <p className="text-sm text-gray-500">Capture conversations, get AI suggestions, and execute actions with approval</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/chat')}
            className="text-gray-500 hover:text-gray-700"
          >
            <X size={24} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-4">
          {msg && (
            <div className={`mb-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
              msg.type === 'success' 
                ? 'bg-green-50 text-green-700 border border-green-200' 
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}>
              {msg.type === 'success' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
              {msg.text}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left: Conversation Setup and Input */}
            <div className="lg:col-span-2 space-y-4">
              {/* Participants Setup */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <Users size={16} /> Participants
                  </h3>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useDiarization}
                      onChange={(e) => {
                        setUseDiarization(e.target.checked)
                        if (e.target.checked) {
                          setConversations([])
                          setParticipants([])
                        }
                      }}
                      className="w-4 h-4 text-brand-600 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">Auto-detect speakers</span>
                  </label>
                </div>

                {useDiarization ? (
                  // Diarization: Audio Input Mode
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        <Volume2 size={16} className="inline mr-2" />
                        Audio Language
                      </label>
                      <select
                        value={audioLanguage}
                        onChange={(e) => setAudioLanguage(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      >
                        <option value="english">English</option>
                        <option value="igbo">Igbo</option>
                        <option value="hausa">Hausa</option>
                        <option value="yoruba">Yoruba</option>
                      </select>
                      <p className="text-xs text-gray-500 mt-1">Speech will be auto-translated to English before processing</p>
                    </div>

                    {!isRecording ? (
                      <div className="space-y-2">
                        <button
                          onClick={startRecording}
                          disabled={loading}
                          className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-2"
                        >
                          <Mic size={16} /> Start Recording
                        </button>
                        <label className="w-full cursor-pointer">
                          <div className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-2 border border-gray-300">
                            <Upload size={16} /> Upload Audio File
                          </div>
                          <input
                            type="file"
                            accept="audio/*"
                            onChange={handleAudioFileUpload}
                            disabled={loading}
                            className="hidden"
                          />
                        </label>
                      </div>
                    ) : (
                      <button
                        onClick={stopRecording}
                        className="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-2 animate-pulse"
                      >
                        <Square size={16} /> Stop Recording
                      </button>
                    )}

                    {/* Live Transcription Display */}
                    {isRecording && isWebSpeechActive && (
                      <div className="mt-3 p-4 bg-blue-50 border-2 border-blue-300 rounded-lg animate-pulse">
                        <div className="flex items-center gap-2 mb-2">
                          <Mic size={16} className="text-blue-600 animate-bounce" />
                          <p className="text-sm font-semibold text-blue-900">Live Transcription</p>
                          <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded">
                            {audioLanguage.toUpperCase()}
                          </span>
                        </div>
                        <div className="bg-white rounded p-2 min-h-12">
                          {finalTranscript && (
                            <p className="text-sm text-gray-800 font-medium mb-1">{finalTranscript}</p>
                          )}
                          {interimText && (
                            <p className="text-sm text-gray-500 italic">{interimText}</p>
                          )}
                          {!finalTranscript && !interimText && (
                            <p className="text-sm text-gray-400 italic">Listening for speech...</p>
                          )}
                        </div>
                      </div>
                    )}

                    {participants.length > 0 && (
                      <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <p className="text-sm font-medium text-green-900 mb-2">Detected Speakers:</p>
                        <div className="flex flex-wrap gap-2">
                          {participants.map((p, idx) => (
                            <span key={idx} className="bg-green-200 text-green-900 text-sm px-2 py-1 rounded">
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  // Manual Mode
                  <>
                    {participants.length === 0 && (
                      <div className="text-center py-4">
                        <p className="text-gray-500 text-sm mb-3">No participants added yet. Add at least 2 to begin.</p>
                        <button
                          onClick={addParticipant}
                          className="btn-primary flex items-center gap-2 mx-auto"
                        >
                          <Plus size={16} /> Add Participant
                        </button>
                      </div>
                    )}
                    {participants.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex gap-2 flex-wrap mb-3">
                          {participants.map((p, idx) => (
                            <button
                              key={idx}
                              onClick={() => setCurrentParticipant(p)}
                              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                currentParticipant === p
                                  ? 'bg-brand-600 text-white'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {p}
                            </button>
                          ))}
                          <button
                            onClick={addParticipant}
                            className="px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 border border-dashed border-gray-300"
                          >
                            <Plus size={16} />
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Conversation Messages */}
              {participants.length >= 2 && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                      <MessageCircle size={16} /> Conversation Transcript
                      {useDiarization && audioLanguage !== 'english' && (
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded font-medium">
                          {audioLanguage.toUpperCase()}
                        </span>
                      )}
                    </h3>
                    {useDiarization && audioLanguage !== 'english' && (
                      <button
                        onClick={() => translateConversation()}
                        disabled={showTranslations}
                        className={`text-xs px-3 py-1.5 rounded border font-medium transition flex items-center gap-1 ${
                          showTranslations 
                            ? 'bg-green-100 text-green-700 border-green-300 opacity-50 cursor-not-allowed' 
                            : 'bg-blue-50 text-blue-600 border-blue-200 hover:bg-blue-100'
                        }`}
                        title="Translate entire conversation to English (optional, post-processing)"
                      >
                        <Eye size={14} />
                        {showTranslations ? '✓ Translated' : '🌐 Translate to English'}
                      </button>
                    )}
                  </div>
                  
                  <div className="space-y-3 mb-4 max-h-96 overflow-y-auto bg-gray-50 rounded p-3">
                    {conversations.length === 0 ? (
                      <p className="text-gray-400 text-sm text-center py-8">
                        {useDiarization ? 'Record or upload audio to begin conversation detection...' : 'No messages yet. Start adding conversation messages below.'}
                      </p>
                    ) : (
                      conversations.map((conv) => (
                        <div key={conv.id} className="bg-white rounded p-3 border border-gray-200 hover:border-gray-300 transition">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="font-semibold text-sm text-brand-600 truncate">{conv.participant}</span>
                                <span className="text-xs text-gray-400 whitespace-nowrap">{conv.timestamp}</span>
                              </div>
                              
                              {editingId === conv.id ? (
                                <div className="space-y-2">
                                  <textarea
                                    value={editText}
                                    onChange={(e) => setEditText(e.target.value)}
                                    className="w-full px-2 py-1 border border-blue-300 rounded text-sm"
                                    rows={3}
                                  />
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => saveEditedMessage(conv.id)}
                                      className="text-xs px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded"
                                    >
                                      Save
                                    </button>
                                    <button
                                      onClick={cancelEdit}
                                      className="text-xs px-2 py-1 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <>
                                  {/* Original text with language badge */}
                                  <div className="flex items-start gap-2">
                                    <p className="text-sm text-gray-800 mb-2 leading-relaxed font-medium flex-1">
                                      {conv.originalText}
                                    </p>
                                    {audioLanguage !== 'english' && (
                                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded whitespace-nowrap">
                                        {audioLanguage.toUpperCase()}
                                      </span>
                                    )}
                                  </div>
                                  
                                  {/* Translation buttons and display */}
                                  <div className="mt-2 space-y-2">
                                    {/* Translation action buttons */}
                                    <div className="flex flex-wrap gap-2">
                                      {audioLanguage !== 'english' && (
                                        <button
                                          onClick={() => translateStatement(conv.id, conv.originalText, audioLanguage, 'english')}
                                          disabled={translatingId === conv.id}
                                          className={`text-xs px-3 py-1.5 rounded font-medium transition ${
                                            statementTranslations[conv.id]?.['translatedToenglish']
                                              ? 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-300'
                                              : 'bg-blue-100 text-blue-700 hover:bg-blue-200 border border-blue-300'
                                          } ${translatingId === conv.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        >
                                          {translatingId === conv.id ? (
                                            <>
                                              <Loader size={12} className="inline mr-1 animate-spin" />
                                              Translating...
                                            </>
                                          ) : statementTranslations[conv.id]?.['translatedToenglish'] ? (
                                            <>✓ English{statementTranslations[conv.id]?.['showenglish'] ? ' ▼' : ' ▶'}</>
                                          ) : (
                                            '🌐 English'
                                          )}
                                        </button>
                                      )}
                                      
                                      {/* Additional language buttons */}
                                      {['igbo', 'yoruba', 'hausa'].filter(lang => lang !== audioLanguage.toLowerCase()).map(lang => (
                                        <button
                                          key={lang}
                                          onClick={() => translateStatement(conv.id, conv.originalText, audioLanguage || 'english', lang)}
                                          disabled={translatingId === conv.id}
                                          className={`text-xs px-2.5 py-1.5 rounded transition ${
                                            statementTranslations[conv.id]?.[`translatedTo${lang}`]
                                              ? 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-300'
                                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-300'
                                          }`}
                                        >
                                          {lang.charAt(0).toUpperCase() + lang.slice(1)}
                                        </button>
                                      ))}
                                    </div>
                                    
                                    {/* Display translations if available and visible */}
                                    {Object.entries(statementTranslations[conv.id] || {}).map(([key, value]) => {
                                      if (!key.startsWith('translatedTo')) return null
                                      const langCode = key.replace('translatedTo', '')
                                      const showKey = `show${langCode}`
                                      if (!statementTranslations[conv.id][showKey]) return null
                                      
                                      return (
                                        <div 
                                          key={langCode}
                                          className="bg-gradient-to-r from-green-50 to-teal-50 border-l-4 border-green-400 pl-3 py-2 rounded-r"
                                        >
                                          <p className="text-xs font-semibold text-green-700 mb-1">
                                            {langCode === 'english' ? '🌍 English Translation:' : `📝 ${langCode.toUpperCase()}:`}
                                          </p>
                                          <p className="text-xs text-green-800 leading-relaxed">{value}</p>
                                        </div>
                                      )
                                    })}
                                    
                                    {/* Show backend translation if available */}
                                    {showTranslations && conv.translatedText && conv.translatedText !== conv.originalText && (
                                      <div className="bg-blue-50 border-l-2 border-blue-300 pl-2 py-2 rounded-sm">
                                        <p className="text-xs font-medium text-blue-700 mb-1">📝 Auto-Translated (Backend):</p>
                                        <p className="text-xs text-blue-800 leading-relaxed">{conv.translatedText}</p>
                                      </div>
                                    )}
                                  </div>
                                </>
                              )}
                            </div>
                            
                            {editingId !== conv.id && (
                              <div className="flex gap-1 flex-shrink-0">
                                <button
                                  onClick={() => startEditingMessage(conv.id, conv.originalText)}
                                  className="text-gray-400 hover:text-blue-600 p-1"
                                  title="Edit"
                                >
                                  ✏️
                                </button>
                                <button
                                  onClick={() => removeMessage(conv.id)}
                                  className="text-gray-400 hover:text-red-600 p-1"
                                  title="Delete"
                                >
                                  <X size={16} />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                    <div ref={conversationEndRef} />
                  </div>

                  {/* For Diarization: Show transcript summary and options */}
                  {useDiarization && conversations.length > 0 && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          <p className="text-xs font-medium text-blue-900 mb-2">✓ Conversation captured successfully!</p>
                          <p className="text-xs text-blue-700">
                            {conversations.length} speaker{conversations.length !== 1 ? 's' : ''} detected • 
                            {audioLanguage !== 'english' ? ` Language: ${audioLanguage.toUpperCase()}` : ' English'}
                          </p>
                        </div>
                        {showTranslations && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded whitespace-nowrap">
                            Translation visible
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Message Input - Only if not diarization mode OR after diarization is done */}
                  {!useDiarization || conversations.length > 0 ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={currentMessage}
                        onChange={(e) => setCurrentMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addMessage()}
                        placeholder={useDiarization ? 'Add more messages (optional)...' : `Enter message for ${currentParticipant}...`}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                      <button
                        onClick={addMessage}
                        className="btn-primary flex items-center gap-2"
                      >
                        <Send size={16} /> Add
                      </button>
                    </div>
                  ) : null}
                </div>
              )}

              {/* AI Instructions - Show after conversations loaded */}
              {participants.length >= 2 && conversations.length > 0 && !approvalPending && (
                <div className={`rounded-lg border p-4 ${
                  useDiarization && !aiInstructions.trim() 
                    ? 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-300 ring-2 ring-amber-200' 
                    : 'bg-white border-gray-200'
                }`}>
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                      <Zap size={16} className={useDiarization && !aiInstructions.trim() ? 'text-amber-600' : 'text-gray-700'} />
                      <span>Step 3: What Should the AI Do?</span>
                      {useDiarization && (
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded font-medium">
                          {aiInstructions.trim() ? '✓ Ready' : 'Required'}
                        </span>
                      )}
                    </h3>
                  </div>
                  
                  <p className="text-xs text-gray-600 mb-3 leading-relaxed">
                    {useDiarization 
                      ? 'Your conversation has been captured. Now tell the AI what to do with it. Be specific about the analysis, summary, or action you want.' 
                      : 'Specify what analysis or action you want the AI to perform on this conversation.'}
                  </p>

                  <div className="mb-3">
                    <label className="text-xs font-medium text-gray-700 block mb-2">
                      AI Instructions *
                    </label>
                    <textarea
                      value={aiInstructions}
                      onChange={(e) => setAiInstructions(e.target.value)}
                      placeholder="Examples:
• Extract all action items and assign them to speakers
• Summarize the key agreements and decisions
• Identify any disagreements and suggest resolutions
• Generate detailed meeting notes with timestamps
• Translate and analyze sentiment of each speaker
• Create a brief executive summary"
                      rows={5}
                      className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 transition ${
                        aiInstructions.trim()
                          ? 'border-green-300 focus:ring-green-200 bg-green-50'
                          : 'border-gray-300 focus:ring-blue-200 bg-white'
                      }`}
                    />
                  </div>

                  <div className="mb-3">
                    <p className="text-xs text-gray-500 flex items-center gap-1">
                      <span>💡</span>
                      <span>Be specific about what analysis or action you want. The AI will process the transcript and provide recommendations.</span>
                    </p>
                  </div>

                  <button
                    onClick={submitConversationForAnalysis}
                    disabled={loading || !aiInstructions.trim()}
                    className={`w-full font-medium py-2.5 px-3 rounded-lg flex items-center justify-center gap-2 transition transform ${
                      aiInstructions.trim()
                        ? 'btn-primary hover:scale-105 active:scale-95'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    {loading ? (
                      <>
                        <Loader size={16} className="animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Zap size={16} />
                        Analyze with AI
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Right: AI Response and Approval */}
            <div className="space-y-4">
              {/* Diarization Summary - Show when using diarization */}
              {useDiarization && conversations.length > 0 && (
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-4">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2 text-blue-900">
                    <Users size={16} />
                    Conversation Summary
                  </h4>
                  <div className="space-y-2 text-sm bg-white rounded p-3 border border-blue-100">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Speakers Detected:</span>
                      <span className="font-medium text-blue-700">{participants.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Statements:</span>
                      <span className="font-medium text-blue-700">{conversations.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Language:</span>
                      <span className="font-medium text-blue-700 capitalize">{audioLanguage}</span>
                    </div>
                    {showTranslations && (
                      <div className="flex justify-between border-t border-blue-100 pt-2">
                        <span className="text-gray-600">Translation:</span>
                        <span className="font-medium text-green-600">✓ English</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Stats */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="font-semibold text-sm mb-3">Processing Status</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Mode:</span>
                    <span className="font-medium capitalize">
                      {useDiarization ? 'Audio Capture' : 'Manual Entry'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Participants:</span>
                    <span className="font-medium">{participants.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Statements:</span>
                    <span className="font-medium">{conversations.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Step:</span>
                    <span className={`font-medium ${
                      conversations.length === 0 ? 'text-gray-600' :
                      !aiInstructions.trim() ? 'text-amber-600' :
                      approvalPending ? 'text-blue-600' :
                      mode === 'action' ? 'text-green-600' : 
                      'text-gray-600'
                    }`}>
                      {conversations.length === 0 ? '1. Recording' :
                       !aiInstructions.trim() ? '2. Instructions' :
                       approvalPending ? '3. Review' :
                       mode === 'action' ? '✓ Complete' : 
                       '2. Instructions'}
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Suggestion */}
              {aiResponse && (
                <div className="bg-white rounded-lg border border-brand-200 p-4 bg-brand-50">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    <Eye size={16} className="text-brand-600" /> AI Suggestion
                  </h4>
                  <div className="bg-white rounded p-3 max-h-64 overflow-y-auto mb-3">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{aiResponse}</p>
                  </div>

                  {approvalPending && (
                    <div className="space-y-2">
                      <button
                        onClick={approveAction}
                        disabled={loading}
                        className="w-full btn-primary flex items-center justify-center gap-2"
                      >
                        {loading ? <Loader size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                        {loading ? 'Executing...' : 'Approve & Execute'}
                      </button>
                      <button
                        onClick={rejectAction}
                        disabled={loading}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2"
                      >
                        <AlertCircle size={16} /> Reject & Refine
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Action Complete */}
              {mode === 'action' && !aiResponse && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-700 mb-3">
                    <CheckCircle2 size={18} />
                    <span className="font-semibold">Action Completed</span>
                  </div>
                  <button
                    onClick={doResetConversation}
                    className="w-full btn-primary"
                  >
                    Start New Conversation
                  </button>
                </div>
              )}

              {/* Helper Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <h5 className="font-semibold text-xs text-blue-900 mb-2">How it works:</h5>
                <ol className="text-xs text-blue-800 space-y-1">
                  <li>1. Add participants (2 or more)</li>
                  <li>2. Record their conversation</li>
                  <li>3. Tell AI what to do</li>
                  <li>4. Review AI suggestion</li>
                  <li>5. Approve or refine</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
