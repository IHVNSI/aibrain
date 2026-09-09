import React, { useState, useEffect } from 'react'
import api, { handleApiError } from '../api/client'
import { CheckCircle2, XCircle, Loader, AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

export default function TableRoleAccessPanel() {
  const [tables, setTables] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [expandedTable, setExpandedTable] = useState(null)
  const [initialized, setInitialized] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const [tablesRes, rolesRes] = await Promise.all([
        api.get('/api/auth-config/table-role-access/tables'),
        api.get('/api/auth-config/table-role-access/roles'),
      ])
      
      if (tablesRes.data.success) {
        setTables(tablesRes.data.tables || [])
      }
      if (rolesRes.data.success) {
        setRoles(rolesRes.data.roles || [])
      }
      
      if ((tablesRes.data.tables || []).length === 0 && (rolesRes.data.roles || []).length > 0) {
        setMessage({ 
          type: 'info', 
          text: '⚠️ No table-role access configured yet. Click "Initialize All Tables" to enable access control. This will grant all roles access to all tables by default.' 
        })
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleInitialize = async () => {
    if (!window.confirm('Initialize table-role access? This will grant all roles access to all tables by default.')) {
      return
    }
    
    setSaving(true)
    setMessage(null)
    try {
      const { data } = await api.post('/api/auth-config/table-role-access/initialize', {})
      if (data.success) {
        setMessage({ 
          type: 'success', 
          text: `✅ Initialized ${data.tables_count} tables for ${data.roles_count} roles` 
        })
        setInitialized(true)
        await loadData()
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const handleToggleAccess = async (tableName, roleName, currentAccess) => {
    setSaving(true)
    setMessage(null)
    try {
      const { data } = await api.post('/api/auth-config/table-role-access/update', {
        table_name: tableName,
        role_name: roleName,
        has_access: !currentAccess
      })
      
      if (data.success) {
        await loadData()
        setMessage({ type: 'success', text: data.message })
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const handleCheckAll = async () => {
    if (!window.confirm('Enable all roles for all tables? This will grant all roles access to all tables.')) {
      return
    }
    
    setSaving(true)
    setMessage(null)
    try {
      let updatedCount = 0
      const failures = []
      
      // Iterate through all tables and roles, enabling access where it's currently disabled
      for (const table of tables) {
        for (const roleAccess of table.role_access) {
          if (!roleAccess.has_access) {
            try {
              await api.post('/api/auth-config/table-role-access/update', {
                table_name: table.table_name,
                role_name: roleAccess.role_name,
                has_access: true
              })
              updatedCount++
            } catch (err) {
              failures.push(`${table.table_name}/${roleAccess.role_name}`)
            }
          }
        }
      }
      
      // Reload data to show updates
      await loadData()
      
      if (failures.length === 0) {
        setMessage({ 
          type: 'success', 
          text: `✅ Enabled all roles for all tables (${updatedCount} records updated)` 
        })
      } else {
        setMessage({ 
          type: 'success', 
          text: `✅ Updated ${updatedCount} records. ${failures.length} failed: ${failures.join(', ')}` 
        })
      }
    } catch (e) {
      setMessage({ type: 'error', text: handleApiError(e).message })
    } finally {
      setSaving(false)
    }
  }

  const handleUncheckAll = async () => {
    if (!window.confirm('Disable all roles for all tables? This will revoke all access to all tables.')) {
      return
    }
    
    setSaving(true)
    setMessage(null)
    try {
      let updatedCount = 0
      const failures = []
      
      // Iterate through all tables and roles, disabling access where it's currently enabled
      for (const table of tables) {
        for (const roleAccess of table.role_access) {
          if (roleAccess.has_access) {
            try {
              await api.post('/api/auth-config/table-role-access/update', {
                table_name: table.table_name,
                role_name: roleAccess.role_name,
                has_access: false
              })
              updatedCount++
            } catch (err) {
              failures.push(`${table.table_name}/${roleAccess.role_name}`)
            }
          }
        }
      }
      
      // Reload data to show updates
      await loadData()
      
      if (failures.length === 0) {
        setMessage({ 
          type: 'success', 
          text: `✅ Disabled all roles for all tables (${updatedCount} records updated)` 
        })
      } else {
        setMessage({ 
          type: 'success', 
          text: `✅ Updated ${updatedCount} records. ${failures.length} failed: ${failures.join(', ')}` 
        })
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
          {message.type === 'success' ? <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" /> :
           message.type === 'error' ? <XCircle size={16} className="flex-shrink-0 mt-0.5" /> :
           <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />}
          <div className="flex-1">{message.text}</div>
        </div>
      )}

      {tables.length > 0 && (
        <div className="flex gap-2 mb-2">
          <button 
            onClick={handleCheckAll}
            disabled={saving}
            className="btn-primary text-xs py-1.5 flex items-center gap-1">
            <CheckCircle2 size={14} /> {saving ? 'Checking...' : 'Check All'}
          </button>
          <button 
            onClick={handleUncheckAll}
            disabled={saving}
            className="btn-secondary text-xs py-1.5 flex items-center gap-1">
            <XCircle size={14} /> {saving ? 'Unchecking...' : 'Uncheck All'}
          </button>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-sm text-blue-900 mb-2">Table-Level Access Control</h3>
        <p className="text-xs text-blue-800 mb-3">
          Control which roles have access to specific tables in your source database. 
          When initialized, <strong>all roles have access to all tables by default</strong>. 
          The admin can then uncheck specific roles to restrict access to certain tables.
        </p>
        {tables.length === 0 && roles.length > 0 && (
          <button 
            onClick={handleInitialize}
            disabled={saving || initialized}
            className="btn-primary text-xs py-1.5">
            {saving ? 'Initializing...' : 'Initialize All Tables'}
          </button>
        )}
      </div>

      {tables.length === 0 ? (
        <div className="card text-center py-8">
          <AlertCircle size={32} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-500">No tables configured yet.</p>
          <p className="text-xs text-gray-400 mt-1">Initialize table access control to get started.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tables.map((table) => (
            <div key={table.table_name} className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedTable(expandedTable === table.table_name ? null : table.table_name)}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition">
                <div className="flex items-center gap-2">
                  {expandedTable === table.table_name ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  <span className="font-medium text-sm">{table.table_name}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    {table.role_access.filter(r => r.has_access).length}/{table.role_access.length} roles
                  </span>
                </div>
              </button>

              {expandedTable === table.table_name && (
                <div className="bg-gray-50 border-t border-gray-200 p-4">
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-gray-600 mb-3">
                      Select which roles can access "{table.table_name}":
                    </p>
                    {table.role_access.map((access) => (
                      <label key={access.role_name} className="flex items-center gap-2 cursor-pointer hover:bg-white p-2 rounded transition">
                        <input
                          type="checkbox"
                          checked={access.has_access}
                          onChange={() => handleToggleAccess(table.table_name, access.role_name, access.has_access)}
                          disabled={saving}
                          className="rounded"
                        />
                        <span className="text-sm text-gray-700 flex-1">{access.role_name}</span>
                        {access.has_access && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">✓ Has access</span>
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tables.length > 0 && (
        <div className="flex gap-2 pt-2">
          <button 
            onClick={loadData}
            disabled={loading}
            className="btn-secondary text-xs flex items-center gap-1 py-1.5">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      )}
    </div>
  )
}
