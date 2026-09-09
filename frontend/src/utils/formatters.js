/**
 * Format database column names to user-friendly headers.
 * snake_case → Title Case, camelCase → Title Case, etc.
 */
export function formatColumnName(col) {
  if (!col || typeof col !== 'string') return col
  return col
    .replace(/([_-])/g, ' ') // Replace underscores/hyphens with spaces
    .replace(/([a-z])([A-Z])/g, '$1 $2') // Insert space before uppercase letters
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Copy text to clipboard.
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    console.error('Copy failed:', err)
    return false
  }
}

/**
 * Export HTML element as image (PNG or JPG).
 */
export async function exportAsImage(element, filename = 'export', format = 'png') {
  try {
    const normalized = format === 'jpg' ? 'jpeg' : format
    const { default: html2canvas } = await import('html2canvas')
    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2,
    })
    const link = document.createElement('a')
    link.href = canvas.toDataURL(`image/${normalized}`)
    link.download = `${filename}.${format}`
    link.click()
    return true
  } catch (err) {
    console.error('Export failed:', err)
    return false
  }
}

/**
 * Speak text using Web Speech API with customizable audio settings.
 * @param {string} text - The text to speak
 * @param {object} audioSettings - Optional audio settings object {voiceGender, pitch, rate, volume, voiceInputLanguage}
 */
export function speakText(text, audioSettings) {
  if (!('speechSynthesis' in window)) {
    console.warn('Speech Synthesis API not supported')
    return false
  }
  if (!text || !text.trim()) return false
  
  // Clean markdown formatting from text
  let cleanText = text
    .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold (**)
    .replace(/\*(.*?)\*/g, '$1') // Remove italic (*)
    .replace(/__(.*?)__/g, '$1') // Remove bold (__)
    .replace(/_(.*?)_/g, '$1') // Remove italic (_)
    .replace(/~~(.*?)~~/g, '$1') // Remove strikethrough
    .replace(/`(.*?)`/g, '$1') // Remove inline code (`)
    .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove links, keep text
    .replace(/^#+\s/gm, '') // Remove markdown headers
    .replace(/^>\s/gm, '') // Remove blockquote markers
    .replace(/^[-*+]\s/gm, '') // Remove list markers
    .trim()
  
  const synth = window.speechSynthesis
  const utterance = new SpeechSynthesisUtterance(cleanText)
  
  // Use provided settings or load from localStorage as fallback
  let settings = audioSettings || {
    voiceGender: 'female',
    pitch: 1,
    rate: 1,
    volume: 1,
    voiceInputLanguage: 'english',
  }
  if (!audioSettings) {
    try {
      const saved = localStorage.getItem('audioSettings')
      if (saved) {
        settings = JSON.parse(saved)
      }
    } catch (e) {
      console.error('Failed to load audio settings:', e)
    }
  }
  
  // Map language codes to browser language codes
  // For languages without native browser support, fall back to English
  const languageMap = {
    'english': 'en-US',
    'igbo': 'en-US', // Fallback: Igbo not widely supported by browsers; speak English
    'hausa': 'en-US', // Fallback: Hausa not widely supported by browsers; speak English
    'yoruba': 'en-US', // Fallback: Yoruba not widely supported by browsers; speak English
  }
  
  const userLanguage = settings.voiceInputLanguage || 'english'
  const languageCode = languageMap[userLanguage.toLowerCase()] || 'en-US'
  
  // Apply audio settings
  utterance.pitch = parseFloat(settings.pitch) || 1
  utterance.rate = parseFloat(settings.rate) || 1
  utterance.volume = parseFloat(settings.volume) || 1
  utterance.lang = languageCode

  const speakWithVoices = () => {
    const voices = synth.getVoices()
    if (voices && voices.length) {
      // Find voice matching the selected gender
      let selectedVoice
      if (settings.voiceGender === 'male') {
        selectedVoice = voices.find((v) => v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('man'))
      } else if (settings.voiceGender === 'female') {
        selectedVoice = voices.find((v) => v.name.toLowerCase().includes('female') || v.name.toLowerCase().includes('woman'))
      }
      // Fallback to default or first voice
      utterance.voice = selectedVoice || voices.find((v) => v.default) || voices[0]
    }
    synth.cancel()
    synth.speak(utterance)
    if (synth.paused) synth.resume()
  }

  if (synth.getVoices().length) {
    speakWithVoices()
    return true
  }

  const onVoices = () => {
    speakWithVoices()
    synth.removeEventListener('voiceschanged', onVoices)
  }
  synth.addEventListener('voiceschanged', onVoices)
  // Fallback in case voiceschanged does not fire.
  setTimeout(() => {
    if (synth.speaking || synth.pending) return
    speakWithVoices()
  }, 300)
  return true
}
