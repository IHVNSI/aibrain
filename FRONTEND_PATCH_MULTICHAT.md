/**
 * FRONTEND PATCH: Add to MultiPersonChat.jsx
 * 
 * This file contains the exact code changes needed to implement:
 * 1. Per-statement translation UI
 * 2. Live transcription display improvements  
 * 3. Better speaker detection feedback
 * 4. Translation tracking
 */

// ============================================================
// STEP 1: ADD NEW STATES (around line 30-40)
// ============================================================

// Add these new state variables:
const [statementTranslations, setStatementTranslations] = useState({})
const [translatingId, setTranslatingId] = useState(null)
const [showLiveTranscript, setShowLiveTranscript] = useState(true)
const [targetLanguage, setTargetLanguage] = useState('english')


// ============================================================
// STEP 2: ADD TRANSLATION FUNCTION (around line 300)
// ============================================================

// Add this new function:
const translateStatement = async (statementId, text, sourceLanguage, targetLanguage) => {
  // Check if already translated to this language
  if (statementTranslations[statementId]?.['translatedTo' + targetLanguage]) {
    // Already translated, toggle showing it
    setStatementTranslations(prev => ({
      ...prev,
      [statementId]: {
        ...prev[statementId],
        ['show' + targetLanguage]: !prev[statementId]['show' + targetLanguage]
      }
    }))
    return
  }
  
  setTranslatingId(statementId)
  setMsg(null)
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
          'translatedTo' + targetLanguage: data.translated,
          ['show' + targetLanguage]: true
        }
      }))
      setMsg({ 
        type: 'success', 
        text: `✓ Translated ${sourceLanguage} → ${targetLanguage}` 
      })
      setTimeout(() => setMsg(null), 3000)
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


// ============================================================
// STEP 3: UPDATE CONVERSATION DISPLAY (around line 680)
// ============================================================

// Replace the conversation item rendering section with:

