import React, { useState, useEffect } from 'react'
import api, { handleApiError } from '../api/client'
import { Trash2, Plus, Edit2, Check, X, Loader, AlertCircle, Settings } from 'lucide-react'

export default function AuthorizedContactsPanel({ contactType = 'email' }) {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [showAutoReplySettings, setShowAutoReplySettings] = useState(false)
  const [selectedContactForAutoReply, setSelectedContactForAutoReply] = useState(null)
  
  const [formData, setFormData] = useState({
    contact: '',
    description: '',
    permission_level: 'SELECT_ONLY',
    is_active: true,
    auto_reply_enabled: false,
    auto_reply_mode: 'draft',
    auto_reply_ai_instructions: ''
  })

  const contactTypeLabel = contactType === 'email' ? 'Email' : 'WhatsApp Number'
  const contactPlaceholder = contactType === 'email' ? 'user@example.com' : '+1234567890'

  const loadContacts = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const { data } = await api.get(`/api/security/authorized-contacts?contact_type=${contactType}`)
      if (data.success) {
        setContacts(data.contacts || [])
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadContacts()
  }, [contactType])

  const resetForm = () => {
    setFormData({
      contact: '',
      description: '',
      permission_level: 'SELECT_ONLY',
      is_active: true,
      auto_reply_enabled: false,
      auto_reply_mode: 'draft',
      auto_reply_ai_instructions: ''
    })
    setEditingId(null)
    setShowForm(false)
  }

  const handleAddContact = (e) => {
    e.preventDefault()
    if (!formData.contact.trim()) {
      setMessage({ type: 'error', text: `Please enter a ${contactTypeLabel.toLowerCase()}` })
      return
    }

    // Basic validation
    if (contactType === 'email') {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact)) {
        setMessage({ type: 'error', text: 'Please enter a valid email address' })
        return
      }
    } else if (contactType === 'phone') {
      if (!/^[+]?[\d\s-()]{10,}$/.test(formData.contact)) {
        setMessage({ type: 'error', text: 'Please enter a valid phone number' })
        return
      }
    }

    submitForm()
  }

  const submitForm = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const payload = {
        ...formData,
        contact_type: contactType
      }

      let response
      if (editingId) {
        response = await api.patch(`/api/security/authorized-contacts/${editingId}`, payload)
      } else {
        response = await api.post('/api/security/authorized-contacts', payload)
      }

      if (response.data.success) {
        setMessage({ 
          type: 'success', 
          text: editingId ? '✅ Contact updated' : '✅ Contact added' 
        })
        resetForm()
        await loadContacts()
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (contact) => {
    setFormData({
      contact: contact.contact,
      description: contact.description || '',
      permission_level: contact.permission_level,
      is_active: contact.is_active,
      auto_reply_enabled: contact.auto_reply_enabled || false,
      auto_reply_mode: contact.auto_reply_mode || 'draft',
      auto_reply_ai_instructions: contact.auto_reply_ai_instructions || ''
    })
    setEditingId(contact.id)
    setShowForm(true)
  }

  const handleDelete = async (id, contact) => {
    if (!window.confirm(`Delete authorized contact: ${contact}?`)) {
      return
    }

    setSaving(true)
    setMessage(null)
    try {
      const { data } = await api.delete(`/api/security/authorized-contacts/${id}`)
      if (data.success) {
        setMessage({ type: 'success', text: `✅ Contact deleted` })
        await loadContacts()
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const openAutoReplySettings = (contact) => {
    setSelectedContactForAutoReply(contact)
    setFormData({
      contact: contact.contact,
      description: contact.description || '',
      permission_level: contact.permission_level,
      is_active: contact.is_active,
      auto_reply_enabled: contact.auto_reply_enabled || false,
      auto_reply_mode: contact.auto_reply_mode || 'draft',
      auto_reply_ai_instructions: contact.auto_reply_ai_instructions || ''
    })
    setEditingId(contact.id)
    setShowAutoReplySettings(true)
  }

  const closeAutoReplySettings = () => {
    setShowAutoReplySettings(false)
    setSelectedContactForAutoReply(null)
    setEditingId(null)
  }

  const saveAutoReplySettings = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const payload = {
        auto_reply_enabled: formData.auto_reply_enabled,
        auto_reply_mode: formData.auto_reply_mode,
        auto_reply_ai_instructions: formData.auto_reply_ai_instructions
      }

      const response = await api.patch(
        `/api/security/authorized-contacts/${selectedContactForAutoReply.id}`,
        payload
      )

      if (response.data.success) {
        setMessage({ type: 'success', text: '✅ Auto-reply settings saved' })
        closeAutoReplySettings()
        await loadContacts()
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="animate-spin text-gray-400" size={24} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {message && (
        <div className={`flex items-start gap-3 p-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' :
          message.type === 'error' ? 'bg-red-50 text-red-700' :
          'bg-blue-50 text-blue-700'
        }`}>
          {message.type === 'error' && <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />}
          <div className="flex-1">{message.text}</div>
        </div>
      )}

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-sm text-blue-900 mb-2">Authorized {contactTypeLabel}s</h3>
        <p className="text-xs text-blue-800 mb-2">
          {contactType === 'email' 
            ? 'Only emails in this list can send messages that trigger database queries. Add email addresses to authorize them.'
            : 'Only WhatsApp numbers in this list can send messages that trigger database queries. Add numbers to authorize them.'}
        </p>
        <p className="text-xs text-blue-800">
          <strong>Auto-Reply:</strong> Configure individual auto-reply behavior for each authorized email - save as draft or send automatically.
        </p>
      </div>

      {/* Add new contact button */}
      {!showForm && !showAutoReplySettings && (
        <button 
          onClick={() => setShowForm(true)}
          className="btn-primary text-xs py-2 flex items-center gap-2">
          <Plus size={14} /> Add Authorized {contactTypeLabel}
        </button>
      )}

      {/* Auto-Reply Settings Modal */}
      {showAutoReplySettings && selectedContactForAutoReply && (
        <div className="border border-blue-300 rounded-lg p-4 bg-blue-50">
          <h4 className="font-medium text-sm mb-3 flex items-center gap-2">
            <Settings size={16} /> Auto-Reply Settings: {selectedContactForAutoReply.contact}
          </h4>
          
          <div className="space-y-3">
            {/* Enable Auto-Reply */}
            <div className="flex items-center gap-2 p-3 bg-white rounded-lg border border-gray-200">
              <input
                type="checkbox"
                id="auto_reply_enabled"
                checked={formData.auto_reply_enabled}
                onChange={(e) => setFormData({ ...formData, auto_reply_enabled: e.target.checked })}
                disabled={saving}
                className="rounded"
              />
              <label htmlFor="auto_reply_enabled" className="text-xs font-medium text-gray-700 flex-1">
                Enable Auto-Reply for this contact
              </label>
            </div>

            {/* Auto-Reply Mode */}
            {formData.auto_reply_enabled && (
              <div className="p-3 bg-white rounded-lg border border-gray-200 space-y-3">
                <label className="text-xs font-medium text-gray-700 block">
                  Auto-Reply Behavior
                </label>
                
                <div className="space-y-2">
                  <label className="flex items-start gap-2 p-2 border border-gray-200 rounded cursor-pointer hover:bg-blue-50">
                    <input
                      type="radio"
                      name="auto_reply_mode"
                      value="draft"
                      checked={formData.auto_reply_mode === 'draft'}
                      onChange={(e) => setFormData({ ...formData, auto_reply_mode: e.target.value })}
                      disabled={saving}
                      className="mt-0.5"
                    />
                    <div className="flex-1">
                      <div className="text-xs font-medium text-gray-900">📝 Generate Reply with AI and Save as Draft</div>
                      <div className="text-xs text-gray-600 mt-0.5">AI generates response which is saved as draft for manual review and approval before sending</div>
                    </div>
                  </label>

                  <label className="flex items-start gap-2 p-2 border border-gray-200 rounded cursor-pointer hover:bg-green-50">
                    <input
                      type="radio"
                      name="auto_reply_mode"
                      value="send"
                      checked={formData.auto_reply_mode === 'send'}
                      onChange={(e) => setFormData({ ...formData, auto_reply_mode: e.target.value })}
                      disabled={saving}
                      className="mt-0.5"
                    />
                    <div className="flex-1">
                      <div className="text-xs font-medium text-gray-900">📤 Generate Reply with AI and Send Automatically</div>
                      <div className="text-xs text-gray-600 mt-0.5">AI generates response and automatically sends to sender without human oversight</div>
                    </div>
                  </label>
                </div>
              </div>
            )}

            {/* Custom AI Instructions */}
            {formData.auto_reply_enabled && (
              <div className="p-3 bg-white rounded-lg border border-gray-200">
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  Custom AI Instructions (Optional)
                </label>
                <textarea
                  placeholder="e.g., Always be professional, mention product features, suggest upgrade options..."
                  value={formData.auto_reply_ai_instructions}
                  onChange={(e) => setFormData({ ...formData, auto_reply_ai_instructions: e.target.value })}
                  disabled={saving}
                  rows="3"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to use default instructions</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={saveAutoReplySettings}
                disabled={saving}
                className="btn-primary text-xs py-1.5 flex items-center gap-1">
                {saving ? <Loader size={12} className="animate-spin" /> : <Check size={12} />}
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
              <button
                onClick={closeAutoReplySettings}
                disabled={saving}
                className="btn-secondary text-xs py-1.5 flex items-center gap-1">
                <X size={12} /> Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit form */}
      {showForm && !showAutoReplySettings && (
        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
          <h4 className="font-medium text-sm mb-3">
            {editingId ? `Edit ${contactTypeLabel}` : `Add New ${contactTypeLabel}`}
          </h4>
          <form onSubmit={handleAddContact} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                {contactTypeLabel}
              </label>
              <input
                type="text"
                placeholder={contactPlaceholder}
                value={formData.contact}
                onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
                disabled={saving || editingId}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Description (optional)
              </label>
              <input
                type="text"
                placeholder="e.g., Manager Account, Client Support"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={saving}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Permission Level
              </label>
              <select
                value={formData.permission_level}
                onChange={(e) => setFormData({ ...formData, permission_level: e.target.value })}
                disabled={saving}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="SELECT_ONLY">SELECT ONLY (Read-only queries)</option>
                <option value="READ_WRITE">READ/WRITE (Data modification allowed)</option>
                <option value="ADMIN">ADMIN (Full access)</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                disabled={saving}
                className="rounded"
              />
              <label htmlFor="is_active" className="text-xs text-gray-700">
                Active
              </label>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="btn-primary text-xs py-1.5 flex items-center gap-1">
                {saving ? <Loader size={12} className="animate-spin" /> : <Check size={12} />}
                {saving ? 'Saving...' : (editingId ? 'Update' : 'Add')}
              </button>
              <button
                type="button"
                onClick={resetForm}
                disabled={saving}
                className="btn-secondary text-xs py-1.5 flex items-center gap-1">
                <X size={12} /> Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Contacts list */}
      {contacts.length === 0 ? (
        <div className="card text-center py-8">
          <AlertCircle size={32} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-500">No authorized {contactTypeLabel.toLowerCase()}s yet.</p>
          <p className="text-xs text-gray-400 mt-1">Add one to get started.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {contacts.map((contact) => (
            <div key={contact.id} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm truncate">{contact.contact}</span>
                    {!contact.is_active && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Inactive</span>
                    )}
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {contact.permission_level}
                    </span>
                    {contact.auto_reply_enabled && (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        contact.auto_reply_mode === 'send' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {contact.auto_reply_mode === 'send' ? '📤 Auto-Send' : '📝 Auto-Draft'}
                      </span>
                    )}
                  </div>
                  {contact.description && (
                    <p className="text-xs text-gray-600">{contact.description}</p>
                  )}
                  {contact.created_by && (
                    <p className="text-xs text-gray-500 mt-1">Added by {contact.created_by}</p>
                  )}
                </div>
                <div className="flex gap-1 ml-2">
                  <button
                    onClick={() => openAutoReplySettings(contact)}
                    disabled={saving}
                    className="p-1.5 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded transition"
                    title="Configure auto-reply">
                    <Settings size={14} />
                  </button>
                  <button
                    onClick={() => handleEdit(contact)}
                    disabled={saving}
                    className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition"
                    title="Edit">
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(contact.id, contact.contact)}
                    disabled={saving}
                    className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition"
                    title="Delete">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
