/**
 * WhatsApp Web Component - Login and send/receive messages via WhatsApp Web
 * No official API required - uses Selenium for browser automation
 */
import React, { useState, useEffect } from 'react'
import axios from 'axios'
import Swal from 'sweetalert2'
import {
  MessageCircle, LogIn, LogOut, Send, Loader, CheckCircle2,
  AlertCircle, MessageSquare, Clock
} from 'lucide-react'

export default function WhatsAppWebTab() {
  // State
  const [loggedIn, setLoggedIn] = useState(false)
  const [loading, setLoading] = useState(false)
  const [checkingStatus, setCheckingStatus] = useState(true)
  
  // Send message form
  const [phoneNumber, setPhoneNumber] = useState('')
  const [messageText, setMessageText] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  
  // Chat list and messages
  const [chats, setChats] = useState([])
  const [selectedChat, setSelectedChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingMessages, setLoadingMessages] = useState(false)

  // Check login status on mount
  useEffect(() => {
    checkLoginStatus()
  }, [])

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
      
      Swal.fire({
        title: 'Opening WhatsApp Web...',
        html: 'A browser window will open showing a QR code.<br/>Please scan it with your WhatsApp phone.',
        icon: 'info',
        didOpen: async () => {
          Swal.showLoading()
          try {
            const response = await axios.post('/api/whatsapp/login')
            if (response.data.success) {
              Swal.fire({
                title: '✓ Logged In!',
                text: 'You are now connected to WhatsApp Web',
                icon: 'success'
              })
              setLoggedIn(true)
              loadChats()
            } else {
              Swal.fire({
                title: 'Login Failed',
                text: response.data.message || 'Could not login to WhatsApp',
                icon: 'error'
              })
            }
          } catch (error) {
            Swal.fire({
              title: 'Error',
              text: error.response?.data?.error || 'Failed to login',
              icon: 'error'
            })
          }
        }
      })
    } catch (error) {
      Swal.fire({
        title: 'Error',
        text: error.message,
        icon: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      await axios.post('/api/whatsapp/logout')
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
        
        {loggedIn && (
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            <LogOut size={16} />
            Logout
          </button>
        )}
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
            className="flex items-center gap-2 mx-auto px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Send Message Section */}
          <div className="lg:col-span-2">
            <div className="bg-gray-50 p-6 rounded-lg mb-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Send size={18} />
                Send Message
              </h3>
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
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-semibold flex items-center justify-center gap-2"
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
      )}

      {loggedIn && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex gap-2">
            <CheckCircle2 className="text-blue-600 flex-shrink-0" size={20} />
            <div className="text-sm text-blue-900">
              <p className="font-semibold">✓ WhatsApp Web Connected</p>
              <p className="text-xs mt-1">You can now send messages and view chat history directly from Brainr.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
