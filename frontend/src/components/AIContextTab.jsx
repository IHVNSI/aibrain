import React, { useEffect, useState } from 'react'
import api, { handleApiError } from '../api/client'
import { Save, Loader, CheckCircle2, XCircle, RefreshCw, Copy } from 'lucide-react'
import Swal from 'sweetalert2'

export default function AIContextTab() {
  const [context, setContext] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [activeTab, setActiveTab] = useState('system')
  const [editingField, setEditingField] = useState(null)

  useEffect(() => {
    loadContext()
  }, [])

  const loadContext = async () => {
    try {
      const { data } = await api.get('/api/settings/ai-context')
      if (data.success && data.context) {
        setContext(data.context)
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const handleChange = (field, value) => {
    setContext(c => ({ ...c, [field]: value }))
  }

  const save = async () => {
    if (!context || !context.system_instructions.trim()) {
      setMsg({ type: 'error', text: 'System instructions cannot be empty' })
      return
    }

    setSaving(true)
    setMsg(null)
    try {
      const { data } = await api.post('/api/settings/ai-context', context)
      if (data.success) {
        setContext(data.context)
        setMsg({ type: 'success', text: 'AI context saved successfully' })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const resetToDefault = async () => {
    const result = await Swal.fire({
      title: 'Reset to Default?',
      text: 'This will replace all AI context with the built-in default instructions. This action cannot be undone.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Reset',
      cancelButtonText: 'Cancel',
      confirmButtonColor: '#dc2626',
    })

    if (!result.isConfirmed) return

    setSaving(true)
    setMsg(null)
    try {
      const { data } = await api.post('/api/settings/ai-context/default')
      if (data.success) {
        setContext(data.context)
        setMsg({ type: 'success', text: 'AI context reset to default' })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    Swal.fire({
      title: 'Copied',
      text: 'Text copied to clipboard',
      icon: 'success',
      timer: 1500,
      showConfirmButton: false,
    })
  }

  if (!context) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Loader className="animate-spin text-gray-400" size={32} />
      </div>
    )
  }

  const sections = [
    { id: 'system', label: 'System Instructions', field: 'system_instructions', description: 'Main system prompt that guides AI behavior' },
    { id: 'rules', label: 'Response Rules', field: 'response_rules', description: 'Rules for response formatting and tone' },
    { id: 'business', label: 'Business Rules', field: 'business_rules', description: 'Business logic and constraints' },
    { id: 'isolation', label: 'Data Isolation', field: 'data_isolation_rules', description: 'Multi-tenant data filtering rules' },
    { id: 'vocab', label: 'Vocabulary', field: 'vocabulary', description: 'Terminology definitions' },
    { id: 'email', label: 'Email Response Rules', field: 'email_response_rules', description: 'Specific rules for email interactions and auto-replies' },
    { id: 'whatsapp', label: 'WhatsApp Response Rules', field: 'whatsapp_response_rules', description: 'Specific rules for WhatsApp messaging' },
    { id: 'parent_app', label: 'Parent App Description', field: 'parent_app_description', description: 'Describe the structure, nature, and routes of your application' },
  ]

  return (
    <div className="w-full space-y-4">
      {msg && (
        <div className={`flex items-center gap-2 p-3 rounded-lg text-sm mb-3 ${
          msg.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {msg.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          {msg.text}
        </div>
      )}

      <div className="card">
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-2">AI Context Management</h2>
          <p className="text-sm text-gray-600">
            Configure all system instructions and context that the AI will use. No more hidden context — manage everything here.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 border-b border-gray-200 mb-6 overflow-x-auto">
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveTab(section.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition ${
                activeTab === section.id
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {section.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="space-y-4">
          {sections.map(section => (
            activeTab === section.id && (
              <div key={section.id}>
                <div className="mb-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">{section.label}</h3>
                      <p className="text-xs text-gray-500 mt-1">{section.description}</p>
                    </div>
                    {context[section.field] && (
                      <button
                        onClick={() => copyToClipboard(context[section.field])}
                        className="text-gray-400 hover:text-gray-600"
                        title="Copy to clipboard"
                      >
                        <Copy size={16} />
                      </button>
                    )}
                  </div>

                  <textarea
                    value={context[section.field] || ''}
                    onChange={(e) => handleChange(section.field, e.target.value)}
                    className="w-full h-96 p-3 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
                    placeholder={`Enter ${section.label.toLowerCase()}...`}
                  />
                </div>

                {section.id === 'system' && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-900">
                      <strong>💡 Tip:</strong> This is the main system prompt that will be sent to the LLM. 
                      It defines the AI's role, behavior, response style, and all business rules.
                    </p>
                  </div>
                )}
              </div>
            )
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex gap-3 border-t border-gray-200 pt-6">
          <button
            onClick={save}
            disabled={saving}
            className="btn-primary flex items-center gap-2"
          >
            {saving ? <Loader size={16} className="animate-spin" /> : <Save size={16} />}
            Save Context
          </button>

          <button
            onClick={resetToDefault}
            disabled={saving}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Reset to Default
          </button>
        </div>

        {/* Info Section */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h4 className="font-semibold text-gray-900 mb-2">ℹ️ How This Works</h4>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>• <strong>System Instructions:</strong> Sent to the LLM as the system message for every request</li>
            <li>• <strong>Response Rules:</strong> Guidelines for formatting and style (optional)</li>
            <li>• <strong>Business Rules:</strong> Constraints and business logic (optional)</li>
            <li>• <strong>Data Isolation:</strong> Multi-tenant filtering rules (optional)</li>
            <li>• <strong>Vocabulary:</strong> Terminology definitions for consistent language (optional)</li>
            <li>• <strong>Email Response Rules:</strong> Specific instructions for email auto-replies and interactions (optional)</li>
            <li>• <strong>WhatsApp Response Rules:</strong> Specific instructions for WhatsApp messaging (optional)</li>
            <li>• <strong>Parent App Description:</strong> Describe your application's structure, nature, and routes so the AI understands the context (optional)</li>
            <li>• All changes are saved immediately and apply to all new AI responses</li>
            <li>• Previous conversations are not affected by context changes</li>
          </ul>
        </div>

        {/* Metadata */}
        {context.updated_at && (
          <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500">
            Last updated: {new Date(context.updated_at).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  )
}