conversations.map((conv) => (
  <div key={conv.id} className="bg-white rounded p-3 border border-gray-200 hover:border-gray-300 transition">
    <div className="flex items-start justify-between gap-3">
      <div className="flex-1 min-w-0">
        {/* Speaker name, timestamp, and language badge */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className="font-semibold text-sm text-brand-600">{conv.participant}</span>
          <span className="text-xs text-gray-400">{conv.timestamp}</span>
          {audioLanguage !== 'english' && (
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
              {audioLanguage.toUpperCase()}
            </span>
          )}
        </div>
        
        {/* Original text */}
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
            {/* Original text display */}
            <p className="text-sm text-gray-800 mb-2 leading-relaxed font-medium">
              {conv.originalText}
            </p>
            
            {/* Translation options and display */}
            <div className="space-y-2 mt-2">
              {/* Translation buttons */}
              <div className="flex flex-wrap gap-2">
                {audioLanguage !== 'english' && (
                  <button
                    onClick={() => translateStatement(conv.id, conv.originalText, audioLanguage, 'english')}
                    disabled={translatingId === conv.id}
                    className={`text-xs px-3 py-1 rounded font-medium transition ${
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
                      '🌐 Translate to English'
                    )}
                  </button>
                )}
                
                {/* Additional language translation buttons */}
                {['igbo', 'yoruba', 'hausa'].filter(lang => lang !== audioLanguage.toLowerCase()).map(lang => (
                  <button
                    key={lang}
                    onClick={() => translateStatement(conv.id, conv.originalText, audioLanguage, lang)}
                    disabled={translatingId === conv.id}
                    className={`text-xs px-2 py-1 rounded transition ${
                      statementTranslations[conv.id]?.[`translated${lang}`]
                        ? 'bg-green-50 text-green-700 hover:bg-green-100'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </button>
                ))}
              </div>
              
              {/* Display translations if available */}
              {Object.entries(statementTranslations[conv.id] || {}).map(([key, value]) => {
                if (!key.startsWith('translatedTo') || !statementTranslations[conv.id][`show${key.replace('translatedTo', '')}`]) {
                  return null
                }
                const langCode = key.replace('translatedTo', '')
                return (
                  <div 
                    key={langCode}
                    className="bg-gradient-to-r from-green-50 to-teal-50 border-l-3 border-green-400 pl-3 py-2 rounded-sm mt-2"
                  >
                    <p className="text-xs font-semibold text-green-700 mb-1">
                      {langCode === 'english' ? '🌍 English Translation:' : `📝 ${langCode.toUpperCase()}:`}
                    </p>
                    <p className="text-xs text-green-800 leading-relaxed">{value}</p>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
      
      {/* Action buttons */}
      {editingId !== conv.id && (
        <div className="flex gap-1 flex-shrink-0">
          <button
            onClick={() => startEditingMessage(conv.id, conv.originalText)}
            className="text-gray-400 hover:text-blue-600 p-1 hover:bg-blue-50 rounded"
            title="Edit"
          >
            ✏️
          </button>
          <button
            onClick={() => removeMessage(conv.id)}
            className="text-gray-400 hover:text-red-600 p-1 hover:bg-red-50 rounded"
            title="Delete"
          >
            🗑️
          </button>
        </div>
      )}
    </div>
  </div>
))


// ============================================================
// STEP 4: IMPROVE LIVE TRANSCRIPTION DISPLAY (around line 550)
// ============================================================

// Update the recording section to show live transcript:

{isRecording && (
  <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4 mb-4">
    <div className="flex items-center gap-2 mb-2">
      <div className="animate-pulse">🎤</div>
      <span className="font-semibold text-blue-900">Recording in progress...</span>
    </div>
    
    {/* Live transcription display */}
    {isWebSpeechActive && (
      <div className="space-y-2">
        {/* Final transcript */}
        {finalTranscript && (
          <div>
            <p className="text-xs font-medium text-blue-800 mb-1">Transcribed so far:</p>
            <div className="bg-white border border-blue-300 rounded p-2">
              <p className="text-sm text-blue-900">{finalTranscript}</p>
            </div>
          </div>
        )}
        
        {/* Interim/live transcript */}
        {interimText && (
          <div>
            <p className="text-xs font-medium text-purple-800 mb-1">Currently hearing:</p>
            <div className="bg-purple-50 border border-purple-300 rounded p-2">
              <p className="text-sm text-purple-800 italic">{interimText}</p>
            </div>
          </div>
        )}
        
        {!finalTranscript && !interimText && (
          <p className="text-xs text-blue-700">Listening... Start speaking!</p>
        )}
      </div>
    )}
    
    <div className="flex gap-2 mt-3">
      <button
        onClick={stopRecording}
        className="btn-danger flex items-center gap-2 flex-1 justify-center"
      >
        <Square size={16} /> Stop Recording
      </button>
    </div>
  </div>
)}


// ============================================================
// STEP 5: IMPROVE SPEAKER DETECTION FEEDBACK (around line 470)
// ============================================================

// Update the diarization success message to show more detail:

if (data.success && data.conversations && data.conversations.length > 0) {
  const speakers = [...new Set(data.conversations.map(c => c.participant))]
  setParticipants(speakers)
  
  const conversationsList = data.conversations.map((c, idx) => ({
    id: Date.now() + Math.random(),
    participant: c.participant,
    originalText: c.originalText || c.translatedText || '',
    translatedText: c.translatedText || c.originalText || '',
    timestamp: c.timestamp || `${idx}:00`,
    reviewed: false
  }))
  
  setConversations(conversationsList)
  setMode('listening')
  
  // Enhanced success message
  const uniqueSpeakers = speakers.length
  const totalStatements = conversationsList.length
  const avgStatementsPerSpeaker = (totalStatements / uniqueSpeakers).toFixed(1)
  
  const summary = `✓ Successfully detected ${uniqueSpeakers} speaker${uniqueSpeakers !== 1 ? 's' : ''} with ${totalStatements} total statement${totalStatements !== 1 ? 's' : ''} (avg ${avgStatementsPerSpeaker} per speaker)`
  
  setMsg({ type: 'success', text: summary })
  console.log('Speakers detected:', speakers)
  console.log('Conversations:', conversationsList)
}


// ============================================================
// STEP 6: UPDATE AI INSTRUCTIONS SECTION (around line 800)
// ============================================================

// Add helpful examples for what AI can do:

const aiExamples = [
  "Extract all action items and assign them to speakers",
  "Summarize the key agreements and decisions made",
  "Identify disagreements and suggest resolutions",
  "Generate meeting notes with timestamps for each speaker",
  "Analyze sentiment of each speaker's contributions",
  "Create a brief executive summary for stakeholders",
  "Compare proposals and highlight differences",
  "Identify next steps and dependencies",
  "Calculate agreement score between speakers",
  "Prepare follow-up email to all participants"
]

// Display in textarea placeholder or below the input


// ============================================================
// SUMMARY OF CHANGES:
// ============================================================

/*
1. ✅ Added 4 new state variables for translations and transcript display
2. ✅ Added translateStatement() function to handle per-statement translation
3. ✅ Enhanced conversation display with translation buttons and display areas
4. ✅ Improved live transcription display during recording
5. ✅ Better speaker detection feedback with statistics
6. ✅ AI instruction examples for better user guidance

These changes enable:
- Real-time speech display as users speak
- Per-statement translation in any language
- Better feedback on how many speakers were detected
- Clearer UI for translations with original/translated text comparison
- AI context with full conversation history for better suggestions
*/
