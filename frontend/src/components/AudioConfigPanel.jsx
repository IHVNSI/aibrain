import React, { useState, useEffect, useRef } from 'react'
import { Mic, Volume2, Settings, AlertCircle, CheckCircle, Loader, Edit2, Save, X } from 'lucide-react'
import api from '../api/client'

/**
 * Redesigned Audio Configuration Tab
 * Groups STT and TTS with individual configuration, testing, and monitoring
 */
function AudioConfigPanel() {
  const [activeTab, setActiveTab] = useState('overview') // overview, stt, tts, voice-training
  const [settings, setSettings] = useState({
    // STT Settings
    sttModel: 'naijavox',
    sttApiKey: '',
    sttLanguage: 'english',
    
    // TTS Settings
    ttsModel: 'google-cloud',
    ttsApiKey: '',
    ttsLanguage: 'english',
    voiceGender: 'female',
    pitch: 1,
    rate: 1,
    volume: 0.8,
    
    // Training
    voiceTrainingSamples: [],
  })

  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sttStatus, setSttStatus] = useState({ status: 'unknown', message: 'Not tested' })
  const [ttsStatus, setTtsStatus] = useState({ status: 'unknown', message: 'Not tested' })
  const [testingAudio, setTestingAudio] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)

  // STT Models Configuration
  const STT_MODELS = [
    {
      id: 'naijavox',
      name: 'NaijaVox-2.0',
      description: 'Best for Nigerian languages (Yoruba, Hausa, Igbo)',
      requiresKey: false,
      status: 'local',
      languages: ['english', 'igbo', 'hausa', 'yoruba', 'pidgin']
    },
    {
      id: 'web-speech',
      name: 'Web Speech API',
      description: 'Built-in browser speech recognition (free, local)',
      requiresKey: false,
      status: 'local',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'whisper',
      name: 'OpenAI Whisper (Large-v3)',
      description: 'Multilingual with excellent African language support',
      requiresKey: true,
      keyName: 'OPENAI_API_KEY',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba', 'pidgin']
    },
    {
      id: 'google-cloud-stt',
      name: 'Google Cloud Speech-to-Text',
      description: 'Native African language support (ig-NG, ha-NG, yo-NG)',
      requiresKey: true,
      keyName: 'GOOGLE_CLOUD_CREDENTIALS',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'azure-stt',
      name: 'Azure Speech-to-Text',
      description: 'Microsoft\'s speech recognition service',
      requiresKey: true,
      keyName: 'AZURE_SPEECH_KEY',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'elevenlabs',
      name: 'ElevenLabs Scribe API',
      description: 'Premium with speaker diarization',
      requiresKey: true,
      keyName: 'ELEVENLABS_API_KEY',
      status: 'premium',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    }
  ]

  // TTS Models Configuration
  const TTS_MODELS = [
    {
      id: 'browser',
      name: 'Browser Native TTS',
      description: 'Built-in browser speech synthesis (free, local, English only)',
      requiresKey: false,
      status: 'local',
      languages: ['english']
    },
    {
      id: 'google-chirp',
      name: 'Google Chirp TTS',
      description: 'Affordable Google TTS service with natural voices',
      requiresKey: true,
      keyName: 'GOOGLE_CLOUD_CREDENTIALS',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'google-cloud',
      name: 'Google Cloud Text-to-Speech',
      description: 'Premium Google service, best for African languages',
      requiresKey: true,
      keyName: 'GOOGLE_CLOUD_CREDENTIALS',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'azure-tts',
      name: 'Azure Text-to-Speech',
      description: 'Microsoft\'s neural TTS with diverse voices',
      requiresKey: true,
      keyName: 'AZURE_SPEECH_KEY',
      status: 'cloud',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'elevenlabs-tts',
      name: 'ElevenLabs Text-to-Speech',
      description: 'Premium voices with voice cloning support',
      requiresKey: true,
      keyName: 'ELEVENLABS_API_KEY',
      status: 'premium',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    },
    {
      id: 'yarngpt-tts',
      name: 'YarnGPT Text-to-Speech',
      description: 'Premium multilingual voices with natural speech patterns',
      requiresKey: true,
      keyName: 'YARNGPT_API_KEY',
      status: 'premium',
      languages: ['english', 'igbo', 'hausa', 'yoruba']
    }
  ]

  const LANGUAGES = [
    { code: 'english', label: 'English' },
    { code: 'igbo', label: 'Igbo' },
    { code: 'hausa', label: 'Hausa' },
    { code: 'yoruba', label: 'Yoruba' },
    { code: 'pidgin', label: 'Nigerian Pidgin' }
  ]

  const TEST_MESSAGES = {
    english: 'Welcome, how are you doing today',
    igbo: 'Nnoo, kedu ka ị na-eme taa',
    hausa: 'Maraba, yaya kuke ji taa',
    yoruba: 'Kaabo, bawo lo n se loni',
    pidgin: 'Welcome, how you dey do tida'
  }

  // Load settings from API
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const { data } = await api.get('/api/settings/user')
      if (data.settings?.audio_settings) {
        setSettings(prev => ({ ...prev, ...data.settings.audio_settings }))
      }
    } catch (e) {
      console.error('Failed to load audio settings:', e)
    }
  }

  const saveSettings = async (updatedSettings) => {
    try {
      const newSettings = { ...settings, ...updatedSettings }
      setSettings(newSettings)
      await api.post('/api/settings/user', { audio_settings: newSettings })
      setMsg({ type: 'success', text: 'Settings saved successfully' })
      setTimeout(() => setMsg(null), 2000)
      return true
    } catch (e) {
      console.error('Failed to save settings:', e)
      setMsg({ type: 'error', text: 'Failed to save settings' })
      return false
    }
  }

  const testSTT = async () => {
    setLoading(true)
    setSttStatus({ status: 'testing', message: 'Testing STT service...' })
    try {
      const { data } = await api.post('/api/voice/test-transcription', {
        language: settings.sttLanguage || 'english',
        stt_provider: settings.sttModel || 'naijavox'
      })
      
      if (data.success) {
        setSttStatus({
          status: 'success',
          message: `✓ ${data.provider || STT_MODELS.find(m => m.id === settings.sttModel)?.name || 'STT'} working - ${data.message || ''}`
        })
      } else {
        setSttStatus({
          status: 'error',
          message: `✗ ${data.error || 'STT service not configured'}`
        })
      }
    } catch (e) {
      setSttStatus({
        status: 'error',
        message: `✗ ${e.response?.data?.error || 'Failed to test STT service'}`
      })
    } finally {
      setLoading(false)
    }
  }

  const testTTS = async () => {
    setTestingAudio(true)
    setTtsStatus({ status: 'testing', message: 'Testing TTS service...' })
    try {
      const language = settings.ttsLanguage || 'english'
      const testMessage = TEST_MESSAGES[language] || TEST_MESSAGES.english

      const { data } = await api.post('/api/chat/synthesize-speech', {
        text: testMessage,
        language: language,
        gender: settings.voiceGender === 'male' ? 'MALE' : 'FEMALE',
        tts_provider: settings.ttsModel || 'browser'
      })

      if (data.success) {
        // Check if using browser native TTS (for English)
        if (data.use_browser_tts) {
          // Use Web Speech API for English
          const utterance = new SpeechSynthesisUtterance(testMessage)
          utterance.lang = language === 'english' ? 'en-US' : language
          utterance.rate = parseFloat(settings.rate || 1)
          utterance.pitch = 1
          utterance.volume = parseFloat(settings.volume || 0.8)
          
          // Get voice - prefer female if available
          const voices = speechSynthesis.getVoices()
          const selectedGender = settings.voiceGender === 'male' ? 'Google UK English Male' : 'Google UK English Female'
          const voice = voices.find(v => v.name.includes(selectedGender)) || voices.find(v => v.lang.includes('en')) || voices[0]
          if (voice) utterance.voice = voice
          
          speechSynthesis.cancel()
          speechSynthesis.speak(utterance)
          
          setTtsStatus({
            status: 'success',
            message: '✓ Browser native TTS is working (free, English)'
          })
        } else if (data.audio) {
          // Use cloud TTS audio
          const audio = new Audio(data.audio)
          audio.volume = parseFloat(settings.volume || 0.8)
          await audio.play()
          
          setTtsStatus({
            status: 'success',
            message: `✓ ${data.provider || 'TTS'} working - ${data.cost || ''}`
          })
        } else {
          setTtsStatus({
            status: 'success',
            message: `✓ TTS configured (${data.provider})`
          })
        }
      } else {
        setTtsStatus({
          status: 'error',
          message: data.error || 'TTS service not configured'
        })
      }
    } catch (e) {
      setTtsStatus({
        status: 'error',
        message: e.response?.data?.error || 'Failed to test TTS service'
      })
    } finally {
      setTestingAudio(false)
    }
  }

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      audioChunksRef.current = []
      
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      setMsg({ type: 'success', text: 'Recording voice sample... Speak clearly.' })
    } catch (e) {
      setMsg({ type: 'error', text: 'Cannot access microphone: ' + e.message })
    }
  }

  const stopVoiceRecording = async () => {
    if (!mediaRecorderRef.current) return
    
    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
      streamRef.current?.getTracks().forEach(track => track.stop())
      await uploadVoiceSample(audioBlob)
    }
    
    mediaRecorderRef.current.stop()
    setIsRecording(false)
  }

  const uploadVoiceSample = async (audioBlob) => {
    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('voice_sample', audioBlob, 'voice_sample.wav')
      
      const { data } = await api.post('/api/multiperson/train-user-voice', formData)
      
      if (data.success) {
        setSettings(prev => ({
          ...prev,
          voiceTrainingSamples: [...(prev.voiceTrainingSamples || []), data.voice_id]
        }))
        setMsg({
          type: 'success',
          text: `✓ Voice sample enrolled! (${data.samples_count || 1} samples total)`
        })
      } else {
        setMsg({ type: 'error', text: data.error || 'Failed to enroll voice sample' })
      }
    } catch (e) {
      setMsg({ type: 'error', text: 'Failed to upload voice sample: ' + e.message })
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="text-green-600" size={16} />
      case 'error':
        return <AlertCircle className="text-red-600" size={16} />
      case 'testing':
        return <Loader className="text-blue-600 animate-spin" size={16} />
      default:
        return <AlertCircle className="text-gray-400" size={16} />
    }
  }

  return (
    <div className="space-y-4 max-w-4xl">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 sticky top-0 bg-white p-3 rounded-t-lg">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded text-sm font-medium transition ${
            activeTab === 'overview'
              ? 'bg-blue-100 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('stt')}
          className={`px-4 py-2 rounded text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'stt'
              ? 'bg-blue-100 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Mic size={14} /> Speech-to-Text (STT)
        </button>
        <button
          onClick={() => setActiveTab('tts')}
          className={`px-4 py-2 rounded text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'tts'
              ? 'bg-blue-100 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Volume2 size={14} /> Text-to-Speech (TTS)
        </button>
        <button
          onClick={() => setActiveTab('voice-training')}
          className={`px-4 py-2 rounded text-sm font-medium transition flex items-center gap-2 ${
            activeTab === 'voice-training'
              ? 'bg-blue-100 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Mic size={14} /> Voice Training
        </button>
      </div>

      {/* Messages */}
      {msg && (
        <div className={`p-3 rounded-lg flex gap-2 items-start ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {msg.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          <p className="text-sm">{msg.text}</p>
        </div>
      )}

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* STT Status */}
            <div className="border border-gray-200 rounded-lg p-4 bg-white">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-sm text-gray-900">Speech-to-Text (STT)</h3>
                  <p className="text-xs text-gray-500 mt-1">Voice input transcription</p>
                </div>
                {getStatusIcon(sttStatus.status)}
              </div>
              
              <div className="text-xs text-gray-600 mb-3">
                <p className="font-medium">{STT_MODELS.find(m => m.id === settings.sttModel)?.name}</p>
                <p className="text-gray-500 mt-1">{sttStatus.message}</p>
              </div>
              
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-700">Language:</p>
                <select
                  value={settings.sttLanguage}
                  onChange={(e) => saveSettings({ sttLanguage: e.target.value })}
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.code}>{lang.label}</option>
                  ))}
                </select>
              </div>
              
              <button
                onClick={testSTT}
                disabled={loading}
                className="btn-primary w-full mt-3 text-xs"
              >
                {loading ? 'Testing...' : 'Test STT'}
              </button>
            </div>

            {/* TTS Status */}
            <div className="border border-gray-200 rounded-lg p-4 bg-white">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-sm text-gray-900">Text-to-Speech (TTS)</h3>
                  <p className="text-xs text-gray-500 mt-1">Voice output synthesis</p>
                </div>
                {getStatusIcon(ttsStatus.status)}
              </div>
              
              <div className="text-xs text-gray-600 mb-3">
                <p className="font-medium">{TTS_MODELS.find(m => m.id === settings.ttsModel)?.name}</p>
                <p className="text-gray-500 mt-1">{ttsStatus.message}</p>
              </div>
              
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-700">Language:</p>
                <select
                  value={settings.ttsLanguage}
                  onChange={(e) => saveSettings({ ttsLanguage: e.target.value })}
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.code}>{lang.label}</option>
                  ))}
                </select>
              </div>
              
              <button
                onClick={testTTS}
                disabled={testingAudio}
                className="btn-primary w-full mt-3 text-xs"
              >
                {testingAudio ? 'Playing...' : 'Test TTS'}
              </button>
            </div>
          </div>

          {/* Quick Settings */}
          <div className="border border-gray-200 rounded-lg p-4 bg-white">
            <h3 className="font-semibold text-sm text-gray-900 mb-3">Voice Output Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-700">Gender</label>
                <select
                  value={settings.voiceGender}
                  onChange={(e) => saveSettings({ voiceGender: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 text-xs border border-gray-300 rounded"
                >
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>
              
              <div>
                <label className="text-xs font-medium text-gray-700">Volume</label>
                <input
                  type="range"
                  min="0" max="1" step="0.1"
                  value={settings.volume}
                  onChange={(e) => saveSettings({ volume: parseFloat(e.target.value) })}
                  className="w-full mt-1"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-700">Pitch</label>
                <input
                  type="range"
                  min="0.5" max="2" step="0.1"
                  value={settings.pitch}
                  onChange={(e) => saveSettings({ pitch: parseFloat(e.target.value) })}
                  className="w-full mt-1"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-700">Rate</label>
                <input
                  type="range"
                  min="0.5" max="2" step="0.1"
                  value={settings.rate}
                  onChange={(e) => saveSettings({ rate: parseFloat(e.target.value) })}
                  className="w-full mt-1"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STT CONFIGURATION TAB */}
      {activeTab === 'stt' && (
        <div className="space-y-4">
          <div className="border border-gray-200 rounded-lg p-4 bg-white">
            <h3 className="font-semibold text-sm text-gray-900 mb-4">Speech-to-Text (STT) Models</h3>
            
            <div className="space-y-3">
              {STT_MODELS.map(model => (
                <div
                  key={model.id}
                  className={`p-3 border rounded-lg cursor-pointer transition ${
                    settings.sttModel === model.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => saveSettings({ sttModel: model.id })}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-medium text-sm text-gray-900">{model.name}</p>
                      <p className="text-xs text-gray-600 mt-1">{model.description}</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      model.status === 'local' ? 'bg-purple-100 text-purple-700' :
                      model.status === 'cloud' ? 'bg-blue-100 text-blue-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {model.status === 'local' ? '💻 Local' : model.status === 'cloud' ? '☁️ Cloud' : '✨ Premium'}
                    </span>
                  </div>
                  
                  <div className="text-xs text-gray-600">
                    Languages: {model.languages.join(', ')}
                  </div>

                  {model.requiresKey && (
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                      Requires API Key: {model.keyName}
                    </div>
                  )}

                  {settings.sttModel === model.id && (
                    <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-800 flex items-center gap-2">
                      <CheckCircle size={14} /> Selected
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* STT Configuration Help */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-blue-900 mb-2">📋 Configuration Guide</p>
            <div className="text-xs text-blue-800 space-y-1">
              <p>• <strong>NaijaVox-2.0:</strong> FREE! Best for Nigerian languages (Igbo, Yoruba, Hausa). Auto-downloads ~2.5GB.</p>
              <p>• <strong>Whisper:</strong> Uses your existing OPENAI_API_KEY for excellent multilingual support.</p>
              <p>• <strong>Google Cloud:</strong> Best accuracy for African languages. Requires paid service account.</p>
              <p>• <strong>ElevenLabs:</strong> Requires ELEVENLABS_API_KEY in .env</p>
              <p className="text-blue-700 font-semibold mt-2">💡 <strong>Quick Start:</strong> NaijaVox-2.0 is completely free and optimized for your languages!</p>
            </div>
          </div>
        </div>
      )}

      {/* TTS CONFIGURATION TAB */}
      {activeTab === 'tts' && (
        <div className="space-y-4">
          <div className="border border-gray-200 rounded-lg p-4 bg-white">
            <h3 className="font-semibold text-sm text-gray-900 mb-4">Text-to-Speech (TTS) Models</h3>
            
            <div className="space-y-3">
              {TTS_MODELS.map(model => (
                <div
                  key={model.id}
                  className={`p-3 border rounded-lg cursor-pointer transition ${
                    settings.ttsModel === model.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => saveSettings({ ttsModel: model.id })}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-medium text-sm text-gray-900">{model.name}</p>
                      <p className="text-xs text-gray-600 mt-1">{model.description}</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      model.status === 'local' ? 'bg-purple-100 text-purple-700' :
                      model.status === 'cloud' ? 'bg-blue-100 text-blue-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {model.status === 'local' ? '💻 Local' : model.status === 'cloud' ? '☁️ Cloud' : '✨ Premium'}
                    </span>
                  </div>
                  
                  <div className="text-xs text-gray-600">
                    Languages: {model.languages.join(', ')}
                  </div>

                  {model.requiresKey && (
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                      Requires API Key: {model.keyName}
                    </div>
                  )}

                  {settings.ttsModel === model.id && (
                    <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-800 flex items-center gap-2">
                      <CheckCircle size={14} /> Selected
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* TTS Configuration Help */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-blue-900 mb-2">📋 Configuration Guide</p>
            <div className="text-xs text-blue-800 space-y-1">
              <p>• <strong>Google Cloud TTS:</strong> Best for African languages. Requires paid service account.</p>
              <p>• <strong>ElevenLabs TTS:</strong> Premium voices. Requires ELEVENLABS_API_KEY in .env</p>
              <p>• <strong>Browser TTS:</strong> Free, built-in, works for English</p>
              <p className="text-blue-700 font-semibold mt-2">💡 <strong>No paid service?</strong> See docs/AUDIO_SETUP_FREE_TIER.md for free speech-to-text alternatives (NaijaVox-2.0, Whisper)</p>
            </div>
          </div>
        </div>
      )}

      {/* VOICE TRAINING TAB */}
      {activeTab === 'voice-training' && (
        <div className="space-y-4">
          <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
            <h3 className="font-semibold text-sm text-purple-900 mb-2">Voice Training for Speaker Identification</h3>
            <p className="text-xs text-purple-800 mb-4">
              Enroll voice samples so the system can identify you in multi-person conversations.
              This trains speaker identification, NOT AI content understanding.
              See docs/VOICE_TRAINING_EXPLAINED.md for details.
            </p>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-white rounded p-3 border border-purple-200">
                <p className="text-xs font-medium text-gray-700 mb-2">Enrolled Samples</p>
                <p className="text-lg font-bold text-purple-600">
                  {settings.voiceTrainingSamples?.length || 0} / 3
                </p>
              </div>
              <div className="bg-white rounded p-3 border border-purple-200">
                <p className="text-xs font-medium text-gray-700 mb-2">Status</p>
                <p className="text-sm font-semibold text-purple-600">
                  {(settings.voiceTrainingSamples?.length || 0) >= 2 ? '✓ Ready' : '⏳ Pending'}
                </p>
              </div>
            </div>

            {!isRecording ? (
              <button
                onClick={startVoiceRecording}
                disabled={loading || (settings.voiceTrainingSamples?.length || 0) >= 3}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Mic size={16} /> Record Voice Sample
              </button>
            ) : (
              <button
                onClick={stopVoiceRecording}
                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium text-sm flex items-center justify-center gap-2 animate-pulse"
              >
                <Mic size={16} /> Stop Recording
              </button>
            )}

            <p className="text-xs text-gray-600 mt-3">
              💡 Tip: Record 2-3 clear voice samples (5-10 seconds each) for best speaker identification accuracy.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default AudioConfigPanel
