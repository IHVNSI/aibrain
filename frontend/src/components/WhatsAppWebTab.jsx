/**
 * WhatsApp Web Component - Login and send/receive messages via WhatsApp Web
 * No official API required - uses Selenium for browser automation
 */
import React, { useState, useEffect } from 'react'
import axios from 'axios'
import Swal from 'sweetalert2'
import AuthorizedContactsPanel from './AuthorizedContactsPanel'
import {
  MessageCircle, LogIn, LogOut, Send, Loader, CheckCircle2,
  AlertCircle, MessageSquare, Clock, Lock, ChevronDown
} from 'lucide-react'

export default function WhatsAppWebTab() {
  // State
  const [loggedIn, setLoggedIn] = useState(false)
  const [loading, setLoading] = useState(false)
  const [checkingStatus, setCheckingStatus] = useState(true)
  const [showAuthorizedNumbers, setShowAuthorizedNumbers] = useState(false)
  
  // Send message form
  const [phoneNumber, setPhoneNumber] = useState('')
  const [messageText, setMessageText] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [sendFormOpen, setSendFormOpen] = useState(false)
  
  // Chat list and messages
  const [chats, setChats] = useState([])
  const [selectedChat, setSelectedChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingMessages, setLoadingMessages] = useState(false)
  
  // Direct AI message handling
  const [directMessage, setDirectMessage] = useState('')
  const [directSenderName, setDirectSenderName] = useState('User')
  const [processingDirectMessage, setProcessingDirectMessage] = useState(false)
  const [aiResponses, setAiResponses] = useState([])
  const [aiFormOpen, setAiFormOpen] = useState(false)
  
  // Auto-processed messages (from message listener)
  const [autoProcessedResponses, setAutoProcessedResponses] = useState([])
  const [listenerActive, setListenerActive] = useState(false)

  // Check login status on mount and poll continuously
  useEffect(() => {
    checkLoginStatus()
    
    // Poll for login status every 3 seconds (includes during QR scan)
    const statusPollInterval = setInterval(async () => {
      try {
        const response = await axios.get('/api/whatsapp/status')
        setLoggedIn(response.data.logged_in)
        if (response.data.logged_in) {
          loadChats()
        }
      } catch (error) {
        console.error('Status poll error:', error)
      }
    }, 3000) // Poll every 3 seconds
    
    return () => clearInterval(statusPollInterval)
  }, [])
  
  // Poll for auto-processed messages when logged in
  useEffect(() => {
    if (!loggedIn) return
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get('/api/whatsapp/processed-responses')
        if (response.data.success) {
          setAutoProcessedResponses(response.data.responses || [])
          setListenerActive(response.data.listener_active || false)
        }
      } catch (error) {
        console.error('Error fetching processed responses:', error)
      }
    }, 2000) // Poll every 2 seconds
    
    return () => clearInterval(pollInterval)
  }, [loggedIn])

  const checkLoginStatus = async () => {
    try {
      setCheckingStatus(true)
      const response = await axios.get('/api/whatsapp/status')
      setLoggedIn(response.data.logged_in)
      if (response.data.logged_in) {
        loadChats()
      }
    } catch (error) {
      console.error('Status check error:', error)
    } finally {
      setCheckingStatus(false)
    }
  }

  const handleLogin = async () => {
    try {
      setLoading(true)
      
      // Request login/QR code
      const response = await axios.post('/api/whatsapp/login', {
        print_terminal: true
      })
      
      if (response.data.success) {
        // Case 1: Already logged in on browser
        if (response.data.logged_in) {
          Swal.fire({
            title: '✅ Connected!',
            text: 'WhatsApp Web is already logged in. You are now connected.',
            icon: 'success',
            timer: 2500,
            timerProgressBar: true
          })
          setLoggedIn(true)
          loadChats()
          return
        }
        
        // Case 2: Need to scan QR code
        if (response.data.qr_code) {
          Swal.fire({
            title: '📱 Scan QR Code',
            html: `
              <div style="text-align: center;">
                <p style="font-size: 14px; color: #666; margin-bottom: 16px;">
                  <strong>Use your phone camera to scan this QR code:</strong>
                </p>
                <div style="background: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 12px; display: inline-block;">
                  <img 
                    src="${response.data.qr_code}" 
                    alt="WhatsApp QR Code"
                    style="width: 280px; height: 280px; display: block;" 
                  />
                </div>
                <p style="font-size: 12px; color: #999; margin: 0;">
                  A copy of this QR code has also been printed to your terminal.
                </p>
              </div>
            `,
            width: 'auto',
            padding: '1.5rem',
            allowOutsideClick: false,
            allowEscapeKey: false,
            confirmButtonText: 'Already Scanned?',
            showCancelButton: true,
            cancelButtonText: 'Cancel',
            didOpen: async () => {
              // Poll for login completion while modal is open
              let isScanned = false
              let pollInterval = setInterval(async () => {
                try {
                  const statusResponse = await axios.get('/api/whatsapp/status')
                  if (statusResponse.data.logged_in && !isScanned) {
                    isScanned = true
                    if (pollInterval) clearInterval(pollInterval)
                    
                    // Auto-close the QR modal
                    Swal.close()
                    
                    // Show success message
                    await Swal.fire({
                      title: '✅ Connected!',
                      text: 'You are now connected to WhatsApp Web.',
                      icon: 'success',
                      timer: 2000,
                      timerProgressBar: true
                    })
                    
                    // Update state and load chats
                    setLoggedIn(true)
                    loadChats()
                  }
                } catch (error) {
                  console.error('Status poll error:', error)
                }
              }, 1000) // Poll every 1 second for faster detection
              
              // Store interval for cleanup
              Swal.pollInterval = pollInterval
            },
            willClose: () => {
              // Clean up interval
              if (Swal.pollInterval) {
                clearInterval(Swal.pollInterval)
              }
            }
          }).then((result) => {
            // If user clicks "Already Scanned?" button
            if (result.isConfirmed) {
              checkLoginStatus()
            }
          })
        }
      } else {
        Swal.fire({
          title: '❌ Error',
          text: response.data.message || 'Failed to start login',
          icon: 'error'
        })
      }
    } catch (error) {
      Swal.fire({
        title: '❌ Error',
        text: error.response?.data?.error || error.message || 'Failed to login',
        icon: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      await axios.post('/api/whatsapp/logout', {})
      setLoggedIn(false)
      setChats([])
      setMessages([])
      setSelectedChat(null)
      Swal.fire({
        title: '✓ Logged Out',
        text: 'You have been logged out from WhatsApp Web',
        icon: 'success',
        timer: 2000
      })
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.message,
        icon: 'error'
      })
    }
  }

  const loadChats = async () => {
    try {
      const response = await axios.get('/api/whatsapp/chats?limit=15')
      if (response.data.success) {
        setChats(response.data.chats)
      }
    } catch (error) {
      console.error('Failed to load chats:', error)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!phoneNumber.trim() || !messageText.trim()) {
      Swal.fire({
        title: 'Missing Info',
        text: 'Please enter phone number and message',
        icon: 'warning'
      })
      return
    }

    try {
      setSendingMessage(true)
      const response = await axios.post('/api/whatsapp/send', {
        phone_number: phoneNumber,
        message: messageText
      })

      if (response.data.success) {
        Swal.fire({
          title: '✓ Sent!',
          text: `Message sent to ${phoneNumber}`,
          icon: 'success',
          timer: 2000
        })
        setPhoneNumber('')
        setMessageText('')
      } else {
        Swal.fire({
          title: 'Failed',
          text: response.data.error || 'Could not send message',
          icon: 'error'
        })
      }
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.response?.data?.error || error.message,
        icon: 'error'
      })
    } finally {
      setSendingMessage(false)
    }
  }

  const loadMessages = async (chatName) => {
    try {
      setLoadingMessages(true)
      const response = await axios.post('/api/whatsapp/messages', {
        chat_name: chatName,
        limit: 30
      })
      if (response.data.success) {
        setMessages(response.data.messages)
        setSelectedChat(chatName)
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleDirectMessageWithAI = async (e) => {
    e.preventDefault()
    
    if (!directMessage.trim()) {
      Swal.fire({
        title: 'Empty Message',
        text: 'Please enter a message',
        icon: 'warning'
      })
      return
    }

    try {
      setProcessingDirectMessage(true)
      
      // Send message to AI for processing
      const response = await axios.post('/api/whatsapp/handle-message', {
        message: directMessage,
        sender_name: directSenderName || 'User'
      })

      if (response.data.success) {
        // Add AI response to list
        const aiResponse = {
          userMessage: directMessage,
          senderName: directSenderName,
          aiResponse: response.data.response,
          timestamp: new Date().toLocaleTimeString(),
          ready_to_send: response.data.ready_to_send
        }
        
        setAiResponses([aiResponse, ...aiResponses])
        setDirectMessage('')
        
        // Show success notification
        Swal.fire({
          title: '✓ Response Generated',
          text: 'AI response is ready to send',
          icon: 'success',
          timer: 2500
        })
      } else {
        Swal.fire({
          title: 'Error',
          text: response.data.error || 'Failed to generate response',
          icon: 'error'
        })
      }
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.response?.data?.error || error.message,
        icon: 'error'
      })
    } finally {
      setProcessingDirectMessage(false)
    }
  }

  const handleSendAIResponse = async (aiResponse, index) => {
    if (!phoneNumber.trim()) {
      Swal.fire({
        title: 'Missing Number',
        text: 'Please enter the recipient phone number',
        icon: 'warning'
      })
      return
    }

    try {
      setSendingMessage(true)
      const response = await axios.post('/api/whatsapp/send-ai-response', {
        phone_number: phoneNumber,
        message: aiResponse.aiResponse
      })

      if (response.data.success) {
        // Remove from pending list
        const updatedResponses = aiResponses.filter((_, i) => i !== index)
        setAiResponses(updatedResponses)
        
        Swal.fire({
          title: '✓ Response Sent!',
          text: `AI response sent to ${phoneNumber}`,
          icon: 'success',
          timer: 2000
        })
      } else {
        Swal.fire({
          title: 'Failed',
          text: response.data.error || 'Could not send response',
          icon: 'error'
        })
      }
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.response?.data?.error || error.message,
        icon: 'error'
      })
    } finally {
      setSendingMessage(false)
    }
  }

  const handleSendAutoProcessedResponse = async (response, index) => {
    if (!phoneNumber.trim()) {
      Swal.fire({
        title: 'Missing Number',
        text: 'Please enter the recipient phone number',
        icon: 'warning'
      })
      return
    }

    try {
      setSendingMessage(true)
      const sendResponse = await axios.post('/api/whatsapp/send-ai-response', {
        phone_number: phoneNumber,
        message: response.ai_response
      })

      if (sendResponse.data.success) {
        // Remove from queue
        const updated = autoProcessedResponses.filter((_, i) => i !== index)
        setAutoProcessedResponses(updated)
        
        Swal.fire({
          title: '✓ Sent!',
          text: `Response sent to ${phoneNumber}`,
          icon: 'success',
          timer: 2000
        })
      } else {
        Swal.fire({
          title: 'Failed',
          text: sendResponse.data.error || 'Could not send response',
          icon: 'error'
        })
      }
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.response?.data?.error || error.message,
        icon: 'error'
      })
    } finally {
      setSendingMessage(false)
    }
  }

  const handleClearProcessedResponses = async () => {
    try {
      const result = await Swal.fire({
        title: 'Clear Queue?',
        text: `This will clear ${autoProcessedResponses.length} processed responses`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Clear',
        cancelButtonText: 'Cancel'
      })

      if (result.isConfirmed) {
        const response = await axios.delete('/api/whatsapp/processed-responses')
        if (response.data.success) {
          setAutoProcessedResponses([])
          Swal.fire({
            title: 'Cleared!',
            text: `Cleared ${response.data.cleared_count} responses`,
            icon: 'success',
            timer: 2000
          })
        }
      }
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.message,
        icon: 'error'
      })
    }
  }

  if (checkingStatus) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader className="animate-spin mx-auto mb-4" size={32} />
          <p>Checking WhatsApp status...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageCircle className="text-green-600" size={24} />
          <h2 className="text-2xl font-bold">WhatsApp Web</h2>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
            loggedIn ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {loggedIn ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowAuthorizedNumbers(!showAuthorizedNumbers)}
            className="btn-primary flex items-center gap-2"
            title="Manage authorized WhatsApp numbers"
          >
            <Lock size={16} />
            Authorized Numbers
          </button>
          {loggedIn && (
            <button
              onClick={handleLogout}
              className="btn-danger flex items-center gap-2"
            >
              <LogOut size={16} />
              Logout
            </button>
          )}
        </div>
      </div>

      {!loggedIn ? (
        // Login Section
        <div className="text-center p-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <MessageCircle className="mx-auto mb-4 text-gray-400" size={48} />
          <h3 className="text-xl font-semibold mb-2">Connect to WhatsApp</h3>
          <p className="text-gray-600 mb-6">
            Login with your personal WhatsApp account using QR code scanning.<br />
            Your browser will open and display a QR code to scan with your phone.
          </p>
          <button
            onClick={handleLogin}
            disabled={loading}
            className="btn-success flex items-center gap-2 mx-auto"
          >
            {loading ? <Loader className="animate-spin" size={18} /> : <LogIn size={18} />}
            {loading ? 'Logging In...' : 'Login with WhatsApp'}
          </button>
          <p className="text-sm text-gray-500 mt-4">
            💡 Note: A Chrome window will open. This is secure and only accesses WhatsApp Web.
          </p>
        </div>
      ) : (
        // Main Interface
        <div className="space-y-6">
          {/* Info Banner */}
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex gap-2">
              <CheckCircle2 className="text-green-600 flex-shrink-0" size={20} />
              <div className="text-sm text-green-900">
                <p className="font-semibold">✓ WhatsApp Web Connected</p>
                <p className="text-xs mt-1">💡 QR code was printed to terminal during login. Incoming messages are being automatically processed with AI.</p>
                {listenerActive && (
                  <p className="text-xs mt-1 text-green-700">
                    🎧 <strong>Message Listener Active</strong> - Messages you receive will be automatically processed
                  </p>
                )}
              </div>
            </div>
          </div>
          
          {/* Auto-Processed Messages (from message listener) */}
          {autoProcessedResponses.length > 0 && (
            <div className="bg-orange-50 p-6 rounded-lg border-2 border-orange-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2 text-orange-900">
                  <MessageSquare size={18} />
                  📨 Auto-Processed Messages ({autoProcessedResponses.length})
                </h3>
                <button
                  onClick={handleClearProcessedResponses}
                  className="px-3 py-1 text-xs bg-orange-200 hover:bg-orange-300 text-orange-900 rounded font-medium"
                >
                  Clear All
                </button>
              </div>
              
              <p className="text-sm text-orange-700 mb-4">
                ✅ Messages received on your WhatsApp number were automatically processed by AI
              </p>
              
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {autoProcessedResponses.map((response, idx) => (
                  <div key={idx} className="bg-white p-4 rounded-lg border border-orange-200">
                    <div className="mb-3">
                      <p className="text-xs text-gray-600 mb-1">
                        <strong>From:</strong> {response.from} · {new Date(response.timestamp).toLocaleTimeString()}
                      </p>
                      <div className="text-sm p-3 bg-orange-50 rounded text-gray-700 border-l-2 border-orange-400 italic">
                        💬 "{response.received_message}"
                      </div>
                    </div>
                    
                    <div className="mb-3">
                      <p className="text-xs font-semibold text-gray-700 mb-1">🤖 AI Response:</p>
                      <div className="text-sm p-3 bg-green-50 rounded text-green-900 border-l-2 border-green-400">
                        {response.ai_response}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleSendAutoProcessedResponse(response, idx)}
                      disabled={sendingMessage || !phoneNumber.trim()}
                      className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-sm font-medium rounded flex items-center justify-center gap-2 transition"
                    >
                      {sendingMessage ? (
                        <>
                          <Loader className="animate-spin" size={14} />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send size={14} />
                          Send to WhatsApp
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>
              
              <p className="text-xs text-orange-600 mt-4 p-3 bg-orange-100 rounded border border-orange-300">
                💡 <strong>Tip:</strong> Enter the recipient phone number in the "Send Message" section below, then click "Send to WhatsApp" on the response you want to send.
              </p>
            </div>
          )}
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Direct AI Message Handler */}
              <div className="bg-purple-50 p-6 rounded-lg border-2 border-purple-200">
                <button
                  onClick={() => setAiFormOpen(!aiFormOpen)}
                  className="w-full flex items-center justify-between mb-4 hover:opacity-80 transition"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-purple-900">
                    <MessageSquare size={18} />
                    Direct AI Message Handler
                  </h3>
                  <ChevronDown
                    size={20}
                    className={`text-purple-900 transition-transform ${aiFormOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                <p className="text-sm text-purple-700 mb-4">
                  Manually process WhatsApp messages with AI and generate smart responses
                </p>
                
                {aiFormOpen && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-purple-900">Sender Name</label>
                    <input
                      type="text"
                      value={directSenderName}
                      onChange={(e) => setDirectSenderName(e.target.value)}
                      placeholder="e.g., Customer Name"
                      className="w-full px-4 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2 text-purple-900">Message from WhatsApp</label>
                    <textarea
                      value={directMessage}
                      onChange={(e) => setDirectMessage(e.target.value)}
                      placeholder="Paste the message you received on WhatsApp..."
                      rows={4}
                      className="w-full px-4 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  
                  <button
                    onClick={handleDirectMessageWithAI}
                    disabled={processingDirectMessage || !loggedIn}
                    className="w-full px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition"
                  >
                    {processingDirectMessage ? (
                      <>
                        <Loader className="animate-spin" size={18} />
                        Generating Response...
                      </>
                    ) : (
                      <>
                        <Send size={18} />
                        Generate AI Response
                      </>
                    )}
                  </button>
                </div>
                )}
                
                {/* Pending AI Responses */}
                {aiResponses.length > 0 && (
                  <div className="mt-6 pt-6 border-t-2 border-purple-200">
                    <h4 className="font-semibold text-purple-900 mb-3">Generated Responses ({aiResponses.length})</h4>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {aiResponses.map((response, idx) => (
                        <div key={idx} className="bg-white p-4 rounded-lg border border-purple-200">
                          <div className="mb-3">
                            <p className="text-xs text-gray-500 mb-1">From: <strong>{response.senderName}</strong> · {response.timestamp}</p>
                            <p className="text-sm p-2 bg-purple-50 rounded text-purple-900 italic border-l-2 border-purple-300">
                              "{response.userMessage}"
                            </p>
                          </div>
                          
                          <div className="mb-3">
                            <p className="text-xs font-semibold text-gray-600 mb-1">AI Response:</p>
                            <p className="text-sm p-2 bg-green-50 rounded text-green-900">
                              {response.aiResponse}
                            </p>
                          </div>
                          
                          <button
                            onClick={() => handleSendAIResponse(response, idx)}
                            disabled={sendingMessage || !phoneNumber.trim()}
                            className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-sm font-medium rounded flex items-center justify-center gap-2 transition"
                          >
                            {sendingMessage ? (
                              <>
                                <Loader className="animate-spin" size={14} />
                                Sending...
                              </>
                            ) : (
                              <>
                                <Send size={14} />
                                Send to WhatsApp
                              </>
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Send Message Section */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <button
                  onClick={() => setSendFormOpen(!sendFormOpen)}
                  className="w-full flex items-center justify-between mb-4 hover:opacity-80 transition"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Send size={18} />
                    Send Message
                  </h3>
                  <ChevronDown
                    size={20}
                    className={`text-gray-700 transition-transform ${sendFormOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                
                {sendFormOpen && (
                <form onSubmit={handleSendMessage} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Phone Number</label>
                    <input
                      type="text"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      placeholder="+1234567890"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Include country code (e.g., +1234567890)</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Message</label>
                    <textarea
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      placeholder="Type your message here..."
                      rows={4}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                  
                  <button
                    type="submit"
                    disabled={sendingMessage || !loggedIn}
                    className="btn-success w-full flex items-center justify-center gap-2"
                  >
                    {sendingMessage ? (
                      <>
                        <Loader className="animate-spin" size={18} />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send size={18} />
                        Send Message
                      </>
                    )}
                  </button>
                </form>
                )}
              </div>

              {/* Recent Chats Messages */}
              {selectedChat && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-semibold mb-3 text-blue-900">Messages from {selectedChat}</h4>
                  {loadingMessages ? (
                    <div className="text-center py-4">
                      <Loader className="animate-spin mx-auto" size={24} />
                    </div>
                  ) : messages.length > 0 ? (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {messages.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded ${
                            msg.incoming ? 'bg-white border-l-4 border-blue-500' : 'bg-green-100 border-l-4 border-green-500 ml-auto'
                          } max-w-xs`}
                        >
                          <p className="text-sm">{msg.text}</p>
                          <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                            <Clock size={12} />
                            {new Date(parseInt(msg.time)).toLocaleTimeString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-600 text-sm">No messages yet</p>
                  )}
                </div>
              )}
            </div>

            {/* Auto-Processed Received Messages Section */}
            {(autoProcessedResponses.length > 0 || (listenerActive && autoProcessedResponses.length === 0)) && (
              <div className="bg-teal-50 p-6 rounded-lg border-2 border-teal-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-teal-900 flex items-center gap-2">
                    <MessageCircle size={18} className="text-teal-600" />
                    Received Messages
                    {autoProcessedResponses.length > 0 && (
                      <span className="ml-2 px-3 py-1 bg-teal-600 text-white text-xs font-bold rounded-full">
                        {autoProcessedResponses.length}
                      </span>
                    )}
                  </h3>
                  <button
                    onClick={async () => {
                      try {
                        const response = await axios.get('/api/whatsapp/processed-responses')
                        if (response.data.success) {
                          setAutoProcessedResponses(response.data.responses || [])
                        }
                      } catch (error) {
                        console.error('Error refreshing responses:', error)
                      }
                    }}
                    className="px-3 py-1 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition"
                    title="Refresh received messages"
                  >
                    🔄 Refresh
                  </button>
                </div>

                {/* Loading state when listener is active but no messages yet */}
                {autoProcessedResponses.length === 0 && listenerActive ? (
                  <div className="text-center py-8">
                    <Loader className="animate-spin mx-auto mb-3" size={28} />
                    <p className="text-sm text-teal-700">Waiting for incoming messages...</p>
                    <p className="text-xs text-teal-600 mt-2">Listener is active and monitoring WhatsApp</p>
                  </div>
                ) : autoProcessedResponses.length > 0 ? (
                  <div className="space-y-4 max-h-[600px] overflow-y-auto">
                    {autoProcessedResponses.map((response, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-lg border border-teal-200 shadow-sm hover:shadow-md transition">
                        {/* Header with contact name and timestamp */}
                        <div className="flex items-start justify-between mb-3 pb-3 border-b border-teal-100">
                          <div>
                            <p className="font-semibold text-teal-900 text-sm">{response.from}</p>
                            <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                              <Clock size={12} />
                              {new Date(response.timestamp).toLocaleString()}
                            </p>
                          </div>
                          {response.ready_to_send && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-green-100 rounded-full">
                              <CheckCircle2 size={12} className="text-green-600" />
                              <span className="text-xs font-semibold text-green-600">Ready</span>
                            </div>
                          )}
                        </div>

                        {/* Received Message */}
                        <div className="mb-3">
                          <p className="text-xs font-semibold text-gray-600 mb-2">📩 Received Message:</p>
                          <div className="bg-teal-50 p-3 rounded-lg border-l-4 border-teal-400">
                            <p className="text-sm text-gray-800">{response.received_message}</p>
                          </div>
                        </div>

                        {/* AI Response */}
                        <div className="mb-4">
                          <p className="text-xs font-semibold text-gray-600 mb-2">🤖 AI-Generated Response:</p>
                          <div className="bg-green-50 p-3 rounded-lg border-l-4 border-green-400">
                            <p className="text-sm text-gray-800">{response.ai_response}</p>
                          </div>
                        </div>

                        {/* Send Response Button */}
                        <button
                          onClick={async () => {
                            try {
                              setSendingMessage(true)
                              const sendResponse = await axios.post('/api/whatsapp/send-ai-response', {
                                phone_number: response.from,
                                message: response.ai_response
                              })
                              
                              if (sendResponse.data.success) {
                                Swal.fire({
                                  icon: 'success',
                                  title: 'Message Sent!',
                                  text: `Response sent to ${response.from}`,
                                  timer: 2000,
                                  timerProgressBar: true
                                })
                                
                                // Remove from list after sending
                                setAutoProcessedResponses(
                                  autoProcessedResponses.filter((_, i) => i !== idx)
                                )
                              } else {
                                Swal.fire({
                                  icon: 'error',
                                  title: 'Failed to Send',
                                  text: sendResponse.data.error || 'Could not send response'
                                })
                              }
                            } catch (error) {
                              Swal.fire({
                                icon: 'error',
                                title: 'Error',
                                text: error.response?.data?.error || 'Failed to send message'
                              })
                            } finally {
                              setSendingMessage(false)
                            }
                          }}
                          disabled={sendingMessage || !loggedIn}
                          className="w-full px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition"
                        >
                          {sendingMessage ? (
                            <>
                              <Loader className="animate-spin" size={14} />
                              Sending...
                            </>
                          ) : (
                            <>
                              <Send size={14} />
                              Send Response
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-teal-600">
                    <AlertCircle className="mx-auto mb-2" size={24} />
                    <p className="text-sm">No received messages yet</p>
                    <p className="text-xs mt-2">Messages will appear here as they arrive</p>
                  </div>
                )}
              </div>
            )}

            {/* Chats List */}
            <div className="bg-gray-50 p-6 rounded-lg h-fit">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <MessageSquare size={18} />
                Recent Chats
              </h3>
              
              {chats.length > 0 ? (
                <div className="space-y-2">
                  {chats.map((chat, idx) => (
                    <button
                      key={idx}
                      onClick={() => loadMessages(chat.name)}
                      className={`w-full text-left px-4 py-3 rounded-lg border-2 transition ${
                        selectedChat === chat.name
                          ? 'border-green-500 bg-green-50 text-green-900 font-semibold'
                          : 'border-gray-200 hover:border-green-300 hover:bg-green-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{chat.name}</span>
                        {loadingMessages && selectedChat === chat.name && (
                          <Loader className="animate-spin" size={16} />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-gray-500">
                  <AlertCircle className="mx-auto mb-2" size={24} />
                  <p className="text-sm">No chats found</p>
                  <p className="text-xs mt-2">Start a conversation on WhatsApp first</p>
                </div>
              )}
              
              <button
                onClick={loadChats}
                className="w-full mt-4 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 text-sm font-medium"
              >
                🔄 Refresh Chats
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Authorized WhatsApp Numbers Modal */}
      {showAuthorizedNumbers && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="text-lg font-semibold text-gray-900">Authorized WhatsApp Numbers</h2>
              <button
                onClick={() => setShowAuthorizedNumbers(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="px-6 py-4">
              <AuthorizedContactsPanel contactType="phone" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
