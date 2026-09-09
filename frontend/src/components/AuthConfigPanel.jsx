import React, { useState, useEffect } from 'react'
import api from '../api/client'
import { Save, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, TestTube, Lock } from 'lucide-react'

export default function AuthConfigPanel() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState(null)
  const [sourceTables, setSourceTables] = useState([])
  const [tableColumns, setTableColumns] = useState({})
  const [expandedTable, setExpandedTable] = useState(null)
  
  // Form state
  const [formData, setFormData] = useState({
    users_table: '',
    username_field: '',
    password_field: '',
    is_active_field: '',
    is_active_value: '',
    password_hash_type: 'bcrypt',
    company_table: '',
    company_id_field: '',
    company_name_field: '',
    user_company_fk_field: '',
    user_companies_junction_table: '',
    user_companies_user_fk: '',
    user_companies_company_fk: '',
    roles_table: '',
    role_id_field: '',
    role_name_field: '',
    user_roles_junction_table: '',
    user_roles_user_fk: '',
    user_roles_role_fk: ''
  })
  
  // Security config
  const [securityConfig, setSecurityConfig] = useState({
    sql_banned_keywords: 'password,secret,api_key,token,DELETE,DROP,ALTER',
    require_password_in_results: false
  })

  // Password management state
  const [passwordChangeForm, setPasswordChangeForm] = useState({
    email: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [passwordChanging, setPasswordChanging] = useState(false)

  // Load configuration and tables on mount
  useEffect(() => {
    loadConfig()
    loadSourceTables()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await api.get('/api/auth-config/config')
      if (response.data.success && response.data.config) {
        const mergedConfig = {
          users_table: response.data.config.users_table || '',
          username_field: response.data.config.username_field || '',
          password_field: response.data.config.password_field || '',
          is_active_field: response.data.config.is_active_field || '',
          is_active_value: response.data.config.is_active_value || '',
          password_hash_type: response.data.config.password_hash_type || 'bcrypt',
          company_table: response.data.config.company_table || '',
          company_id_field: response.data.config.company_id_field || '',
          company_name_field: response.data.config.company_name_field || '',
          user_company_fk_field: response.data.config.user_company_fk_field || '',
          user_companies_junction_table: response.data.config.user_companies_junction_table || '',
          user_companies_user_fk: response.data.config.user_companies_user_fk || '',
          user_companies_company_fk: response.data.config.user_companies_company_fk || '',
          roles_table: response.data.config.roles_table || '',
          role_id_field: response.data.config.role_id_field || '',
          role_name_field: response.data.config.role_name_field || '',
          user_roles_junction_table: response.data.config.user_roles_junction_table || '',
          user_roles_user_fk: response.data.config.user_roles_user_fk || '',
          user_roles_role_fk: response.data.config.user_roles_role_fk || ''
        }
        setFormData(mergedConfig)
        console.log('✅ Authentication configuration loaded successfully', mergedConfig)
      } else {
        console.log('ℹ️  No existing authentication configuration found')
      }
    } catch (error) {
      console.error('❌ Error loading configuration:', error)
    }
  }

  const loadSourceTables = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/auth-config/source-tables')
      if (response.data.success) {
        setSourceTables(response.data.tables)
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load source tables: ' + error.message })
    } finally {
      setLoading(false)
    }
  }

  const getTableColumns = async (tableName) => {
    if (tableColumns[tableName]) {
      return tableColumns[tableName]
    }

    try {
      const response = await api.get(`/api/auth-config/source-columns/${tableName}`)
      if (response.data.success) {
        setTableColumns(prev => ({
          ...prev,
          [tableName]: response.data.columns
        }))
        return response.data.columns
      }
    } catch (error) {
      console.error('Error loading columns:', error)
    }
    return []
  }

  const handleFieldChange = async (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // Load columns when junction tables are selected
    if ((field === 'user_companies_junction_table' || field === 'user_roles_junction_table') && value) {
      await getTableColumns(value)
    }
  }

  const handleSecurityChange = (field, value) => {
    setSecurityConfig(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      const response = await api.post('/api/auth-config/config', formData)
      if (response.data.success) {
        setMessage({ type: 'success', text: 'Authentication configuration saved' })
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to save configuration'
      })
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSecurity = async () => {
    setSaving(true)
    try {
      const response = await api.post('/api/auth-config/security', securityConfig)
      if (response.data.success) {
        setMessage({ type: 'success', text: 'Security configuration saved' })
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to save security configuration'
      })
    } finally {
      setSaving(false)
    }
  }

  const handleVerifyConfig = async () => {
    setTesting(true)
    try {
      const response = await api.post('/api/auth-config/verify')
      if (response.data.success) {
        setMessage({
          type: 'success',
          text: `Configuration verified! Found ${response.data.test_result.row_count} users.`
        })
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Configuration verification failed'
      })
    } finally {
      setTesting(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    
    // Validation
    if (!passwordChangeForm.email.trim()) {
      setMessage({ type: 'error', text: 'Email is required' })
      return
    }
    
    if (!passwordChangeForm.newPassword) {
      setMessage({ type: 'error', text: 'New password is required' })
      return
    }
    
    if (passwordChangeForm.newPassword !== passwordChangeForm.confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match' })
      return
    }
    
    if (passwordChangeForm.newPassword.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters' })
      return
    }

    setPasswordChanging(true)
    try {
      const response = await api.post('/api/auth-config/change-user-password', {
        email: passwordChangeForm.email.trim(),
        newPassword: passwordChangeForm.newPassword
      })
      
      if (response.data.success) {
        setMessage({ 
          type: 'success', 
          text: `✅ Password changed successfully for user: ${passwordChangeForm.email}` 
        })
        // Reset form
        setPasswordChangeForm({ email: '', newPassword: '', confirmPassword: '' })
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to change password'
      })
    } finally {
      setPasswordChanging(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-2">
          <AlertCircle className="text-blue-600 flex-shrink-0" size={20} />
          <div>
            <h4 className="font-semibold text-blue-900">Authentication Configuration</h4>
            <p className="text-sm text-blue-800 mt-1">
              Configure how the application authenticates users directly from the SOURCE database.
            </p>
            <p className="text-sm text-blue-700 mt-2 font-medium">
              ✅ All data is fetched from the <span className="font-bold">SOURCE Database</span>
            </p>
          </div>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg flex gap-2 ${
          message.type === 'success'
            ? 'bg-green-50 border border-green-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle2 className="text-green-600 flex-shrink-0" size={20} />
          ) : (
            <AlertCircle className="text-red-600 flex-shrink-0" size={20} />
          )}
          <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
            {message.text}
          </p>
        </div>
      )}

      {/* Previously Saved Settings Display */}
      {(formData.users_table || formData.company_table || formData.roles_table) && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-2 items-start mb-3">
            <CheckCircle2 className="text-blue-600 flex-shrink-0 mt-1" size={20} />
            <h4 className="font-semibold text-blue-900">Previously Saved Settings</h4>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {formData.users_table && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Users Table:</span>
                <span className="text-blue-900 ml-2">{formData.users_table}</span>
              </div>
            )}
            {formData.username_field && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Username Field:</span>
                <span className="text-blue-900 ml-2">{formData.username_field}</span>
              </div>
            )}
            {formData.password_field && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Password Field:</span>
                <span className="text-blue-900 ml-2">{formData.password_field}</span>
              </div>
            )}
            {formData.password_hash_type && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Password Hash Type:</span>
                <span className="text-blue-900 ml-2">{formData.password_hash_type}</span>
              </div>
            )}
            {formData.company_table && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Company Table:</span>
                <span className="text-blue-900 ml-2">{formData.company_table}</span>
              </div>
            )}
            {formData.company_id_field && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Company ID Field:</span>
                <span className="text-blue-900 ml-2">{formData.company_id_field}</span>
              </div>
            )}
            {formData.roles_table && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Roles Table:</span>
                <span className="text-blue-900 ml-2">{formData.roles_table}</span>
              </div>
            )}
            {formData.role_id_field && (
              <div className="bg-white p-2 rounded border border-blue-100">
                <span className="text-blue-700 font-medium">Role ID Field:</span>
                <span className="text-blue-900 ml-2">{formData.role_id_field}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Users Table Configuration */}
      <div className="space-y-4 p-4 border border-gray-200 rounded-lg">
        <h3 className="font-bold text-gray-900">Users Table Configuration</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Users Table
            </label>
            <select
              value={formData.users_table}
              onChange={(e) => {
                handleFieldChange('users_table', e.target.value)
                getTableColumns(e.target.value)
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select table...</option>
              {sourceTables.map(table => (
                <option key={table.name} value={table.name}>
                  {table.name} ({table.row_count} rows)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Username Field
            </label>
            <select
              value={formData.username_field}
              onChange={(e) => handleFieldChange('username_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.users_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password Field
            </label>
            <select
              value={formData.password_field}
              onChange={(e) => handleFieldChange('password_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.users_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Active/Status Field
            </label>
            <div className="flex gap-2">
              <select
                value={formData.is_active_field}
                onChange={(e) => handleFieldChange('is_active_field', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select field (optional)...</option>
                {(tableColumns[formData.users_table] || []).map(col => (
                  <option key={col.name} value={col.name}>
                    {col.name}
                  </option>
                ))}
              </select>
              {formData.is_active_field && (
                <input
                  type="text"
                  placeholder="Active value (e.g., 1, true, active)"
                  value={formData.is_active_value}
                  onChange={(e) => handleFieldChange('is_active_value', e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Optional. If left empty, all users are considered active. If set, specify the field and its active value.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password Hash Type
            </label>
            <select
              value={formData.password_hash_type}
              onChange={(e) => handleFieldChange('password_hash_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="bcrypt">bcrypt</option>
              <option value="plaintext">Plaintext (NOT RECOMMENDED)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Company Configuration */}
      <div className="space-y-4 p-4 border border-gray-200 rounded-lg">
        <h3 className="font-bold text-gray-900">Company/Organization Configuration</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company Table
            </label>
            <select
              value={formData.company_table}
              onChange={(e) => {
                handleFieldChange('company_table', e.target.value)
                getTableColumns(e.target.value)
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select table (optional)...</option>
              {sourceTables.map(table => (
                <option key={table.name} value={table.name}>
                  {table.name} ({table.row_count} rows)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company ID Field
            </label>
            <select
              value={formData.company_id_field}
              onChange={(e) => handleFieldChange('company_id_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.company_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company Name Field
            </label>
            <select
              value={formData.company_name_field}
              onChange={(e) => handleFieldChange('company_name_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.company_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              User-Company FK in Users Table
            </label>
            <select
              value={formData.user_company_fk_field}
              onChange={(e) => handleFieldChange('user_company_fk_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.users_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          {formData.company_table && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  User-Company Junction Table
                </label>
                <select
                  value={formData.user_companies_junction_table}
                  onChange={(e) => handleFieldChange('user_companies_junction_table', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select table...</option>
                  {sourceTables.map(table => (
                    <option key={table.name} value={table.name}>
                      {table.name} ({table.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  User FK in Junction Table
                </label>
                <select
                  value={formData.user_companies_user_fk}
                  onChange={(e) => handleFieldChange('user_companies_user_fk', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select field...</option>
                  {(tableColumns[formData.user_companies_junction_table] || []).map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company FK in Junction Table
                </label>
                <select
                  value={formData.user_companies_company_fk}
                  onChange={(e) => handleFieldChange('user_companies_company_fk', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select field...</option>
                  {(tableColumns[formData.user_companies_junction_table] || []).map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Roles Configuration */}
      <div className="space-y-4 p-4 border border-gray-200 rounded-lg">
        <h3 className="font-bold text-gray-900">Roles Configuration</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Roles Table
            </label>
            <select
              value={formData.roles_table}
              onChange={(e) => {
                handleFieldChange('roles_table', e.target.value)
                getTableColumns(e.target.value)
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select table (optional)...</option>
              {sourceTables.map(table => (
                <option key={table.name} value={table.name}>
                  {table.name} ({table.row_count} rows)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Role ID Field
            </label>
            <select
              value={formData.role_id_field}
              onChange={(e) => handleFieldChange('role_id_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.roles_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Role Name Field
            </label>
            <select
              value={formData.role_name_field}
              onChange={(e) => handleFieldChange('role_name_field', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select field...</option>
              {(tableColumns[formData.roles_table] || []).map(col => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>

          {formData.roles_table && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  User-Role Junction Table
                </label>
                <select
                  value={formData.user_roles_junction_table}
                  onChange={(e) => handleFieldChange('user_roles_junction_table', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select table...</option>
                  {sourceTables.map(table => (
                    <option key={table.name} value={table.name}>
                      {table.name} ({table.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  User FK in Junction Table
                </label>
                <select
                  value={formData.user_roles_user_fk}
                  onChange={(e) => handleFieldChange('user_roles_user_fk', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select field...</option>
                  {(tableColumns[formData.user_roles_junction_table] || []).map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Role FK in Junction Table
                </label>
                <select
                  value={formData.user_roles_role_fk}
                  onChange={(e) => handleFieldChange('user_roles_role_fk', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select field...</option>
                  {(tableColumns[formData.user_roles_junction_table] || []).map(col => (
                    <option key={col.name} value={col.name}>
                      {col.name}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Password Management */}
      <div className="space-y-4 p-4 border border-purple-200 bg-purple-50 rounded-lg">
        <div className="flex gap-2 items-start">
          <Lock className="text-purple-600 flex-shrink-0 mt-1" size={20} />
          <div className="flex-1">
            <h3 className="font-bold text-purple-900">Change User Password</h3>
            <p className="text-sm text-purple-800 mt-1">
              Quickly reset a user's password directly in the source database
            </p>
          </div>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-3 mt-4">
          <div>
            <label className="block text-sm font-medium text-purple-900 mb-2">
              User Email
            </label>
            <input
              type="email"
              value={passwordChangeForm.email}
              onChange={(e) => setPasswordChangeForm({ ...passwordChangeForm, email: e.target.value })}
              placeholder="Enter user email"
              className="w-full px-3 py-2 border border-purple-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              disabled={passwordChanging}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-900 mb-2">
              New Password
            </label>
            <input
              type="password"
              value={passwordChangeForm.newPassword}
              onChange={(e) => setPasswordChangeForm({ ...passwordChangeForm, newPassword: e.target.value })}
              placeholder="Enter new password"
              className="w-full px-3 py-2 border border-purple-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              disabled={passwordChanging}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-900 mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              value={passwordChangeForm.confirmPassword}
              onChange={(e) => setPasswordChangeForm({ ...passwordChangeForm, confirmPassword: e.target.value })}
              placeholder="Confirm new password"
              className="w-full px-3 py-2 border border-purple-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              disabled={passwordChanging}
            />
          </div>

          <button
            type="submit"
            disabled={passwordChanging || saving || testing}
            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white font-medium py-2 px-4 rounded-md transition flex items-center justify-center gap-2"
          >
            <Lock size={18} />
            {passwordChanging ? 'Changing Password...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3">
        <button
          onClick={handleVerifyConfig}
          disabled={saving || testing}
          className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 font-medium rounded-md transition flex items-center gap-2"
        >
          <TestTube size={18} />
          Verify Configuration
        </button>
        <button
          onClick={handleSaveConfig}
          disabled={saving || testing}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-md transition flex items-center gap-2"
        >
          <Save size={18} />
          Save Configuration
        </button>
      </div>
    </div>
  )
}
