import React, { useState, useEffect } from 'react'
import api from '../api/client'
import Swal from 'sweetalert2'
import {
  MessageCircle, Plus, Edit2, Trash2, Loader, CheckCircle2, XCircle, AlertCircle, Save, X
} from 'lucide-react'

export default function SocialMediaTab() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [msg, setMsg] = useState(null)

  const [formData, setFormData] = useState({
    channel_type: 'whatsapp',
    account_id: '',
    account_name: '',
    api_key: '',
    owner_number: '',
    auto_response_enabled: false,
    treat_as_prompt: true,
    use_context: true,
    use_security_policies: true,
    ai_instructions: 'Be helpful, professional, and follow all company policies. Respect user privacy and security.'
  })

  const [showApiKey, setShowApiKey] = useState(false)

  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/social-media/accounts')
      if (data.success) {
        setAccounts(data.accounts || [])
      }
    } catch (error) {
      console.error('Error loading accounts:', error)
      setMsg({ type: 'error', text: 'Failed to load social media accounts' })
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      channel_type: 'whatsapp',
      account_id: '',
      account_name: '',
      api_key: '',
      owner_number: '',
      auto_response_enabled: false,
      treat_as_prompt: true,
      use_context: true,
      use_security_policies: true,
      ai_instructions: 'Be helpful, professional, and follow all company policies. Respect user privacy and security.'
    })
    setEditingId(null)
    setShowApiKey(false)
  }

  const handleEdit = (account) => {
    setFormData({
      ...account,
      api_key: '••••••••••••' // Don't show actual key in edit
    })
    setEditingId(account.id)
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!formData.channel_type.trim()) {
      Swal.fire('Error', 'Channel type is required', 'error')
      return
    }
    if (!formData.account_id.trim()) {
      Swal.fire('Error', 'Account ID (phone number) is required', 'error')
      return
    }
    if (!formData.api_key.trim() || formData.api_key.includes('•')) {
      Swal.fire('Error', 'Please enter the API key', 'error')
      return
    }
    if (!formData.owner_number.trim() && formData.channel_type === 'whatsapp') {
      Swal.fire('Error', 'Owner phone number is required for WhatsApp', 'error')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/api/social-media/accounts', formData)

      if (response.data.success) {
        Swal.fire('Success', response.data.message, 'success')
        loadAccounts()
        setShowForm(false)
        resetForm()
      } else {
        Swal.fire('Error', response.data.error || 'Failed to save account', 'error')
      }
    } catch (error) {
      Swal.fire('Error', error.response?.data?.error || error.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (accountId) => {
    const confirmed = await Swal.fire({
      title: 'Delete Account?',
      text: 'This will remove the social media account configuration. This action cannot be undone.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#dc2626',
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel'
    })

    if (!confirmed.isConfirmed) return

    try {
      const response = await api.delete(`/api/social-media/accounts/${accountId}`)
      if (response.data.success) {
        Swal.fire('Deleted', 'Account removed successfully', 'success')
        loadAccounts()
      } else {
        Swal.fire('Error', response.data.error || 'Failed to delete account', 'error')
      }
    } catch (error) {
      Swal.fire('Error', error.response?.data?.error || error.message, 'error')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <MessageCircle size={20} />
          Social Media Channels
        </h2>
        <button
          onClick={() => {
            resetForm()
            setShowForm(true)
          }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2 transition"
        >
          <Plus size={18} /> Add Channel
        </button>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {msg.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {msg.text}
        </div>
      )}

      {loading && accounts.length === 0 ? (
        <div className="flex justify-center py-8">
          <Loader size={32} className="animate-spin text-blue-600" />
        </div>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <MessageCircle size={48} className="text-gray-300 mx-auto mb-3" />
          <p className="text-gray-600 mb-4">No social media channels configured yet</p>
          <button
            onClick={() => {
              resetForm()
              setShowForm(true)
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
          >
            Configure Your First Channel
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {accounts.map(account => (
            <div key={account.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <MessageCircle size={20} className={account.enabled ? 'text-green-600' : 'text-gray-400'} />
                    <h3 className="font-semibold text-gray-900">
                      {account.channel_type.toUpperCase()}: {account.account_name || account.account_id}
                    </h3>
                    {account.enabled && (
                      <span className="inline-block bg-green-100 text-green-800 text-xs px-2 py-1 rounded font-medium">
                        Active
                      </span>
                    )}
                    {!account.enabled && (
                      <span className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded font-medium">
                        Disabled
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 mb-2">Account ID: {account.account_id}</p>
                  {account.owner_number && (
                    <p className="text-xs text-gray-600 mb-2">Owner Number: {account.owner_number}</p>
                  )}
                  
                  <div className="text-xs text-gray-700 space-y-1 mt-2">
                    <div className="flex items-center gap-2">
                      {account.treat_as_prompt ? (
                        <>
                          <CheckCircle2 size={14} className="text-green-600" />
                          <span>Treats messages as prompts</span>
                        </>
                      ) : (
                        <>
                          <XCircle size={14} className="text-gray-400" />
                          <span>Does not process as prompts</span>
                        </>
                      )}
                    </div>
                    {account.treat_as_prompt && (
                      <>
                        <div className="flex items-center gap-2 ml-4">
                          {account.use_context ? (
                            <>
                              <CheckCircle2 size={14} className="text-green-600" />
                              <span>Uses training context</span>
                            </>
                          ) : (
                            <>
                              <XCircle size={14} className="text-gray-400" />
                              <span>No training context</span>
                            </>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          {account.use_security_policies ? (
                            <>
                              <CheckCircle2 size={14} className="text-green-600" />
                              <span>Applies security policies</span>
                            </>
                          ) : (
                            <>
                              <XCircle size={14} className="text-gray-400" />
                              <span>Security policies disabled</span>
                            </>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {account.ai_instructions && (
                    <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200 text-xs text-gray-700">
                      <p className="font-semibold text-blue-900 mb-1">AI Instructions:</p>
                      <p>{account.ai_instructions}</p>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleEdit(account)}
                    className="p-2 hover:bg-gray-100 rounded transition"
                    title="Edit"
                  >
                    <Edit2 size={18} className="text-gray-600" />
                  </button>
                  <button
                    onClick={() => handleDelete(account.id)}
                    className="p-2 hover:bg-red-100 rounded transition"
                    title="Delete"
                  >
                    <Trash2 size={18} className="text-red-600" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingId ? 'Edit Social Media Account' : 'Add Social Media Account'}
              </h2>
              <button
                onClick={() => {
                  setShowForm(false)
                  resetForm()
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={24} />
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              {/* Channel Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Channel Type</label>
                <select
                  value={formData.channel_type}
                  onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                  disabled={!!editingId}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  <option value="whatsapp">WhatsApp</option>
                  <option value="telegram">Telegram</option>
                  <option value="signal">Signal</option>
                  <option value="messenger">Facebook Messenger</option>
                </select>
              </div>

              {/* Account ID / Phone Number */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {formData.channel_type === 'whatsapp' ? 'Account Phone Number' : 'Account ID / Username'}
                </label>
                <input
                  type="text"
                  value={formData.account_id}
                  onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
                  placeholder={formData.channel_type === 'whatsapp' ? '+1234567890' : 'username or ID'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {formData.channel_type === 'whatsapp' 
                    ? 'The phone number of the WhatsApp Business Account'
                    : 'The account username or ID where messages will be received'}
                </p>
              </div>

              {/* Account Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input
                  type="text"
                  value={formData.account_name}
                  onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                  placeholder="e.g., Support Line, Sales Team"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Owner Number (WhatsApp specific) */}
              {formData.channel_type === 'whatsapp' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Owner Phone Number <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.owner_number}
                    onChange={(e) => setFormData({ ...formData, owner_number: e.target.value })}
                    placeholder="+9876543210"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Only messages from this number will be treated as prompts and receive AI responses
                  </p>
                </div>
              )}

              {/* API Key */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key / Auth Token</label>
                <div className="flex gap-2">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={formData.api_key}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    placeholder="Your API key from the provider"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="px-3 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg transition"
                  >
                    {showApiKey ? 'Hide' : 'Show'}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Get this from your {formData.channel_type} Business Account settings
                </p>
              </div>

              {/* AI Instructions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">AI Instructions (Optional)</label>
                <textarea
                  value={formData.ai_instructions}
                  onChange={(e) => setFormData({ ...formData, ai_instructions: e.target.value })}
                  rows={3}
                  placeholder="Custom instructions for AI responses..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                />
              </div>

              {/* Options */}
              <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
                <p className="font-semibold text-sm text-gray-900">Response Settings</p>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.treat_as_prompt}
                    onChange={(e) => setFormData({ ...formData, treat_as_prompt: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">
                    Treat incoming messages as prompts (AI will respond)
                  </span>
                </label>

                {formData.treat_as_prompt && (
                  <>
                    <label className="flex items-center gap-3 cursor-pointer ml-6">
                      <input
                        type="checkbox"
                        checked={formData.use_context}
                        onChange={(e) => setFormData({ ...formData, use_context: e.target.checked })}
                        className="w-4 h-4 rounded border-gray-300"
                      />
                      <span className="text-sm text-gray-700">
                        Use training data context in responses
                      </span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer ml-6">
                      <input
                        type="checkbox"
                        checked={formData.use_security_policies}
                        onChange={(e) => setFormData({ ...formData, use_security_policies: e.target.checked })}
                        className="w-4 h-4 rounded border-gray-300"
                      />
                      <span className="text-sm text-gray-700">
                        Apply security policies and guidelines
                      </span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer ml-6">
                      <input
                        type="checkbox"
                        checked={formData.auto_response_enabled}
                        onChange={(e) => setFormData({ ...formData, auto_response_enabled: e.target.checked })}
                        className="w-4 h-4 rounded border-gray-300"
                      />
                      <span className="text-sm text-gray-700">
                        Enable auto-response mode (responds immediately)
                      </span>
                    </label>
                  </>
                )}
              </div>
            </div>

            <div className="border-t border-gray-200 px-6 py-4 flex gap-2 justify-end sticky bottom-0 bg-white">
              <button
                onClick={() => {
                  setShowForm(false)
                  resetForm()
                }}
                className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {loading ? <Loader size={16} className="animate-spin" /> : <Save size={16} />}
                {editingId ? 'Update Account' : 'Create Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
