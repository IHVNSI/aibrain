import React, { useEffect, useMemo, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { handleApiError } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { copyToClipboard } from '../utils/formatters'
import AIContextTab from '../components/AIContextTab'
import AuthConfigPanel from '../components/AuthConfigPanel'
import TableRoleAccessPanel from '../components/TableRoleAccessPanel'
import EmailTab from './EmailTab'
import SchedulerTab from './SchedulerTab'
import AudioConfigPanel from '../components/AudioConfigPanel'
import SocialMediaTab from '../components/SocialMediaTab'
import WhatsAppWebTab from '../components/WhatsAppWebTab'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Swal from 'sweetalert2'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import {
  Cpu, Database, Layers, GraduationCap, MessagesSquare, Gauge,
  Save, Loader, CheckCircle2, XCircle, Play, Trash2, RefreshCw, Upload, Pencil, X, Shield, Volume2, FileText, Download, Eye, Search, Copy, Terminal, Zap, Mic, Square, Mail, Clock, MessageCircle
} from 'lucide-react'

const BASE_TABS = [
  { id: 'llm', label: 'LLM Config', icon: Cpu },
  { id: 'database', label: 'DB Config', icon: Database },
  { id: 'sqlite', label: 'SQLite DBMS', icon: Database },
  { id: 'vector', label: 'Vector DB', icon: Layers },
  { id: 'training', label: 'Training / RAG', icon: GraduationCap },
  { id: 'exchange', label: 'Data Exchange', icon: Upload },
  { id: 'auth-config', label: 'Authentication', icon: Shield },
  { id: 'table-access', label: 'Access', icon: Shield },
  // Token Tester tab only shown to admins
  { id: 'token-tester', label: 'Token Tester', icon: Shield, adminOnly: true },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'audio', label: 'Audio', icon: Volume2 },
  { id: 'ai-context', label: 'AI Context', icon: Zap },
  { id: 'audit', label: 'Audit Logs', icon: FileText },
  { id: 'cache', label: 'Caching / Metrics', icon: Gauge },
  { id: 'api-doc', label: 'DOCS', icon: FileText },
  { id: 'email', label: 'Email', icon: Mail, adminOnly: true },
  { id: 'social-media', label: 'Social Media (API)', icon: MessageCircle, adminOnly: true },
  { id: 'whatsapp-web', label: 'WhatsApp (Web)', icon: MessageCircle, adminOnly: true },
  { id: 'scheduler', label: 'Scheduler', icon: Clock, adminOnly: true },
  { id: 'server-logs', label: 'Server Logs', icon: Terminal, adminOnly: true },
]

async function confirmDeleteAction(text) {
  const result = await Swal.fire({
    title: 'Confirm delete',
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    confirmButtonColor: '#dc2626',
  })
  return result.isConfirmed
}

export default function Settings() {
  const [tab, setTab] = useState('llm')
  const [engine, setEngine] = useState(null)
  const { isAdmin, isCentralAdmin } = useAuth()
  const navigate = useNavigate()

  // Restrict access to admin users (isAdmin or isCentralAdmin)
  const hasAdminAccess = isAdmin || isCentralAdmin
  useEffect(() => {
    if (!hasAdminAccess) {
      navigate('/chat')
    }
  }, [hasAdminAccess, navigate])

  if (!hasAdminAccess) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <p className="text-gray-500">Access denied. Only admin users can access Settings.</p>
      </div>
    )
  }

  // Filter tabs based on user permissions
  const TABS = useMemo(() => {
    return BASE_TABS.filter(t => !t.adminOnly || isAdmin)
  }, [isAdmin])

  const refreshEngine = async () => {
    try {
      const { data } = await api.get('/api/settings/engine/status')
      setEngine(data.status)
    } catch (e) { /* ignore */ }
  }
  useEffect(() => { refreshEngine() }, [])

  return (
    <div className="w-full p-[10px]">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Settings</h1>
        <EngineBadge engine={engine} onRefresh={refreshEngine} />
      </div>

      <div className="flex gap-2 border-b border-gray-200 mb-5 overflow-x-auto px-[10px] py-[6px] -mx-[10px]">
        {TABS.map((t) => {
          const Icon = t.icon
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex items-center gap-1 px-4 py-2.5 text-sm border-b-2 whitespace-nowrap ${
                tab === t.id ? 'border-brand-600 text-brand-700 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'}`}>
              <Icon size={16} /> {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'llm' && <LLMTab onChanged={refreshEngine} />}
      {tab === 'database' && <DatabaseConfigTab onChanged={refreshEngine} />}
      {tab === 'sqlite' && <SQLiteTab />}
      {tab === 'vector' && <VectorTab onChanged={refreshEngine} />}
      {tab === 'training' && <TrainingTab />}
      {tab === 'exchange' && <DataExchangeTab />}
      {tab === 'api-doc' && <ApiDocTab />}
      {tab === 'auth-config' && <AuthConfigPanel />}
      {tab === 'table-access' && <TableRoleAccessPanel />}
      {tab === 'token-tester' && <TokenTesterTab />}
      {tab === 'security' && <SecurityTab />}
      {tab === 'audio' && <AudioConfigPanel />}
      {tab === 'ai-context' && <AIContextTab />}
      {tab === 'audit' && <AuditLogsTab />}
      {tab === 'cache' && <CacheTab />}
      {tab === 'email' && <EmailTab />}
      {tab === 'social-media' && <SocialMediaTab />}
      {tab === 'whatsapp-web' && <WhatsAppWebTab />}
      {tab === 'scheduler' && <SchedulerTab />}
      {tab === 'server-logs' && <ServerLogsTab />}
    </div>
  )
}

function EngineBadge({ engine, onRefresh }) {
  const ready = engine?.ready
  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
        ready ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
        {ready ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
        Engine {ready ? 'ready' : 'not ready'}
        {engine?.llm_provider ? ` · ${engine.llm_provider}` : ''}
        {engine?.vector_store ? ` · ${engine.vector_store}` : ''}
      </span>
      <button onClick={onRefresh} className="text-gray-400 hover:text-gray-700"><RefreshCw size={14} /></button>
    </div>
  )
}

function Banner({ msg }) {
  if (!msg) return null
  return (
    <div className={`flex items-center gap-2 p-3 rounded-lg text-sm mb-3 ${
      msg.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
      {msg.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}{msg.text}
    </div>
  )
}

/* ----------------------------- LLM ----------------------------- */
function LLMTab({ onChanged }) {
  const [cfg, setCfg] = useState(null)
  const [providers, setProviders] = useState([])
  const [msg, setMsg] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/api/settings/llm').then(({ data }) => setCfg(data.config))
    api.get('/api/settings/llm/providers').then(({ data }) => setProviders(data.providers || []))
  }, [])

  if (!cfg) return <Loader className="animate-spin text-gray-400" />

  const models = providers.find((p) => p.id === cfg.provider)?.models || []
  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }))

  const save = async () => {
    setSaving(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/llm', cfg)
      setCfg(data.config)
      setMsg({ type: 'success', text: 'LLM settings saved.' })
      onChanged?.()
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
    finally { setSaving(false) }
  }

  return (
    <div className="card w-full space-y-4">
      <Banner msg={msg} />
      <div>
        <label className="text-sm text-gray-600">Provider</label>
        <select className="input mt-1" value={cfg.provider} onChange={(e) => set('provider', e.target.value)}>
          {providers.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>
      <div>
        <label className="text-sm text-gray-600">Model</label>
        <input className="input mt-1" list="models" value={cfg.model || ''} onChange={(e) => set('model', e.target.value)} />
        <datalist id="models">{models.map((m) => <option key={m} value={m} />)}</datalist>
      </div>

      {cfg.provider === 'gemini' && (
        <KeyField label="Gemini API Key" set={cfg.gemini_api_key_set} onChange={(v) => set('gemini_api_key', v)} />
      )}
      {cfg.provider === 'openai' && (
        <KeyField label="OpenAI API Key" set={cfg.openai_api_key_set} onChange={(v) => set('openai_api_key', v)} />
      )}
      {cfg.provider === 'anthropic' && (
        <KeyField label="Anthropic API Key" set={cfg.anthropic_api_key_set} onChange={(v) => set('anthropic_api_key', v)} />
      )}
      {cfg.provider === 'huggingface' && (
        <div>
          <label className="text-sm text-gray-600">Hugging Face model (offline)</label>
          <input className="input mt-1" value={cfg.hf_model || ''} onChange={(e) => set('hf_model', e.target.value)} />
          <p className="text-xs text-gray-400 mt-1">Runs locally via transformers. First use downloads the model to cache.</p>
        </div>
      )}
      <div>
        <label className="text-sm text-gray-600">Temperature</label>
        <input type="number" min="0" max="1" step="0.1" className="input mt-1 w-32"
          value={cfg.temperature ?? 0} onChange={(e) => set('temperature', parseFloat(e.target.value))} />
      </div>
      <button onClick={save} disabled={saving} className="btn-primary flex items-center gap-1">
        {saving ? <Loader size={16} className="animate-spin" /> : <Save size={16} />} Save
      </button>
    </div>
  )
}

function KeyField({ label, set, onChange }) {
  const [val, setVal] = useState('')
  return (
    <div>
      <label className="text-sm text-gray-600">{label} {set && <span className="text-green-600 text-xs">(configured)</span>}</label>
      <input type="password" className="input mt-1" placeholder={set ? '•••••••• (leave blank to keep)' : 'Enter key'}
        value={val} onChange={(e) => { setVal(e.target.value); onChange(e.target.value) }} />
    </div>
  )
}

/* --------------------------- Database Config (Combined Source + Admin) ----------- */
function DatabaseConfigTab({ onChanged }) {
  const [sourceCollapsed, setSourceCollapsed] = useState(true)
  const [adminCollapsed, setAdminCollapsed] = useState(true)
  return (
    <div className="space-y-4">
      {/* Source Database Section */}
      <div className="card">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setSourceCollapsed(!sourceCollapsed)}>
          <h3 className="font-medium text-sm">Source Database Configuration</h3>
          <span className="text-gray-400">{sourceCollapsed ? '▶' : '▼'}</span>
        </div>
        {!sourceCollapsed && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <DatabaseTab onChanged={onChanged} />
          </div>
        )}
      </div>

      {/* Admin Database Section */}
      <div className="card">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setAdminCollapsed(!adminCollapsed)}>
          <h3 className="font-medium text-sm">Admin Database Config</h3>
          <span className="text-gray-400">{adminCollapsed ? '▶' : '▼'}</span>
        </div>
        {!adminCollapsed && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <AdminDatabaseTab onChanged={onChanged} />
          </div>
        )}
      </div>
    </div>
  )
}

/* --------------------------- Database --------------------------- */
function DatabaseTab({ onChanged }) {
  const [cfg, setCfg] = useState(null)
  const [sourceDbInfo, setSourceDbInfo] = useState(null)
  const [mode, setMode] = useState('url') // 'url' or 'form'
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    dbType: 'postgresql',
    host: 'localhost',
    port: 5432,
    username: '',
    password: '',
    database: '',
    options: ''
  })

  const DB_TYPES = {
    postgresql: { driver: 'psycopg2', port: 5432, example: 'postgresql+psycopg2://user:pass@host:5432/db' },
    mysql: { driver: 'pymysql', port: 3306, example: 'mysql+pymysql://user:pass@host:3306/db' },
    sqlite: { driver: null, port: null, example: 'sqlite:///path/to/database.db' },
    mongodb: { driver: null, port: 27017, example: 'mongodb://user:pass@host:27017/db' },
    mssql: { driver: 'pyodbc', port: 1433, example: 'mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server' },
  }

  useEffect(() => {
    api.get('/api/settings/database').then(({ data }) => {
      setCfg(data.config)
      if (data.config?.source_db_url) parseUrl(data.config.source_db_url)
    })
    loadSourceDbInfo()
  }, [])

  const loadSourceDbInfo = async () => {
    try {
      const { data } = await api.get('/api/settings/database/info')
      setSourceDbInfo(data.source_db)
    } catch (e) {
      console.error('Error loading source DB info:', e)
    }
  }

  const parseUrl = (url) => {
    if (!url) return
    try {
      const match = url.match(/^(\w+)\+?(\w+)?:\/\/(.*)/)
      if (!match) return
      const [, dbType, driver, rest] = match
      const f = { ...form, dbType }
      if (dbType === 'sqlite') {
        f.database = rest.replace('///', '')
      } else if (dbType === 'mongodb') {
        const m = rest.match(/^(?:([^:]+)(?::([^@]*))?@)?([^:/?]+)(?::(\d+))?(?:\/([^?]*))?/)
        if (m) {
          f.username = m[1] || ''
          f.password = m[2] || ''
          f.host = m[3] || 'localhost'
          f.port = m[4] || 27017
          f.database = m[5] || ''
        }
      } else {
        const m = rest.match(/^(?:([^:]+)(?::([^@]*))?@)?([^:/?]+)(?::(\d+))?(?:\/([^?]*))?(?:\?(.*))?/)
        if (m) {
          f.username = m[1] || ''
          f.password = m[2] || ''
          f.host = m[3] || 'localhost'
          f.port = parseInt(m[4]) || DB_TYPES[dbType]?.port || 5432
          f.database = m[5] || ''
          f.options = m[6] || ''
        }
      }
      setForm(f)
    } catch (e) { console.error('Parse error:', e) }
  }

  const buildUrl = () => {
    const { dbType, host, port, username, password, database, options } = form
    if (dbType === 'sqlite') {
      return `sqlite:///${database}`
    } else if (dbType === 'mongodb') {
      const auth = username ? `${username}${password ? ':' + password : ''}@` : ''
      const p = port ? `:${port}` : ''
      return `mongodb://${auth}${host}${p}${database ? '/' + database : ''}`
    } else {
      const driver = DB_TYPES[dbType]?.driver || 'psycopg2'
      const auth = username ? `${username}${password ? ':' + password : ''}@` : ''
      const p = port ? `:${port}` : ''
      const opt = options ? `?${options}` : ''
      return `${dbType}+${driver}://${auth}${host}${p}${database ? '/' + database : ''}${opt}`
    }
  }

  const handleModeSwitch = (newMode) => {
    if (newMode === 'form') {
      if (cfg?.source_db_url) parseUrl(cfg.source_db_url)
    } else {
      setCfg({ source_db_url: buildUrl() })
    }
    setMode(newMode)
  }

  const handleFormChange = (key, value) => {
    const newForm = { ...form, [key]: value }
    setForm(newForm)
    if (mode === 'form') {
      setCfg({ source_db_url: buildUrl() })
    }
  }

  if (!cfg) return <Loader className="animate-spin text-gray-400" />

  const test = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/database/test', cfg)
      setMsg({ type: data.success ? 'success' : 'error', text: data.message || data.error })
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
    finally { setBusy(false) }
  }
  const save = async () => {
    setBusy(true); setMsg(null)
    try {
      await api.post('/api/settings/database', cfg)
      setMsg({ type: 'success', text: 'Database settings saved.' })
      onChanged?.()
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="card w-full space-y-5">
      <Banner msg={msg} />

      {/* Current Source DB Info */}
      {sourceDbInfo && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Database size={18} /> Current Source Database
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-600">Type:</span>
              <p className="font-mono font-semibold text-gray-900">{sourceDbInfo.type || 'unknown'}</p>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>
              <p className={`font-semibold ${sourceDbInfo.accessible ? 'text-green-700' : 'text-red-700'}`}>
                {sourceDbInfo.accessible ? 'Accessible' : 'Not Accessible'}
              </p>
            </div>
            {sourceDbInfo.table_count !== undefined && (
              <div>
                <span className="text-gray-600">Tables:</span>
                <p className="font-mono font-semibold text-gray-900">{sourceDbInfo.table_count}</p>
              </div>
            )}
            {sourceDbInfo.size_bytes !== undefined && (
              <div>
                <span className="text-gray-600">Size:</span>
                <p className="font-mono font-semibold text-gray-900">{(sourceDbInfo.size_bytes / 1024).toFixed(2)} KB</p>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Mode Toggle */}
      <div className="flex gap-3 border-b pb-4">
        <button onClick={() => handleModeSwitch('url')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            mode === 'url' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'}`}>
          Connection String
        </button>
        <button onClick={() => handleModeSwitch('form')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            mode === 'form' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'}`}>
          Form Builder
        </button>
      </div>

      {/* Connection String Mode */}
      {mode === 'url' && (
        <div className="space-y-3">
          <div>
            <label className="text-sm text-gray-600">Source database URL (SQLAlchemy)</label>
            <input className="input mt-1" placeholder="postgresql+psycopg2://user:pass@host:5432/db"
              value={cfg.source_db_url || ''} onChange={(e) => setCfg({ source_db_url: e.target.value })} />
            <p className="text-xs text-gray-400 mt-1">Generated SQL runs against this database.</p>
          </div>
        </div>
      )}

      {/* Form Mode */}
      {mode === 'form' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Database Type</label>
            <select className="input" value={form.dbType}
              onChange={(e) => handleFormChange('dbType', e.target.value)}>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
              <option value="mongodb">MongoDB</option>
              <option value="mssql">SQL Server</option>
            </select>
          </div>

          {form.dbType !== 'sqlite' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Host / Server</label>
                  <input className="input" value={form.host} onChange={(e) => handleFormChange('host', e.target.value)} placeholder="localhost" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Port</label>
                  <input className="input" type="number" value={form.port} onChange={(e) => handleFormChange('port', e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Username</label>
                  <input className="input" value={form.username} onChange={(e) => handleFormChange('username', e.target.value)} placeholder="user" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Password</label>
                  <input className="input" type="password" value={form.password} onChange={(e) => handleFormChange('password', e.target.value)} placeholder="••••••" />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm text-gray-600 mb-1">Database Name</label>
            <input className="input" value={form.database} onChange={(e) => handleFormChange('database', e.target.value)}
              placeholder={form.dbType === 'sqlite' ? '/path/to/database.db' : 'database_name'} />
          </div>

          {form.dbType !== 'sqlite' && form.dbType !== 'mongodb' && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">Connection Options (optional)</label>
              <input className="input" value={form.options} onChange={(e) => handleFormChange('options', e.target.value)}
                placeholder="key=value&key2=value2" />
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded p-3">
            <p className="text-xs font-mono text-blue-900 break-all">{cfg.source_db_url}</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={test} disabled={busy} className="btn-secondary flex items-center gap-1"><Play size={16} /> Test</button>
        <button onClick={save} disabled={busy} className="btn-primary flex items-center gap-1">
          {busy ? <Loader size={16} className="animate-spin" /> : <Save size={16} />} Save
        </button>
      </div>
    </div>
  )
}

/* ---------------------- Admin Database Migration ---------------------- */
function AdminDatabaseTab({ onChanged }) {
  const [adminDbInfo, setAdminDbInfo] = useState(null)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState('info') // 'info' or 'migrate'
  const [form, setForm] = useState({
    dbType: 'postgresql',
    host: 'localhost',
    port: 5432,
    username: '',
    password: '',
    database: 'assistantai_admin',
    path: 'assistantai_admin.db',
    dbUrl: ''
  })

  const DB_TYPES = {
    postgresql: { port: 5432 },
    mysql: { port: 3306 },
    sqlite: { port: null }
  }

  useEffect(() => {
    loadAdminDbInfo()
  }, [])

  const loadAdminDbInfo = async () => {
    try {
      const { data } = await api.get('/api/settings/admin-db/info')
      setAdminDbInfo(data.admin_db)
      setForm(prev => ({ ...prev, dbUrl: data.admin_db.url || '' }))
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const handleFormChange = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const testConnection = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/admin-db/test', form)
      if (data.success) {
        setMsg({ type: 'success', text: 'Connection successful!' })
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const createDatabase = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/admin-db/create', form)
      if (data.success) {
        setMsg({ type: 'success', text: data.message })
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const startMigration = async () => {
    const confirm = await Swal.fire({
      title: 'Migrate Admin Database',
      text: `This will migrate all data from the current admin database to a new ${form.dbType} database and update .env. This process cannot be undone without a backup. Ensure you have a backup before proceeding.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Migrate',
      cancelButtonText: 'Cancel',
      confirmButtonColor: '#dc2626',
    })
    if (!confirm.isConfirmed) return

    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/admin-db/migrate', form)
      if (data.success) {
        setMsg({ type: 'success', text: `${data.message}. Please restart the application to use the new database.` })
        setTimeout(() => loadAdminDbInfo(), 2000)
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const updateAdminDbUrl = async () => {
    if (!form.dbUrl || form.dbUrl === adminDbInfo?.url) {
      setMsg({ type: 'warning', text: 'Please enter a different URL' })
      return
    }

    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/admin-db/update-url', { admin_db_url: form.dbUrl })
      if (data.success) {
        setMsg({ type: 'success', text: `${data.message}` })
        setAdminDbInfo(data.admin_db)
        setTimeout(() => loadAdminDbInfo(), 2000)
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  if (!adminDbInfo) return <Loader className="animate-spin text-gray-400" />

  return (
    <div className="card w-full space-y-5">
      <Banner msg={msg} />

      {/* Current Admin DB Info */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <Database size={18} /> Current Admin Database
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
          <div>
            <span className="text-gray-600">Type:</span>
            <p className="font-mono font-semibold text-gray-900">{adminDbInfo.type || 'unknown'}</p>
          </div>
          <div>
            <span className="text-gray-600">Status:</span>
            <p className={`font-semibold ${adminDbInfo.accessible ? 'text-green-700' : 'text-red-700'}`}>
              {adminDbInfo.accessible ? 'Accessible' : 'Not Accessible'}
            </p>
          </div>
          {adminDbInfo.table_count !== undefined && (
            <div>
              <span className="text-gray-600">Tables:</span>
              <p className="font-mono font-semibold text-gray-900">{adminDbInfo.table_count}</p>
            </div>
          )}
          {adminDbInfo.size_bytes !== undefined && (
            <div>
              <span className="text-gray-600">Size:</span>
              <p className="font-mono font-semibold text-gray-900">{(adminDbInfo.size_bytes / 1024).toFixed(2)} KB</p>
            </div>
          )}
        </div>
        {adminDbInfo.url && (
          <div className="border-t border-gray-200 pt-3">
            <span className="text-gray-600">URL:</span>
            <div className="flex items-center gap-2 mt-1">
              <p className="font-mono font-semibold text-gray-900 text-xs flex-1 break-all">{adminDbInfo.url}</p>
              <button
                onClick={() => copyToClipboard(adminDbInfo.url).catch(() => {})}
                className="text-gray-400 hover:text-brand-600"
                title="Copy URL"
              >
                <Copy size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-3 border-b pb-4">
        <button onClick={() => setMode('info')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            mode === 'info' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'}`}>
          Information
        </button>
        <button onClick={() => setMode('migrate')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            mode === 'migrate' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'}`}>
          Migrate
        </button>
      </div>

      {/* Info Mode */}
      {mode === 'info' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              The admin database stores conversations, settings, training data, and audit logs. 
              You can migrate this database from SQLite to PostgreSQL or MySQL for better scalability and performance.
            </p>
            <ul className="list-disc list-inside text-sm text-blue-900 space-y-2 mt-3">
              <li>Create a backup before migration</li>
              <li>Migration will preserve all data</li>
              <li>The .env file will be automatically updated</li>
              <li>Restart the application to use the new database</li>
            </ul>
          </div>
          <div>
            <label className="block text-sm text-gray-600 font-medium mb-2">Admin Database URL</label>
            <div className="flex gap-2">
              <input className="input flex-1" value={form.dbUrl || ''}
                onChange={(e) => handleFormChange('dbUrl', e.target.value)}
                placeholder="e.g. sqlite:///assistantai.db or postgresql+psycopg2://user:pass@host:5432/db" />
              <button onClick={updateAdminDbUrl} disabled={busy}
                className="btn-primary flex items-center gap-1 whitespace-nowrap">
                {busy ? <Loader size={16} className="animate-spin" /> : <Save size={16} />} Save URL
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">Enter the full database connection URL. Changes require application restart.</p>
          </div>
        </div>
      )}

      {/* Migrate Mode */}
      {mode === 'migrate' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 font-medium mb-2">Target Database Type</label>
            <select className="input" value={form.dbType}
              onChange={(e) => handleFormChange('dbType', e.target.value)}>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
            </select>
          </div>

          {form.dbType === 'sqlite' && (
            <div>
              <label className="block text-sm text-gray-600 font-medium mb-2">Database File Path</label>
              <input className="input" value={form.path}
                onChange={(e) => handleFormChange('path', e.target.value)}
                placeholder="/path/to/database.db" />
              <p className="text-xs text-gray-400 mt-1">Relative or absolute file path for SQLite database</p>
            </div>
          )}

          {form.dbType !== 'sqlite' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-600 font-medium mb-2">Host</label>
                  <input className="input" value={form.host}
                    onChange={(e) => handleFormChange('host', e.target.value)}
                    placeholder="localhost" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 font-medium mb-2">Port</label>
                  <input className="input" type="number" value={form.port}
                    onChange={(e) => handleFormChange('port', parseInt(e.target.value))}
                    placeholder={DB_TYPES[form.dbType].port} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-600 font-medium mb-2">Username</label>
                  <input className="input" value={form.username}
                    onChange={(e) => handleFormChange('username', e.target.value)}
                    placeholder="user" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 font-medium mb-2">Password</label>
                  <input className="input" type="password" value={form.password}
                    onChange={(e) => handleFormChange('password', e.target.value)}
                    placeholder="••••••" />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-600 font-medium mb-2">Database Name</label>
                <input className="input" value={form.database}
                  onChange={(e) => handleFormChange('database', e.target.value)}
                  placeholder="assistantai_admin" />
              </div>
            </>
          )}

          <div className="flex gap-2 flex-wrap">
            <button onClick={testConnection} disabled={busy}
              className="btn-secondary flex items-center gap-1">
              {busy ? <Loader size={16} className="animate-spin" /> : <Play size={16} />} Test Connection
            </button>
            <button onClick={createDatabase} disabled={busy}
              className="btn-secondary flex items-center gap-1">
              {busy ? <Loader size={16} className="animate-spin" /> : <Database size={16} />} Create DB
            </button>
            <button onClick={startMigration} disabled={busy}
              className="btn-primary flex items-center gap-1">
              {busy ? <Loader size={16} className="animate-spin" /> : <RefreshCw size={16} />} Migrate Data
            </button>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded p-3">
            <p className="text-xs font-semibold text-amber-900 mb-2">⚠️ Important:</p>
            <ul className="text-xs text-amber-800 space-y-1 list-disc list-inside">
              <li>Ensure the target database server is running and accessible</li>
              <li>Create a backup of your current admin database before proceeding</li>
              <li>The migration will preserve all your data</li>
              <li>After migration, restart the application to use the new database</li>
              <li>.env file will be automatically updated with the new ADMIN_DB_URL</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

/* --------------------------- SQLite --------------------------- */
function SQLiteTab() {
  const [info, setInfo] = useState(null)
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [rowsState, setRowsState] = useState({ rows: [], total: 0, columns: [], page: 1, page_size: 30, pk_column: null })
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [selectedRowIds, setSelectedRowIds] = useState([])
  const [newRowForm, setNewRowForm] = useState({})
  const [editTarget, setEditTarget] = useState(null)
  const [editRowForm, setEditRowForm] = useState({})

  const loadInfo = async () => {
    try {
      const { data } = await api.get('/api/settings/sqlite')
      setInfo(data)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const loadTables = async () => {
    try {
      const { data } = await api.get('/api/settings/sqlite/tables')
      const items = data.items || []
      setTables(items)
      if (!selectedTable && items.length) setSelectedTable(items[0].table)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const loadRows = async (tableName = selectedTable, page = 1) => {
    if (!tableName) return
    setBusy(true)
    try {
      const { data } = await api.get(`/api/settings/sqlite/table/${encodeURIComponent(tableName)}?page=${page}&page_size=30`)
      setRowsState({
        rows: data.rows || [],
        total: data.total || 0,
        columns: data.columns || [],
        page: data.page || 1,
        page_size: data.page_size || 30,
        pk_column: data.pk_column || null,
      })
      setSelectedRowIds([])
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { loadInfo(); loadTables() }, [])
  useEffect(() => { loadRows(selectedTable, 1) }, [selectedTable])

  useEffect(() => {
    const defaults = {}
    for (const col of rowsState.columns) {
      defaults[col.name] = ''
    }
    setNewRowForm(defaults)
  }, [selectedTable, rowsState.columns])

  const setFormValue = (setter, current, key, value) => {
    setter({ ...current, [key]: value })
  }

  const addRow = async () => {
    if (!selectedTable) return
    const row = Object.fromEntries(Object.entries(newRowForm).filter(([, value]) => value !== ''))
    try {
      await api.post(`/api/settings/sqlite/table/${encodeURIComponent(selectedTable)}`, { row })
      setMsg({ type: 'success', text: 'Row inserted.' })
      await loadTables()
      await loadRows(selectedTable, rowsState.page)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const delRow = async (recordId) => {
    if (!selectedTable) return
    if (!(await confirmDeleteAction('Delete this row?'))) return
    try {
      await api.delete(`/api/settings/sqlite/table/${encodeURIComponent(selectedTable)}/${encodeURIComponent(recordId)}`)
      setMsg({ type: 'success', text: 'Row deleted.' })
      await loadTables()
      await loadRows(selectedTable, rowsState.page)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  const toggleRowSelection = (recordId, checked) => {
    if (checked) {
      setSelectedRowIds((prev) => Array.from(new Set([...prev, recordId])))
    } else {
      setSelectedRowIds((prev) => prev.filter((id) => id !== recordId))
    }
  }

  const toggleSelectAllRows = (checked) => {
    if (checked) {
      setSelectedRowIds(rowsState.rows.map((row) => row.__record_id))
    } else {
      setSelectedRowIds([])
    }
  }

  const deleteSelectedRows = async () => {
    if (!selectedTable || !selectedRowIds.length) return
    if (!(await confirmDeleteAction(`Delete ${selectedRowIds.length} selected row(s)?`))) return
    setBusy(true)
    try {
      await Promise.all(
        selectedRowIds.map((recordId) =>
          api.delete(`/api/settings/sqlite/table/${encodeURIComponent(selectedTable)}/${encodeURIComponent(recordId)}`)
        )
      )
      setMsg({ type: 'success', text: `${selectedRowIds.length} row(s) deleted.` })
      await loadTables()
      await loadRows(selectedTable, rowsState.page)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const startEdit = (row) => {
    setEditTarget(row.__record_id)
    const clone = { ...row }
    delete clone.__record_id
    setEditRowForm(clone)
  }

  const saveEdit = async () => {
    if (!selectedTable || editTarget == null) return
    const row = editRowForm
    try {
      await api.put(`/api/settings/sqlite/table/${encodeURIComponent(selectedTable)}/${encodeURIComponent(editTarget)}`, { row })
      setMsg({ type: 'success', text: 'Row updated.' })
      setEditTarget(null)
      await loadRows(selectedTable, rowsState.page)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  if (!info) return <Loader className="animate-spin text-gray-400" />

  const totalPages = Math.max(1, Math.ceil((rowsState.total || 0) / (rowsState.page_size || 30)))

  return (
    <div className="space-y-4">
      <Banner msg={msg} />
      <div className="card space-y-3">
        <div>
          <h3 className="font-medium text-sm">Admin SQLite database (browse + CRUD)</h3>
          <p className="text-xs text-gray-400 mt-1">Browse all tables and perform create, update and delete operations on rows.</p>
        </div>
        <div>
          <label className="text-sm text-gray-600">Admin DB URL</label>
          <input className="input mt-1" value={info.admin_db_url || ''} readOnly />
        </div>
        <div>
          <label className="text-sm text-gray-600">File path</label>
          <input className="input mt-1" value={info.file_path || ''} readOnly />
          <p className="text-xs text-gray-400 mt-1">{info.exists ? `File exists | ${formatBytes(info.size_bytes)}` : 'File not found on disk'}</p>
        </div>
      </div>

      <div className="card space-y-3">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Table</label>
          <select className="input w-72" value={selectedTable} onChange={(e) => setSelectedTable(e.target.value)}>
            {tables.map((t) => <option key={t.table} value={t.table}>{t.table} ({t.row_count})</option>)}
          </select>
          <button onClick={() => { loadTables(); loadRows(selectedTable, rowsState.page) }} className="btn-secondary text-xs">Refresh</button>
          <button onClick={deleteSelectedRows} disabled={!selectedRowIds.length || busy} className="btn-secondary text-xs text-red-600 border-red-200 hover:bg-red-50">
            Delete selected ({selectedRowIds.length})
          </button>
        </div>

        {busy ? <Loader className="animate-spin text-gray-400" /> : (
          <div className="overflow-x-auto border border-gray-100 rounded-lg">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-2 py-2">
                    <input
                      type="checkbox"
                      checked={rowsState.rows.length > 0 && selectedRowIds.length === rowsState.rows.length}
                      onChange={(e) => toggleSelectAllRows(e.target.checked)}
                    />
                  </th>
                  <th className="px-2 py-2">ID</th>
                  {rowsState.columns.map((c) => <th key={c.name} className="px-2 py-2">{c.name}</th>)}
                  <th className="px-2 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rowsState.rows.map((r) => (
                  <tr key={r.__record_id} className="border-t border-gray-100 align-top">
                    <td className="px-2 py-1.5">
                      <input
                        type="checkbox"
                        checked={selectedRowIds.includes(r.__record_id)}
                        onChange={(e) => toggleRowSelection(r.__record_id, e.target.checked)}
                      />
                    </td>
                    <td className="px-2 py-1.5 text-gray-500">{String(r.__record_id)}</td>
                    {rowsState.columns.map((c) => <td key={`${r.__record_id}-${c.name}`} className="px-2 py-1.5 max-w-[260px] truncate">{String(r[c.name] ?? '')}</td>)}
                    <td className="px-2 py-1.5">
                      <div className="flex items-center gap-2">
                        <button onClick={() => startEdit(r)} className="text-gray-500 hover:text-brand-600">Edit</button>
                        <button onClick={() => delRow(r.__record_id)} className="text-gray-500 hover:text-red-600">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {rowsState.rows.length === 0 && (
                  <tr><td className="px-3 py-3 text-gray-400" colSpan={Math.max(3, rowsState.columns.length + 2)}>No rows.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            onClick={() => loadRows(selectedTable, Math.max(1, rowsState.page - 1))}
            disabled={rowsState.page <= 1}
            className="btn-secondary text-xs"
          >Prev</button>
          <span className="text-xs text-gray-500">Page {rowsState.page} / {totalPages}</span>
          <button
            onClick={() => loadRows(selectedTable, Math.min(totalPages, rowsState.page + 1))}
            disabled={rowsState.page >= totalPages}
            className="btn-secondary text-xs"
          >Next</button>
        </div>
      </div>

      <div className="card space-y-2">
        <h4 className="font-medium text-sm">Insert row</h4>
        <div className="grid md:grid-cols-2 gap-3">
          {rowsState.columns.map((col) => (
            <div key={`new-${col.name}`}>
              <label className="text-xs text-gray-600">{col.name}</label>
              <input
                className="input mt-1 text-xs"
                value={newRowForm[col.name] ?? ''}
                onChange={(e) => setFormValue(setNewRowForm, newRowForm, col.name, e.target.value)}
              />
            </div>
          ))}
        </div>
        <button onClick={addRow} className="btn-primary text-xs">Insert</button>
      </div>

      {editTarget != null && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-sm">Edit row #{String(editTarget)}</h3>
              <button onClick={() => setEditTarget(null)} className="text-gray-400 hover:text-gray-700"><X size={16} /></button>
            </div>
            <div className="grid md:grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto pr-1">
              {rowsState.columns.map((col) => (
                <div key={`edit-${col.name}`}>
                  <label className="text-xs text-gray-600">{col.name}</label>
                  <input
                    className="input mt-1 text-xs"
                    value={editRowForm[col.name] ?? ''}
                    onChange={(e) => setFormValue(setEditRowForm, editRowForm, col.name, e.target.value)}
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button onClick={() => setEditTarget(null)} className="btn-secondary text-xs">Cancel</button>
              <button onClick={saveEdit} className="btn-primary text-xs">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* -------------------------- Vector store ------------------------ */
function VectorTab({ onChanged }) {
  const [cfg, setCfg] = useState(null)
  const [stores, setStores] = useState([])
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/api/settings/vector').then(({ data }) => setCfg(data.config))
    api.get('/api/settings/vector/stores').then(({ data }) => setStores(data.stores || []))
  }, [])
  if (!cfg) return <Loader className="animate-spin text-gray-400" />
  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }))

  const save = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post('/api/settings/vector', cfg)
      setCfg(data.config)
      setMsg({ type: 'success', text: 'Vector store settings saved.' })
      onChanged?.()
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="card w-full space-y-4">
      <Banner msg={msg} />
      <div>
        <label className="text-sm text-gray-600">Vector store</label>
        <select className="input mt-1" value={cfg.store} onChange={(e) => set('store', e.target.value)}>
          {stores.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>
      {cfg.store === 'chromadb' && (
        <Field label="ChromaDB path" value={cfg.chroma_path} onChange={(v) => set('chroma_path', v)} />
      )}
      {cfg.store === 'faiss' && (
        <Field label="FAISS path" value={cfg.faiss_path} onChange={(v) => set('faiss_path', v)} />
      )}
      {cfg.store === 'pinecone' && (
        <>
          <KeyField label="Pinecone API Key" set={cfg.pinecone_api_key_set} onChange={(v) => set('pinecone_api_key', v)} />
          <Field label="Pinecone index" value={cfg.pinecone_index} onChange={(v) => set('pinecone_index', v)} />
          <Field label="Pinecone environment" value={cfg.pinecone_environment} onChange={(v) => set('pinecone_environment', v)} />
        </>
      )}
      <Field label="Embedding model (sentence-transformers)" value={cfg.embedding_model} onChange={(v) => set('embedding_model', v)} />
      <button onClick={save} disabled={busy} className="btn-primary flex items-center gap-1">
        {busy ? <Loader size={16} className="animate-spin" /> : <Save size={16} />} Save
      </button>
    </div>
  )
}

function Field({ label, value, onChange }) {
  return (
    <div>
      <label className="text-sm text-gray-600">{label}</label>
      <input className="input mt-1" value={value || ''} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return 'Unknown size'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let u = 0
  while (size >= 1024 && u < units.length - 1) {
    size /= 1024
    u += 1
  }
  return `${size.toFixed(1)} ${units[u]}`
}

/* -------------------------- Training/RAG ------------------------ */
function TrainingTab() {
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [formCollapsed, setFormCollapsed] = useState(true)
  const [trainingType, setTrainingType] = useState('ddl')
  const [trainingRule, setTrainingRule] = useState('optional')
  const [trainingAccess, setTrainingAccess] = useState('all')
  const [form, setForm] = useState({ ddl: '', doc: '', question: '', sql: '' })
  const [kbItems, setKbItems] = useState([])
  const [kbFile, setKbFile] = useState(null)
  const [kbAccess, setKbAccess] = useState('all')
  const [selectedItems, setSelectedItems] = useState(new Set())
  const [bulkRule, setBulkRule] = useState('')
  const [bulkAccess, setBulkAccess] = useState('')
  const [bulkType, setBulkType] = useState('')
  const [showBulkUpdate, setShowBulkUpdate] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const resetBulkUpdateForm = () => {
    setBulkRule('')
    setBulkAccess('')
    setBulkType('')
  }

  const load = async () => {
    const [trainingRes, kbRes] = await Promise.all([
      api.get('/api/training'),
      api.get('/api/training/knowledge-base'),
    ])
    setItems(trainingRes.data.items || [])
    setKbItems(kbRes.data.items || [])
  }
  useEffect(() => { load() }, [])

  const post = async (url, body, okText) => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post(url, body)
      if (data.success) { setMsg({ type: 'success', text: okText }); load() }
      else setMsg({ type: 'error', text: data.error })
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
    finally { setBusy(false) }
  }

  const del = async (id) => { await api.delete(`/api/training/${id}`); load() }

  const update = async (id, body) => {
    setMsg(null)
    const { data } = await api.put(`/api/training/${id}`, body)
    if (data.success) { setMsg({ type: 'success', text: 'Training item updated.' }); await load() }
    else { setMsg({ type: 'error', text: data.error }); throw new Error(data.error) }
  }

  const resetForm = () => {
    setEditingItem(null)
    setTrainingType('ddl')
    setTrainingRule('optional')
    setTrainingAccess('all')
    setForm({ ddl: '', doc: '', question: '', sql: '' })
  }

  const beginEdit = (item) => {
    setEditingItem(item)
    const type = item.item_type || 'ddl'
    setTrainingType(type)
    setTrainingRule(item.rule || 'optional')
    setTrainingAccess(item.access || 'all')
    if (type === 'sql') {
      setForm({ ddl: '', doc: '', question: item.question || '', sql: item.content || '' })
    } else if (type === 'documentation') {
      setForm({ ddl: '', doc: item.content || '', question: '', sql: '' })
    } else {
      setForm({ ddl: item.content || '', doc: '', question: '', sql: '' })
    }
  }

  const submitForm = async () => {
    setBusy(true)
    setMsg(null)
    try {
      if (!editingItem) {
        if (trainingType === 'ddl') {
          await post('/api/training/ddl', { ddl: form.ddl, rule: trainingRule, access: trainingAccess }, 'DDL trained.')
        } else if (trainingType === 'documentation') {
          await post('/api/training/documentation', { documentation: form.doc, rule: trainingRule, access: trainingAccess }, 'Documentation trained.')
        } else {
          await post('/api/training/sql', { question: form.question, sql: form.sql, rule: trainingRule, access: trainingAccess }, 'Q/SQL pair trained.')
        }
      } else {
        const content = trainingType === 'ddl' ? form.ddl : trainingType === 'documentation' ? form.doc : form.sql
        await update(editingItem.id, {
          item_type: trainingType,
          rule: trainingRule,
          access: trainingAccess,
          content,
          question: trainingType === 'sql' ? form.question : undefined,
        })
      }
      resetForm()
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const uploadKnowledgeBase = async () => {
    if (!kbFile) return
    setBusy(true)
    setMsg(null)
    try {
      const fd = new FormData()
      fd.append('file', kbFile)
      fd.append('access', kbAccess)
      const { data } = await api.post('/api/training/knowledge-base/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (data.success) {
        setMsg({ type: 'success', text: 'Knowledge base file ingested and trained.' })
        setKbFile(null)
        await load()
      } else {
        setMsg({ type: 'error', text: data.error || 'Upload failed.' })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  const toggleItemSelection = (id) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedItems(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedItems.size === items.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(items.map(i => i.id)))
    }
  }

  const doBulkUpdate = async () => {
    if (selectedItems.size === 0) {
      setMsg({ type: 'error', text: 'Please select at least one training item.' })
      return
    }
    setBusy(true)
    setMsg(null)
    try {
      const updates = {}
      if (bulkRule !== '') updates.rule = bulkRule
      if (bulkAccess !== '') updates.access = bulkAccess
      if (bulkType !== '') updates.item_type = bulkType
      
      if (Object.keys(updates).length === 0) {
        setMsg({ type: 'error', text: 'Please select at least one field to update.' })
        setBusy(false)
        return
      }

      const { data } = await api.post('/api/training/bulk/update', {
        item_ids: Array.from(selectedItems),
        updates,
      })
      if (data.success) {
        setMsg({ type: 'success', text: `Updated ${data.updated_count} training items.` })
        setSelectedItems(new Set())
        resetBulkUpdateForm()
        setShowBulkUpdate(false)
        await load()
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setBusy(false)
    }
  }

  // Filter items based on search query
  const filteredItems = items.filter((it) => {
    const searchLower = searchQuery.toLowerCase()
    const question = (it.question || '').toLowerCase()
    const content = (it.content || '').toLowerCase()
    const itemType = (it.item_type || '').toLowerCase()
    return (
      question.includes(searchLower) ||
      content.includes(searchLower) ||
      itemType.includes(searchLower)
    )
  })

  return (
    <div className="space-y-4">
      <Banner msg={msg} />
      <div className="card space-y-2 w-full">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-sm">{editingItem ? `Edit Training Item #${editingItem.id}` : 'Add Training Data'}</h3>
          <button onClick={() => setFormCollapsed(!formCollapsed)} className="text-gray-500 hover:text-gray-700">
            {formCollapsed ? '▶' : '▼'}
          </button>
        </div>
        
        {!formCollapsed && (
          <>
        <label className="block mb-1 text-xs font-medium text-gray-700">Training Type</label>
        <select className="input mb-2" value={trainingType} onChange={e=>{setTrainingType(e.target.value)}}>
          <option value="ddl">DDL (CREATE TABLE)</option>
          <option value="documentation">Documentation</option>
          <option value="sql">Question→SQL pair</option>
        </select>

        <label className="block mb-1 text-xs font-medium text-gray-700">Rule</label>
        <select className="input mb-2" value={trainingRule} onChange={(e) => setTrainingRule(e.target.value)}>
          <option value="optional">Optional</option>
          <option value="compulsory">Compulsory</option>
        </select>

        <label className="block mb-1 text-xs font-medium text-gray-700">Access</label>
        <select className="input mb-2" value={trainingAccess} onChange={(e) => setTrainingAccess(e.target.value)}>
          <option value="all">All users (including guest)</option>
          <option value="authenticated">Logged-in users only (exclude guest)</option>
        </select>

        {/* DDL */}
        {trainingType === 'ddl' && (
          <>
            <label className="block text-xs font-medium text-gray-700">DDL <span className="text-red-500">*</span></label>
            <textarea className="input h-24 font-mono text-xs" value={form.ddl} required onChange={e=>setForm({...form, ddl:e.target.value})}/>
          </>
        )}
        {/* Documentation */}
        {trainingType === 'documentation' && (
          <>
            <label className="block text-xs font-medium text-gray-700">Documentation <span className="text-red-500">*</span></label>
            <textarea className="input h-24 text-xs" value={form.doc} required onChange={e=>setForm({...form, doc:e.target.value})}/>
          </>
        )}
        {/* SQL Pair */}
        {trainingType === 'sql' && (
          <>
            <label className="block text-xs font-medium text-gray-700">Question <span className="text-red-500">*</span></label>
            <input className="input text-xs" placeholder="Question..." value={form.question} required onChange={e=>setForm({...form, question:e.target.value})}/>
            <label className="block text-xs font-medium text-gray-700 mt-2">SQL <span className="text-red-500">*</span></label>
            <textarea className="input h-16 font-mono text-xs" placeholder="SQL..." value={form.sql} required onChange={e=>setForm({...form, sql:e.target.value})}/>
          </>
        )}

        <button
          disabled={busy || (trainingType==='ddl' && !form.ddl.trim()) || (trainingType==='documentation' && !form.doc.trim()) ||
            (trainingType==='sql' && (!form.question.trim() || !form.sql.trim()))}
          className="btn-primary text-sm mt-2"
          onClick={submitForm}>
          {editingItem ? 'Update Training Item' : 'Add Training Data'}
        </button>
        {editingItem && (
          <button className="btn-secondary text-sm mt-2 ml-2" onClick={resetForm} disabled={busy}>
            Cancel Edit
          </button>
        )}
          </>
        )}
      </div>
      <div className="card space-y-3 w-full">
        <div>
          <h3 className="font-medium text-sm">Knowledge Base</h3>
          <p className="text-xs text-gray-400 mt-1">Upload Word, Excel, PowerPoint, PDF, PNG or JPG files. Each upload becomes RAG training data.</p>
        </div>
        <div className="grid md:grid-cols-[1fr_240px_180px] gap-2">
          <input
            type="file"
            className="input text-sm"
            accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.png,.jpg,.jpeg"
            onChange={(e) => setKbFile(e.target.files?.[0] || null)}
          />
          <select className="input" value={kbAccess} onChange={(e) => setKbAccess(e.target.value)}>
            <option value="all">All users (including guest)</option>
            <option value="authenticated">Logged-in users only</option>
          </select>
          <button onClick={uploadKnowledgeBase} disabled={busy || !kbFile} className="btn-primary text-sm">
            Upload & Train
          </button>
        </div>
        <div className="space-y-1 max-h-56 overflow-y-auto border border-gray-100 rounded-lg p-2">
          {kbItems.map((it) => (
            <div key={it.id} className="flex items-center justify-between text-xs border-b border-gray-100 py-1.5 last:border-b-0">
              <div className="flex-1 min-w-0">
                <p className="truncate text-gray-700 font-medium">{it.source_name || `knowledge-item-${it.id}`}</p>
                <p className="text-[11px] text-gray-400">{it.source_file_type || 'file'} • {it.access || 'all'} • {String(it.created_at || '').slice(0, 19).replace('T', ' ')}</p>
              </div>
              <button onClick={() => del(it.id)} className="text-gray-400 hover:text-red-500 ml-3" title="Delete"><Trash2 size={14} /></button>
            </div>
          ))}
          {kbItems.length === 0 && <p className="text-xs text-gray-400">No knowledge base uploads yet.</p>}
        </div>
      </div>

      <div className="card md:col-span-2 flex items-center justify-between">
        <div>
          <h3 className="font-medium text-sm">Auto-train from INFORMATION_SCHEMA</h3>
          <p className="text-xs text-gray-400">Trains on the connected source DB's table/column plan.</p>
        </div>
        <button disabled={busy} onClick={() => post('/api/training/auto/information-schema', {}, 'Auto-trained on schema.')} className="btn-secondary text-sm flex items-center gap-1">
          <Play size={14} /> Run
        </button>
      </div>
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-sm">Training items ({searchQuery ? `${filteredItems.length}/${items.length}` : items.length}) <span className="text-xs text-gray-400">(shows compulsory and logged-in-only badges)</span></h3>
          {items.length > 0 && (
            <button 
              onClick={() => {
                if (showBulkUpdate) {
                  resetBulkUpdateForm()
                }
                setShowBulkUpdate(!showBulkUpdate)
              }}
              className="text-xs text-brand-600 hover:text-brand-700"
            >
              {showBulkUpdate ? 'Hide' : 'Bulk Edit'}
            </button>
          )}
        </div>

        {showBulkUpdate && items.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3 space-y-2">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox" 
                checked={selectedItems.size === items.length && items.length > 0}
                onChange={toggleSelectAll}
                className="rounded"
              />
              <span className="text-xs font-medium text-gray-700">
                Select all ({selectedItems.size}/{items.length} selected)
              </span>
            </div>

            {selectedItems.size > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 bg-white p-2 rounded border border-blue-100">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Rule</label>
                  <select 
                    className="input text-xs"
                    value={bulkRule}
                    onChange={(e) => setBulkRule(e.target.value)}
                  >
                    <option value="">-- No change --</option>
                    <option value="optional">Optional</option>
                    <option value="compulsory">Compulsory</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Access</label>
                  <select 
                    className="input text-xs"
                    value={bulkAccess}
                    onChange={(e) => setBulkAccess(e.target.value)}
                  >
                    <option value="">-- No change --</option>
                    <option value="all">All users</option>
                    <option value="authenticated">Logged-in only</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select 
                    className="input text-xs"
                    value={bulkType}
                    onChange={(e) => setBulkType(e.target.value)}
                  >
                    <option value="">-- No change --</option>
                    <option value="ddl">DDL</option>
                    <option value="documentation">Documentation</option>
                    <option value="sql">SQL Pair</option>
                  </select>
                </div>
              </div>
            )}

            {selectedItems.size > 0 && (
              <div className="flex gap-2 pt-2">
                <button 
                  onClick={doBulkUpdate}
                  disabled={busy}
                  className="btn-primary text-xs"
                >
                  Update {selectedItems.size} items
                </button>
              </div>
            )}
          </div>
        )}

        <div className="mb-3">
          <input
            type="text"
            placeholder="Search training data (question, content, type)..."
            className="input text-sm w-full"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="space-y-1 max-h-96 overflow-y-auto">
          {filteredItems.map((it) => (
            <TrainingItemRow 
              key={it.id} 
              item={it} 
              onEditStart={beginEdit} 
              onDelete={del}
              selected={selectedItems.has(it.id)}
              onToggleSelect={toggleItemSelection}
              showCheckbox={showBulkUpdate}
            />
          ))}
          {filteredItems.length === 0 && <p className="text-xs text-gray-400">{searchQuery ? 'No results found.' : 'No training data yet.'}</p>}
        </div>
      </div>
    </div>
  )
}

/* --------------------- Training item (editable) ----------------- */
function TrainingItemRow({ item, onEditStart, onDelete, selected, onToggleSelect, showCheckbox }) {
  const access = item.access || 'all'
  const authOnly = access === 'authenticated'
  const compulsory = (item.rule || 'optional') === 'compulsory'

  return (
    <div className={`flex items-center justify-between text-xs border-b border-gray-100 py-1.5 ${selected ? 'bg-blue-50' : ''}`}>
      {showCheckbox && (
        <input 
          type="checkbox"
          checked={selected}
          onChange={() => onToggleSelect(item.id)}
          className="rounded mr-2"
        />
      )}
      <span className="px-2 py-0.5 rounded bg-gray-100 text-gray-600 mr-2">{item.item_type}</span>
      {compulsory && <span className="ml-1 px-1.5 py-0.5 rounded bg-red-50 text-red-700 text-xs">compulsory</span>}
      {authOnly && <span className="ml-1 px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 text-xs">logged-in only</span>}
      <span className="flex-1 truncate text-gray-700">{item.question || item.content}</span>
      <div className="flex items-center gap-2 ml-2">
        <button onClick={() => onEditStart(item)} className="text-gray-400 hover:text-brand-600" title="Edit"><Pencil size={14} /></button>
        <button onClick={() => onDelete(item.id)} className="text-gray-400 hover:text-red-500" title="Delete"><Trash2 size={14} /></button>
      </div>
    </div>
  )
}

/* ------------------------- Data Exchange ------------------------ */
function DataExchangeTab() {
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [includeSamples, setIncludeSamples] = useState(true)
  const [summary, setSummary] = useState(null)
  const [counts, setCounts] = useState(null)
  const [exportData, setExportData] = useState(null)
  const [fileName, setFileName] = useState('')

  const onFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name); setMsg(null); setCounts(null); setSummary(null)
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      setExportData(json)
      const { data } = await api.post('/api/data-exchange/preview', { export_data: json })
      if (data.success) setSummary(data.summary)
    } catch (err) {
      setMsg({ type: 'error', text: 'Could not read/parse the file. Make sure it is the brainz Data Exchange JSON export.' })
      setExportData(null)
    }
  }

  const doImport = async () => {
    if (!exportData) return
    setBusy(true); setMsg(null); setCounts(null)
    try {
      const { data } = await api.post('/api/data-exchange/import', {
        export_data: exportData,
        include_sample_data: includeSamples,
      })
      if (data.success) {
        setMsg({ type: 'success', text: data.message })
        setCounts(data.counts)
      } else {
        setMsg({ type: 'error', text: data.error })
      }
    } catch (err) {
      setMsg({ type: 'error', text: handleApiError(err).message })
    } finally {
      setBusy(false)
    }
  }

  const doExport = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.get('/api/data-exchange/export')
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'})
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'assistantai-export.json'
      document.body.appendChild(a)
      a.click()
      setTimeout(()=>{
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }, 200)
    } catch (err) {
      setMsg({ type: 'error', text: 'Could not export data.' })
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="card w-full space-y-4">
      <Banner msg={msg} />
      <div>
        <h3 className="font-medium text-sm">Bulk Import/Export of Training Data</h3>
        <p className="text-xs text-gray-400 mt-1">
          Import or export this project's AI training (RAG/DDL/docs) as a JSON file you can reuse elsewhere.
        </p>
      </div>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={doExport} className="btn-secondary flex items-center gap-1">
          <Download size={16}/>
          Export Data
        </button>
        <input type="file" accept="application/json,.json" onChange={onFile} className="input w-auto" />
      </div>
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          <Metric label="RAG records" value={summary.rag_records} />
          <Metric label="Business rules" value={summary.business_rules} />
          <Metric label="App settings" value={summary.app_settings} />
          <Metric label="LLM configs" value={summary.llm_configs} />
        </div>
      )}
      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input type="checkbox" checked={includeSamples} onChange={(e) => setIncludeSamples(e.target.checked)} />
        Include sample rows in training
      </label>
      <button onClick={doImport} disabled={busy || !exportData} className="btn-primary flex items-center gap-1">
        {busy ? <Loader size={16} className="animate-spin" /> : <Upload size={16} />} Import & Train
      </button>
      {counts && (
        <div className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3">
          Trained — DDL: {counts.ddl}, Documentation: {counts.documentation}, SQL: {counts.sql},
          Skipped: {counts.skipped}, Errors: {counts.errors}
        </div>
      )}
    </div>
  )
}

/* -------------------------- API DOC -------------------------- */
function ApiDocTab() {
  const [docs, setDocs] = useState([])
  const [activeSlug, setActiveSlug] = useState('')
  const [doc, setDoc] = useState('')
  const [docTitle, setDocTitle] = useState('')
  const [docCache, setDocCache] = useState({})
  const [searchQuery, setSearchQuery] = useState('')
  const [indexing, setIndexing] = useState(false)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDoc, setLoadingDoc] = useState(false)
  const [msg, setMsg] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const contentRef = useRef(null)

  const slugify = (text) =>
    String(text || '')
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')

  const textFromChildren = (children) => {
    if (typeof children === 'string') return children
    if (Array.isArray(children)) return children.map((c) => (typeof c === 'string' ? c : c?.props?.children || '')).join(' ')
    return children?.props?.children || ''
  }

  const stripMd = (s) =>
    String(s || '')
      .replace(/```[\s\S]*?```/g, ' ')
      .replace(/`[^`]*`/g, ' ')
      .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
      .replace(/\[[^\]]*\]\([^)]*\)/g, ' ')
      .replace(/[>#*_~|\-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()

  const makeSnippet = (rawText, q) => {
    const plain = stripMd(rawText)
    if (!plain) return ''
    const idx = plain.toLowerCase().indexOf(q.toLowerCase())
    if (idx < 0) return plain.slice(0, 180)
    const start = Math.max(0, idx - 80)
    const end = Math.min(plain.length, idx + q.length + 100)
    const prefix = start > 0 ? '... ' : ''
    const suffix = end < plain.length ? ' ...' : ''
    return `${prefix}${plain.slice(start, end)}${suffix}`
  }

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return []
    const out = []
    for (const d of docs) {
      const content = docCache[d.slug] || ''
      const inTitle = d.title.toLowerCase().includes(q)
      const inBody = content.toLowerCase().includes(q)
      if (!inTitle && !inBody) continue
      out.push({
        slug: d.slug,
        title: d.title,
        snippet: makeSnippet(content, q),
      })
    }
    return out.slice(0, 25)
  }, [searchQuery, docs, docCache])

  const headings = useMemo(() => {
    const lines = String(doc || '').split('\n')
    const out = []
    for (const line of lines) {
      const m = line.match(/^(#{1,3})\s+(.+)$/)
      if (!m) continue
      const level = m[1].length
      const text = (m[2] || '').trim()
      out.push({ level, text, id: slugify(text) })
    }
    return out
  }, [doc])

  const downloadPDF = async () => {
    if (!contentRef.current || !doc) return
    setDownloading(true)
    try {
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      })

      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const margin = 12
      const lineHeight = 5.5
      const maxWidth = pageWidth - 2 * margin
      let yPosition = margin

      // Add title page
      pdf.setFontSize(28)
      pdf.setFont(undefined, 'bold')
      pdf.text(docTitle || 'Documentation', margin, yPosition)
      
      yPosition += 15
      pdf.setFontSize(10)
      pdf.setFont(undefined, 'normal')
      pdf.setTextColor(100, 100, 100)
      pdf.text(`Generated on ${new Date().toLocaleDateString()}`, margin, yPosition)
      
      pdf.addPage()
      yPosition = margin
      pdf.setTextColor(0, 0, 0)

      // Parse markdown content into lines
      const lines = doc.split('\n')
      let inCodeBlock = false
      let codeBlockLines = []

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]

        // Check for code block
        if (line.startsWith('```')) {
          if (!inCodeBlock) {
            inCodeBlock = true
            codeBlockLines = []
          } else {
            // End code block
            inCodeBlock = false
            if (yPosition + codeBlockLines.length * 3.5 + 10 > pageHeight - margin) {
              pdf.addPage()
              yPosition = margin
            }
            
            pdf.setFillColor(240, 240, 240)
            pdf.rect(margin, yPosition, maxWidth, codeBlockLines.length * 3.5 + 4, 'F')
            pdf.setFont(undefined, 'normal')
            pdf.setFontSize(8)
            pdf.setTextColor(100, 100, 100)
            
            let codeY = yPosition + 2
            codeBlockLines.forEach(codeLine => {
              pdf.text(codeLine.substring(0, 100), margin + 2, codeY)
              codeY += 3.5
            })
            
            yPosition += codeBlockLines.length * 3.5 + 8
            pdf.setTextColor(0, 0, 0)
            pdf.setFontSize(10)
          }
          continue
        }

        if (inCodeBlock) {
          codeBlockLines.push(line)
          continue
        }

        // Handle headings
        if (line.startsWith('# ')) {
          if (yPosition > margin + 10) pdf.addPage()
          yPosition = margin
          pdf.setFontSize(20)
          pdf.setFont(undefined, 'bold')
          pdf.text(line.replace(/^# /, ''), margin, yPosition)
          yPosition += 12
          pdf.setFont(undefined, 'normal')
          pdf.setFontSize(10)
        } else if (line.startsWith('## ')) {
          if (yPosition > pageHeight - margin - 20) pdf.addPage()
          yPosition += 4
          pdf.setFontSize(14)
          pdf.setFont(undefined, 'bold')
          pdf.text(line.replace(/^## /, ''), margin, yPosition)
          yPosition += 8
          pdf.setFont(undefined, 'normal')
          pdf.setFontSize(10)
        } else if (line.startsWith('### ')) {
          if (yPosition > pageHeight - margin - 15) pdf.addPage()
          yPosition += 2
          pdf.setFontSize(11)
          pdf.setFont(undefined, 'bold')
          pdf.text(line.replace(/^### /, ''), margin, yPosition)
          yPosition += 6
          pdf.setFont(undefined, 'normal')
          pdf.setFontSize(10)
        }
        // Handle horizontal rules
        else if (line.trim() === '---') {
          if (yPosition > pageHeight - margin - 5) pdf.addPage()
          yPosition += 1
          pdf.setDrawColor(200, 200, 200)
          pdf.line(margin, yPosition, pageWidth - margin, yPosition)
          yPosition += 3
        }
        // Handle list items
        else if (line.match(/^[\*\-\+]\s/)) {
          if (yPosition > pageHeight - margin - 5) {
            pdf.addPage()
            yPosition = margin
          }
          const text = line.replace(/^[\*\-\+]\s/, '')
          const wrappedLines = pdf.splitTextToSize(text, maxWidth - 5)
          pdf.setFont(undefined, 'normal')
          pdf.text('• ' + wrappedLines[0], margin + 2, yPosition)
          yPosition += lineHeight
          
          for (let j = 1; j < wrappedLines.length; j++) {
            if (yPosition > pageHeight - margin) {
              pdf.addPage()
              yPosition = margin
            }
            pdf.text(wrappedLines[j], margin + 4, yPosition)
            yPosition += lineHeight
          }
        }
        // Handle numbered list items
        else if (line.match(/^\d+\.\s/)) {
          if (yPosition > pageHeight - margin - 5) {
            pdf.addPage()
            yPosition = margin
          }
          const match = line.match(/^(\d+)\.\s(.*)/)
          const num = match[1]
          const text = match[2]
          const wrappedLines = pdf.splitTextToSize(text, maxWidth - 8)
          pdf.setFont(undefined, 'normal')
          pdf.text(num + '. ' + wrappedLines[0], margin + 2, yPosition)
          yPosition += lineHeight
          
          for (let j = 1; j < wrappedLines.length; j++) {
            if (yPosition > pageHeight - margin) {
              pdf.addPage()
              yPosition = margin
            }
            pdf.text(wrappedLines[j], margin + 6, yPosition)
            yPosition += lineHeight
          }
        }
        // Handle regular paragraphs
        else if (line.trim() !== '') {
          if (yPosition > pageHeight - margin - 5) {
            pdf.addPage()
            yPosition = margin
          }
          const wrappedLines = pdf.splitTextToSize(line, maxWidth)
          pdf.setFont(undefined, 'normal')
          pdf.setFontSize(10)
          
          wrappedLines.forEach(wrappedLine => {
            if (yPosition > pageHeight - margin) {
              pdf.addPage()
              yPosition = margin
            }
            pdf.text(wrappedLine, margin, yPosition)
            yPosition += lineHeight
          })
        } else {
          // Empty line for spacing
          yPosition += 2
        }
      }

      // Table of contents feature is disabled due to jsPDF page management complexity
      // The TOC generation can interfere with page numbering and layout
      // This is a known limitation that would require significant refactoring to fix

      pdf.save(`${docTitle.replace(/\s+/g, '_')}_${new Date().getTime()}.pdf`)
      setMsg({ type: 'success', text: 'PDF downloaded successfully!' })
    } catch (error) {
      console.error('PDF generation error:', error)
      setMsg({ type: 'error', text: 'Failed to generate PDF. Please try again.' })
    } finally {
      setDownloading(false)
    }
  }

  useEffect(() => {
    const loadList = async () => {
      setLoadingList(true)
      setMsg(null)
      try {
        const { data } = await api.get('/api/settings/docs')
        const items = data?.items || []
        setDocs(items)
        if (items.length) {
          setIndexing(true)
          Promise.all(
            items.map(async (item) => {
              try {
                const { data: docData } = await api.get(`/api/settings/docs/${encodeURIComponent(item.slug)}`)
                return [item.slug, docData?.content || '']
              } catch (_) {
                return [item.slug, '']
              }
            })
          ).then((pairs) => {
            setDocCache(Object.fromEntries(pairs))
            setIndexing(false)
          })
        }
        if (items.length) {
          setActiveSlug(items[0].slug)
        } else {
          setMsg({ type: 'error', text: 'No docs found in docs folder.' })
        }
      } catch (e) {
        setMsg({ type: 'error', text: handleApiError(e).message })
      } finally {
        setLoadingList(false)
      }
    }
    loadList()
  }, [])

  useEffect(() => {
    if (!activeSlug) return
    const loadDoc = async () => {
      const fromCache = docCache[activeSlug]
      if (typeof fromCache === 'string' && fromCache.length > 0) {
        setDoc(fromCache)
        setDocTitle(docs.find((d) => d.slug === activeSlug)?.title || activeSlug)
        return
      }
      setLoadingDoc(true)
      setMsg(null)
      try {
        const { data } = await api.get(`/api/settings/docs/${encodeURIComponent(activeSlug)}`)
        if (data?.success) {
          setDoc(data.content || '')
          setDocTitle(data.title || activeSlug)
          setDocCache((prev) => ({ ...prev, [activeSlug]: data.content || '' }))
        } else {
          setMsg({ type: 'error', text: data?.error || 'Could not load selected doc.' })
        }
      } catch (e) {
        setMsg({ type: 'error', text: handleApiError(e).message })
      } finally {
        setLoadingDoc(false)
      }
    }
    loadDoc()
  }, [activeSlug, docCache, docs])

  return (
    <div className="space-y-4">
      <Banner msg={msg} />
      <div className="grid md:grid-cols-[260px_1fr] gap-4">
        <aside className="card h-fit md:sticky md:top-4">
          <h3 className="font-semibold text-sm mb-2">Docs</h3>
          {loadingList ? (
            <div className="flex items-center gap-2 text-xs text-gray-500"><Loader size={14} className="animate-spin" /> Loading docs...</div>
          ) : (
            <div className="space-y-1 max-h-[65vh] overflow-y-auto pr-1">
              {docs.map((d) => (
                <button
                  key={d.slug}
                  onClick={() => setActiveSlug(d.slug)}
                  className={`w-full text-left text-xs px-2 py-1.5 rounded ${activeSlug === d.slug ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  {d.title}
                </button>
              ))}
            </div>
          )}

          {headings.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <h4 className="text-[11px] font-semibold text-gray-500 mb-2 uppercase tracking-wide">On this page</h4>
              <div className="space-y-1 max-h-[30vh] overflow-y-auto pr-1">
                {headings.map((h, idx) => (
                  <a
                    key={`${h.id}-${idx}`}
                    href={`#${h.id}`}
                    className={`block text-xs text-gray-500 hover:text-brand-700 ${h.level === 1 ? 'pl-0' : h.level === 2 ? 'pl-3' : 'pl-6'}`}
                  >
                    {h.text}
                  </a>
                ))}
              </div>
            </div>
          )}
        </aside>

        <div className="card overflow-hidden flex flex-col min-w-0">
          <div className="mb-3 overflow-hidden">
            <label className="text-xs text-gray-500 block mb-1">Search entire documentation</label>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input pl-8 text-sm"
                placeholder="Search all docs by title or content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="mt-1 text-[11px] text-gray-400">
              {indexing ? 'Indexing docs for search...' : `Indexed ${docs.length} docs`}
            </div>
            {searchQuery.trim() && (
              <div className="mt-2 border border-gray-200 rounded-lg max-h-56 overflow-y-auto">
                {searchResults.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-gray-500">No matches found.</div>
                ) : (
                  searchResults.map((r) => (
                    <button
                      key={r.slug}
                      onClick={() => setActiveSlug(r.slug)}
                      className="w-full text-left px-3 py-2 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
                    >
                      <div className="text-xs font-medium text-gray-700">{r.title}</div>
                      <div className="text-[11px] text-gray-500 mt-0.5">{r.snippet || 'Match found in this document.'}</div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <h3 className="font-semibold">{docTitle || 'Documentation'}</h3>
              <p className="text-xs text-gray-500 mt-1">
                Complete guides for using the app, configuring features, and maximizing productivity.
              </p>
            </div>
            <button
              onClick={downloadPDF}
              disabled={downloading || !doc}
              className="flex items-center gap-2 px-3 py-2 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 text-white text-xs rounded font-medium transition"
              title="Download as PDF"
            >
              <Download size={14} />
              {downloading ? 'Generating...' : 'PDF'}
            </button>
          </div>

          {loadingDoc ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader size={16} className="animate-spin" /> Loading documentation...
          </div>
        ) : (
          <div className="overflow-y-auto max-h-[calc(100vh-300px)]">
            <div ref={contentRef} className="prose prose-sm w-full min-w-0 max-w-none overflow-hidden
            prose-h1:text-2xl prose-h1:font-bold prose-h1:text-gray-900 prose-h1:mb-4 prose-h1:mt-6 prose-h1:border-b prose-h1:pb-3 prose-h1:break-words
            prose-h2:text-xl prose-h2:font-bold prose-h2:text-gray-800 prose-h2:mb-3 prose-h2:mt-5 prose-h2:break-words
            prose-h3:text-lg prose-h3:font-semibold prose-h3:text-gray-700 prose-h3:mb-2 prose-h3:mt-4 prose-h3:break-words
            prose-p:text-gray-700 prose-p:leading-relaxed prose-p:mb-4 prose-p:break-words
            prose-a:text-brand-600 prose-a:hover:text-brand-700 prose-a:underline prose-a:break-words
            prose-strong:font-semibold prose-strong:text-gray-900
            prose-em:italic prose-em:text-gray-600
            prose-code:bg-gray-100 prose-code:text-red-600 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:break-words prose-code:whitespace-pre-wrap
            prose-pre:bg-gray-900 prose-pre:text-green-300 prose-pre:border prose-pre:border-gray-800 prose-pre:rounded-lg prose-pre:overflow-x-auto prose-pre:w-full
            prose-ol:list-decimal prose-ol:ml-5 prose-ol:space-y-2
            prose-ul:list-disc prose-ul:ml-5 prose-ul:space-y-2
            prose-li:text-gray-700 prose-li:leading-relaxed prose-li:break-words
            prose-blockquote:border-l-4 prose-blockquote:border-brand-500 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-600 prose-blockquote:my-4 prose-blockquote:break-words
            prose-table:border-collapse prose-table:w-full prose-table:my-4 prose-table:overflow-x-auto
            prose-thead:bg-gray-100
            prose-tr:border-b prose-tr:border-gray-200
            prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-gray-900 prose-th:break-words
            prose-td:px-4 prose-td:py-2 prose-td:text-gray-700 prose-td:break-words
            prose-td:border prose-td:border-gray-200
            prose-img:rounded-lg prose-img:shadow-md prose-img:my-4 prose-img:max-w-full
            prose-hr:border-gray-300 prose-hr:my-6
            bg-white p-6 rounded">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ node, ...props }) => <h1 id={slugify(textFromChildren(props.children))} {...props} />,
                h2: ({ node, ...props }) => <h2 id={slugify(textFromChildren(props.children))} {...props} />,
                h3: ({ node, ...props }) => <h3 id={slugify(textFromChildren(props.children))} {...props} />,
                code: ({ node, inline, className, children, ...props }) => {
                  if (inline) {
                    return <code className="px-1 py-0.5 rounded bg-gray-100 text-red-600 font-mono text-sm" {...props}>{children}</code>
                  }
                  return <DocCodeBlock className={className}>{children}</DocCodeBlock>
                },
                table: ({ node, ...props }) => (
                  <div className="overflow-x-auto my-4">
                    <table className="border-collapse w-full border border-gray-300" {...props} />
                  </div>
                ),
                thead: ({ node, ...props }) => (
                  <thead className="bg-gray-100" {...props} />
                ),
                th: ({ node, ...props }) => (
                  <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900" {...props} />
                ),
                td: ({ node, ...props }) => (
                  <td className="border border-gray-300 px-4 py-2 text-gray-700" {...props} />
                ),
                ul: ({ node, ...props }) => (
                  <ul className="list-disc ml-5 space-y-2 my-3" {...props} />
                ),
                ol: ({ node, ...props }) => (
                  <ol className="list-decimal ml-5 space-y-2 my-3" {...props} />
                ),
                li: ({ node, ...props }) => (
                  <li className="text-gray-700 leading-relaxed" {...props} />
                ),
                blockquote: ({ node, ...props }) => (
                  <blockquote className="border-l-4 border-brand-500 pl-4 italic text-gray-600 my-4 py-2" {...props} />
                ),
                hr: ({ node, ...props }) => (
                  <hr className="border-gray-300 my-6" {...props} />
                ),
              }}
            >
              {doc || '# Documentation unavailable'}
            </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
    </div>
  )
}

function DocCodeBlock({ children, className = '' }) {
  const [copied, setCopied] = useState(false)
  const code = String(children || '').replace(/\n$/, '')
  const lang = (className || '').replace('language-', '').trim() || 'text'

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch (_) {
      setCopied(false)
    }
  }

  return (
    <div className="not-prose rounded-lg overflow-hidden border border-gray-200 my-3 w-full min-w-0">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 text-gray-100 text-[11px]">
        <span className="uppercase tracking-wide opacity-80">{lang}</span>
        <button onClick={copy} className="px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-white">
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="m-0 p-3 overflow-x-auto bg-gray-900 text-green-300 text-xs leading-relaxed w-full whitespace-pre-wrap break-words">
        <code className="break-words">{code}</code>
      </pre>
    </div>
  )
}

/* ------------------------- Security ------------------------ */
function SecurityTab() {
  const [commands, setCommands] = useState([])
  const [keywords, setKeywords] = useState([])
  const [newCmd, setNewCmd] = useState('')
  const [newKw, setNewKw] = useState('')
  const [msg, setMsg] = useState(null)

  const load = async () => {
    try {
      const [c, k] = await Promise.all([
        api.get('/api/security/commands'),
        api.get('/api/security/keywords'),
      ])
      setCommands(c.data.commands || [])
      setKeywords(k.data.keywords || [])
    } catch (e) { /* ignore */ }
  }
  useEffect(() => { load() }, [])

  const addCmd = async () => {
    const cmd = newCmd.trim().toUpperCase()
    if (!cmd) return
    try {
      await api.post('/api/security/commands', { command: cmd, is_blocked: true })
      setNewCmd(''); setMsg({ type: 'success', text: `Blocked "${cmd}"` }); load()
    } catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
  }
  const toggle = async (row) => {
    try { await api.patch(`/api/security/commands/${row.id}`, { is_blocked: !row.is_blocked }); load() }
    catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
  }
  const delCmd = async (row) => {
    try { await api.delete(`/api/security/commands/${row.id}`); load() }
    catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
  }
  const addKw = async () => {
    const kw = newKw.trim()
    if (!kw) return
    const next = Array.from(new Set([...keywords, kw]))
    try { await api.post('/api/security/keywords', { keywords: next }); setNewKw(''); setKeywords(next) }
    catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
  }
  const delKw = async (kw) => {
    const next = keywords.filter((k) => k !== kw)
    try { await api.post('/api/security/keywords', { keywords: next }); setKeywords(next) }
    catch (e) { setMsg({ type: 'error', text: handleApiError(e).message }) }
  }

  return (
    <div className="space-y-4 w-full">
      <Banner msg={msg} />
      <p className="text-xs text-gray-500">
        Generated SQL is always restricted to read-only SELECT. Add extra restricted
        commands or keywords here — any query containing them is blocked before execution.
        (Admin only.)
      </p>

      <div className="card space-y-3">
        <h3 className="font-medium text-sm">Restricted SQL commands</h3>
        <div className="flex gap-2">
          <input className="input text-sm" placeholder="e.g. GRANT" value={newCmd}
            onChange={(e) => setNewCmd(e.target.value)} />
          <button onClick={addCmd} className="btn-primary text-sm whitespace-nowrap">Block command</button>
        </div>
        <div className="space-y-1">
          {commands.map((c) => (
            <div key={c.id} className="flex items-center justify-between text-sm border-b border-gray-100 py-1.5">
              <span className="font-mono">{c.command}</span>
              <div className="flex items-center gap-3">
                <button onClick={() => toggle(c)}
                  className={`px-2 py-0.5 rounded-full text-xs ${c.is_blocked ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'}`}>
                  {c.is_blocked ? 'Blocked' : 'Allowed'}
                </button>
                <button onClick={() => delCmd(c)} className="text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
          {commands.length === 0 && <p className="text-xs text-gray-400">No restricted commands configured.</p>}
        </div>
      </div>

      <div className="card space-y-3">
        <h3 className="font-medium text-sm">Restricted keywords</h3>
        <div className="flex gap-2">
          <input className="input text-sm" placeholder="e.g. password" value={newKw}
            onChange={(e) => setNewKw(e.target.value)} />
          <button onClick={addKw} className="btn-primary text-sm whitespace-nowrap">Add keyword</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {keywords.map((k) => (
            <span key={k} className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
              {k}
              <button onClick={() => delKw(k)} className="text-gray-400 hover:text-red-500"><X size={12} /></button>
            </span>
          ))}
          {keywords.length === 0 && <p className="text-xs text-gray-400">No restricted keywords.</p>}
        </div>
      </div>
    </div>
  )
}

/* ----------------------- Audio Settings ----------------------- */
function AudioTab() {
  const [settings, setSettings] = useState({
    voiceGender: 'female',
    pitch: 1,
    rate: 1,
    volume: 1,
    voiceInputLanguage: 'english',
    sttModel: 'whisper', // Speech-to-Text model: whisper, elevenlabs, local
    ttsProvider: 'google-cloud', // Text-to-Speech provider
  })
  const [msg, setMsg] = useState(null)
  const [isTrainingVoice, setIsTrainingVoice] = useState(false)
  const [isRecordingTraining, setIsRecordingTraining] = useState(false)
  const [trainingProgress, setTrainingProgress] = useState(0)
  const mediaRecorderRef = React.useRef(null)
  const audioChunksRef = React.useRef([])
  const streamRef = React.useRef(null)

  const VOICE_INPUT_LANGUAGES = [
    { code: 'english', label: 'English' },
    { code: 'igbo', label: 'Igbo' },
    { code: 'hausa', label: 'Hausa' },
    { code: 'yoruba', label: 'Yoruba' },
    { code: 'pidgin', label: 'Nigerian Pidgin' },
  ]

  const STT_MODELS = [
    {
      id: 'naijavox',
      name: 'NaijaVox-2.0 (Nigerian Languages)',
      description: '🇳🇬 Best for Nigerian languages: Yoruba, Hausa, Igbo, Nigerian Pidgin, Nigerian English. Built on Whisper-large-v3 with LoRA fine-tuning. 22.58% average WER.',
      status: 'recommended'
    },
    {
      id: 'whisper',
      name: 'OpenAI Whisper (Large-v3)',
      description: 'Excellent open-weights multilingual transcription. Natively supports Hausa, Yoruba, Igbo, and English with robust low-resource accent handling.',
      status: 'recommended'
    },
    {
      id: 'elevenlabs',
      name: 'ElevenLabs Scribe API',
      description: 'Dedicated high-accuracy processing with diarization explicitly optimized for African languages like Igbo and Hausa.',
      status: 'premium'
    },
    {
      id: 'local',
      name: 'Local/Regional Models',
      description: 'Specialized developer toolkits like N-ATLaS-LLM custom-tuned on local phonetic and contextual speech data.',
      status: 'experimental'
    }
  ]

  const TTS_PROVIDERS = [
    {
      id: 'google-cloud',
      name: 'Google Cloud Text-to-Speech',
      description: 'Premium quality, best support for Nigerian languages (Igbo, Yoruba, Hausa). Requires API key setup.',
      status: 'recommended'
    },
    {
      id: 'elevenlabs-tts',
      name: 'ElevenLabs TTS',
      description: 'High-quality synthetic voices with voice cloning. Supports multilingual output.',
      status: 'premium'
    },
    {
      id: 'azure-tts',
      name: 'Microsoft Azure Text-to-Speech',
      description: 'Enterprise-grade synthesis with diverse voice options.',
      status: 'premium'
    },
    {
      id: 'browser',
      name: 'Browser Native TTS',
      description: 'Free, no API required, but limited to English only.',
      status: 'limited'
    }
  ]

  // Language-specific test messages
  const TEST_MESSAGES = {
    english: 'Welcome, how are you doing today',
    igbo: 'Nnoo, kedu ka ị na-eme taa',
    hausa: 'Maraba, yaya kuke ji taa',
    yoruba: 'Kaabo, bawo lo n se loni'
  }

  // Load settings from API on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const { data } = await api.get('/api/settings/user')
        if (data.settings && data.settings.audio_settings) {
          setSettings(data.settings.audio_settings)
        }
      } catch (e) {
        console.error('Failed to load audio settings:', e)
        // Fallback to defaults if API fails
      }
    }
    loadSettings()
  }, [])

  const handleChange = async (key, value) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    try {
      await api.post('/api/settings/user', { audio_settings: newSettings })
      setMsg({ type: 'success', text: 'Audio settings saved.' })
      setTimeout(() => setMsg(null), 2000)
    } catch (e) {
      console.error('Failed to save settings:', e)
      setMsg({ type: 'error', text: 'Failed to save settings' })
    }
  }

  const testVoice = async () => {
    const language = settings.voiceInputLanguage || 'english'
    const testMessage = TEST_MESSAGES[language] || TEST_MESSAGES.english
    
    // For African languages, try backend TTS first
    if (language !== 'english') {
      try {
        const { data } = await api.post('/api/chat/synthesize-speech', {
          text: testMessage,
          language: language,
          gender: settings.voiceGender === 'male' ? 'MALE' : settings.voiceGender === 'female' ? 'FEMALE' : 'NEUTRAL',
          tts_provider: settings.ttsProvider || 'google-cloud'  // Use user's selected provider
        })
        
        // Check if backend TTS succeeded
        if (data.success && data.audio) {
          // Play server-generated audio
          const audio = new Audio(data.audio)
          audio.volume = parseFloat(settings.volume || 0.5)
          await audio.play()
          setMsg({ 
            type: 'success', 
            text: `Playing ${language.charAt(0).toUpperCase() + language.slice(1)} voice via ${data.provider || 'server TTS'}.` 
          })
          setTimeout(() => setMsg(null), 3000)
          return
        }
        
        // Backend returned error - show setup message for non-English
        if (!data.success) {
          setMsg({ 
            type: 'error', 
            text: `${language.charAt(0).toUpperCase() + language.slice(1)} voice requires server-side TTS. ${data.setup_guide || 'Configure a Text-to-Speech provider in the Audio settings.'}` 
          })
          setTimeout(() => setMsg(null), 6000)
          return
        }
      } catch (err) {
        console.warn('Backend TTS unavailable:', err)
        // For non-English, don't fall back to browser TTS which will spell out characters
        setMsg({ 
          type: 'error', 
          text: `Cannot test ${language.charAt(0).toUpperCase() + language.slice(1)} voice: TTS service not working. Check your configuration.` 
        })
        setTimeout(() => setMsg(null), 6000)
        return
      }
    }
    
    // English: Use browser Web Speech Synthesis API
    const synth = window.speechSynthesis
    const utterance = new SpeechSynthesisUtterance(testMessage)
    utterance.lang = 'en-US'
    
    // Set voice gender preference
    const voices = synth.getVoices()
    if (voices && voices.length > 0) {
      let selectedVoice = null
      
      // Filter by gender preference if available
      if (settings.voiceGender === 'male') {
        let maleVoices = voices.filter((v) => 
          v.name.toLowerCase().includes('male') || 
          v.name.toLowerCase().includes('man')
        )
        selectedVoice = maleVoices[0]
      } else if (settings.voiceGender === 'female') {
        let femaleVoices = voices.filter((v) => 
          v.name.toLowerCase().includes('female') || 
          v.name.toLowerCase().includes('woman')
        )
        selectedVoice = femaleVoices[0]
      }
      
      // Final fallback to default voice
      utterance.voice = selectedVoice || voices.find((v) => v.default) || voices[0]
    }
    
    utterance.pitch = parseFloat(settings.pitch || 1)
    utterance.rate = parseFloat(settings.rate || 1)
    utterance.volume = parseFloat(settings.volume || 0.5)
    
    synth.cancel()
    synth.speak(utterance)
    
    setMsg({ 
      type: 'success', 
      text: `Testing English voice using browser TTS.` 
    })
    setTimeout(() => setMsg(null), 3000)
  }

  const startVoiceTraining = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      audioChunksRef.current = []
      
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }
      
      mediaRecorder.onstop = async () => {
        await uploadVoiceTraining()
        stream.getTracks().forEach(track => track.stop())
      }
      
      mediaRecorder.start()
      setIsRecordingTraining(true)
      setMsg({ type: 'success', text: 'Recording voice sample... Please speak clearly.' })
    } catch (error) {
      console.error('Microphone error:', error)
      setMsg({ type: 'error', text: 'Unable to access microphone. Check permissions.' })
    }
  }

  const stopVoiceTraining = () => {
    if (mediaRecorderRef.current && isRecordingTraining) {
      mediaRecorderRef.current.stop()
      setIsRecordingTraining(false)
    }
  }

  const uploadVoiceTraining = async () => {
    try {
      setTrainingProgress(25)
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
      
      const formData = new FormData()
      formData.append('voice_sample', audioBlob, 'training.wav')
      formData.append('sample_text', 'This is my voice sample for authentication')
      
      setTrainingProgress(50)
      const { data } = await api.post('/api/chat/train-user-voice', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      setTrainingProgress(75)
      
      if (data.success) {
        setTrainingProgress(100)
        setMsg({ type: 'success', text: `Voice training successful! ${data.samples_count} samples enrolled.` })
        setTimeout(() => setTrainingProgress(0), 2000)
      } else {
        setMsg({ type: 'error', text: `Training failed: ${data.error}` })
      }
    } catch (error) {
      console.error('Voice training upload error:', error)
      setMsg({ type: 'error', text: `Upload failed: ${error.response?.data?.error || error.message}` })
      setTrainingProgress(0)
    }
  }

  return (
    <div className="card w-full space-y-6">
      <Banner msg={msg} />
      
      <div>
        <h3 className="font-medium text-sm mb-4">Response Audio Settings</h3>
        <p className="text-xs text-gray-400 mb-4">Customize how the AI responses are spoken to you.</p>
      </div>

      {/* Voice Gender */}
      <div>
        <label className="text-sm text-gray-600">Voice Gender</label>
        <div className="flex gap-2 mt-2">
          {['female', 'male', 'neutral'].map((gender) => (
            <button
              key={gender}
              onClick={() => handleChange('voiceGender', gender)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                settings.voiceGender === gender
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {gender.charAt(0).toUpperCase() + gender.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Pitch/Intonation */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm text-gray-600">Pitch / Intonation</label>
          <span className="text-xs text-gray-400">{settings.pitch.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={settings.pitch}
          onChange={(e) => handleChange('pitch', parseFloat(e.target.value))}
          className="w-full"
        />
        <p className="text-xs text-gray-400 mt-1">Lower = deeper, Higher = higher-pitched</p>
      </div>

      {/* Rate/Tempo/Speed */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm text-gray-600">Speed / Tempo</label>
          <span className="text-xs text-gray-400">{settings.rate.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={settings.rate}
          onChange={(e) => handleChange('rate', parseFloat(e.target.value))}
          className="w-full"
        />
        <p className="text-xs text-gray-400 mt-1">Lower = slower, Higher = faster</p>
      </div>

      {/* Volume */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm text-gray-600">Volume</label>
          <span className="text-xs text-gray-400">{Math.round(settings.volume * 100)}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={settings.volume}
          onChange={(e) => handleChange('volume', parseFloat(e.target.value))}
          className="w-full"
        />
      </div>

      {/* Voice Input Language */}
      <div>
        <label className="text-sm text-gray-600 mb-2 block">Voice Input Language</label>
        <p className="text-xs text-gray-400 mb-3">Select the language for voice input. Text will be automatically translated to English before processing.</p>
        <select
          value={settings.voiceInputLanguage || 'english'}
          onChange={(e) => handleChange('voiceInputLanguage', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          {VOICE_INPUT_LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      {/* Speech-to-Text (STT) Model Selection */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="font-semibold text-sm text-gray-800 mb-3 flex items-center gap-2">
          🎙️ Speech-to-Text Model
        </h4>
        <p className="text-xs text-gray-400 mb-4">Choose which service to use for converting voice input to text. Different models optimize for different languages and accents.</p>
        
        <div className="space-y-3">
          {STT_MODELS.map((model) => (
            <div
              key={model.id}
              onClick={() => handleChange('sttModel', model.id)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                settings.sttModel === model.id
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="sttModel"
                    value={model.id}
                    checked={settings.sttModel === model.id}
                    onChange={() => handleChange('sttModel', model.id)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-medium text-sm text-gray-900">{model.name}</p>
                  </div>
                </div>
                <span className={`text-xs font-semibold px-2 py-1 rounded ${
                  model.status === 'recommended'
                    ? 'bg-green-100 text-green-700'
                    : model.status === 'premium'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {model.status === 'recommended' ? '✓ Recommended' : model.status === 'premium' ? '⭐ Premium' : '🧪 Experimental'}
                </span>
              </div>
              <p className="text-xs text-gray-600 ml-6">{model.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800">
            <strong>Current selection:</strong> {STT_MODELS.find(m => m.id === settings.sttModel)?.name || 'OpenAI Whisper'} will be used for all voice input transcription.
          </p>
        </div>
      </div>

      {/* Text-to-Speech (TTS) Provider Selection */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="font-semibold text-sm text-gray-800 mb-3 flex items-center gap-2">
          🔊 Text-to-Speech Provider
        </h4>
        <p className="text-xs text-gray-400 mb-4">Choose which service to use for converting text to speech. Different providers have different voice quality and language support.</p>
        
        <div className="space-y-3">
          {TTS_PROVIDERS.map((provider) => (
            <div
              key={provider.id}
              onClick={() => handleChange('ttsProvider', provider.id)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                settings.ttsProvider === provider.id
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="ttsProvider"
                    value={provider.id}
                    checked={settings.ttsProvider === provider.id}
                    onChange={() => handleChange('ttsProvider', provider.id)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-medium text-sm text-gray-900">{provider.name}</p>
                  </div>
                </div>
                <span className={`text-xs font-semibold px-2 py-1 rounded ${
                  provider.status === 'recommended'
                    ? 'bg-green-100 text-green-700'
                    : provider.status === 'premium'
                    ? 'bg-blue-100 text-blue-700'
                    : provider.status === 'limited'
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {provider.status === 'recommended' ? '✓ Recommended' : provider.status === 'premium' ? '⭐ Premium' : provider.status === 'limited' ? '⚠️ Limited' : '🧪 Experimental'}
                </span>
              </div>
              <p className="text-xs text-gray-600 ml-6">{provider.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800">
            <strong>Current selection:</strong> {TTS_PROVIDERS.find(p => p.id === settings.ttsProvider)?.name || 'Google Cloud Text-to-Speech'} will be used for text-to-speech synthesis.
          </p>
        </div>
      </div>

      {/* Test Button */}
      <div>
        <button
          onClick={testVoice}
          className="btn-primary flex items-center gap-2"
        >
          <Volume2 size={16} /> Test Audio ({settings.voiceInputLanguage || 'english'})
        </button>
      </div>

      {/* Voice Training Section */}
      <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
        <h4 className="font-semibold text-sm text-purple-900 mb-3 flex items-center gap-2">
          <Mic size={16} /> Voice Training
        </h4>
        <p className="text-xs text-purple-800 mb-3">
          Train the AI to recognize your voice. Record a few voice samples so the AI can identify when you're speaking in multi-person conversations.
        </p>
        
        {!isRecordingTraining ? (
          <button
            onClick={startVoiceTraining}
            disabled={isTrainingVoice}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-2"
          >
            <Mic size={16} /> Record Voice Sample
          </button>
        ) : (
          <button
            onClick={stopVoiceTraining}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-2 animate-pulse"
          >
            <Square size={16} /> Stop Recording
          </button>
        )}
        
        {trainingProgress > 0 && (
          <div className="mt-3 space-y-1">
            <div className="flex justify-between text-xs text-purple-700">
              <span>Processing...</span>
              <span>{trainingProgress}%</span>
            </div>
            <div className="w-full bg-purple-200 rounded-full h-2 overflow-hidden">
              <div className="bg-purple-600 h-full transition-all" style={{ width: `${trainingProgress}%` }}></div>
            </div>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
        <p className="text-xs text-blue-700">
          💡 <strong>Tip:</strong> Click "Test Audio" to hear how your settings sound before using them in chat. Voice input in non-English languages will be automatically translated to English before processing.
        </p>
      </div>
    </div>
  )
}

/* ------------------------- Conversations ------------------------ */
/* --------------------------- Audit Logs ---------------------- */
function AuditLogsTab() {
  const [logs, setLogs] = useState([])
  const [selected, setSelected] = useState(null)
  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  
  // Filters
  const [showApiOnly, setShowApiOnly] = useState(false)
  const [showUIOnly, setShowUIOnly] = useState(false)
  const [showSuccessOnly, setShowSuccessOnly] = useState(false)
  const [conversationFilter, setConversationFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('limit', '80')
      
      if (showApiOnly) params.append('is_api', 'true')
      if (showUIOnly) params.append('is_api', 'false')
      if (showSuccessOnly) params.append('success', 'true')
      if (conversationFilter.trim()) params.append('conversation_id', conversationFilter.trim())
      if (searchTerm.trim()) params.append('search', searchTerm.trim())
      
      const { data } = await api.get(`/api/cache/audit-logs?${params.toString()}`)
      setLogs(data.items || [])
      if (data.total > 0) {
        setMsg({ type: 'info', text: `Showing ${data.items?.length || 0} of ${data.total} logs` })
      }
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [showApiOnly, showUIOnly, showSuccessOnly, conversationFilter, searchTerm])

  const view = async (id) => {
    try {
      const { data } = await api.get(`/api/cache/audit-logs/${id}`)
      setSelected(data.item || null)
    } catch (e) {
      setMsg({ type: 'error', text: handleApiError(e).message })
    }
  }

  return (
    <div className="space-y-4">
      <Banner msg={msg} />
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-sm">Audit logs</h3>
          <button onClick={load} className="btn-secondary text-xs">Refresh</button>
        </div>
        
        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4 pb-4 border-b border-gray-200">
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input type="checkbox" checked={showApiOnly} onChange={(e) => setShowApiOnly(e.target.checked)} className="rounded" />
            <span>API requests only</span>
          </label>
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input type="checkbox" checked={showUIOnly} onChange={(e) => setShowUIOnly(e.target.checked)} className="rounded" />
            <span>UI requests only</span>
          </label>
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input type="checkbox" checked={showSuccessOnly} onChange={(e) => setShowSuccessOnly(e.target.checked)} className="rounded" />
            <span>Successful only</span>
          </label>
          <input 
            type="text" 
            placeholder="Conversation ID" 
            value={conversationFilter} 
            onChange={(e) => setConversationFilter(e.target.value)}
            className="text-xs px-2 py-1 border border-gray-300 rounded"
          />
          <input 
            type="text" 
            placeholder="Search prompt..." 
            value={searchTerm} 
            onChange={(e) => setSearchTerm(e.target.value)}
            className="text-xs px-2 py-1 border border-gray-300 rounded lg:col-span-3"
          />
        </div>

        {loading ? <Loader className="animate-spin text-gray-400" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Prompt</th>
                  <th className="px-3 py-2">Rewritten</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Token In/Out</th>
                  <th className="px-3 py-2">Cache Read</th>
                  <th className="px-3 py-2">SQL</th>
                  <th className="px-3 py-2">View</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((r) => (
                  <tr key={r.id} className="border-t border-gray-100">
                    <td className="px-3 py-1.5 text-gray-400 whitespace-nowrap">{r.created_at?.slice(0, 19).replace('T', ' ')}</td>
                    <td className="px-3 py-1.5 whitespace-nowrap">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${r.is_api ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                        {r.is_api ? 'API' : 'UI'}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 max-w-[220px] truncate">{r.user_query}</td>
                    <td className="px-3 py-1.5 max-w-[220px] truncate text-brand-600">{r.rewritten_query}</td>
                    <td className="px-3 py-1.5 whitespace-nowrap">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${r.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {r.success ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="px-3 py-1.5">{r.token_input || 0} / {r.token_output || 0}</td>
                    <td className="px-3 py-1.5">{r.cache_read_tokens || 0}</td>
                    <td className="px-3 py-1.5 max-w-[200px] truncate">{r.generated_sql}</td>
                    <td className="px-3 py-1.5">
                      <button onClick={() => view(r.id)} className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700"><Eye size={13} /> View</button>
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && <tr><td colSpan={9} className="px-3 py-3 text-gray-400">No audit logs matching filters.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl p-4 space-y-3 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-sm">Audit log #{selected.id}</h3>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700"><X size={16} /></button>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Prompt</p>
              <pre className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">{selected.user_query}</pre>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Rewritten prompt</p>
              <pre className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">{selected.rewritten_query}</pre>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Context cache</p>
              <pre className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">{JSON.stringify(selected.detail?.context_cache || {}, null, 2)}</pre>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <Metric label="Token input" value={selected.detail?.token_input || 0} />
              <Metric label="Token output" value={selected.detail?.token_output || 0} />
              <Metric label="Cache created" value={selected.detail?.cache_creation_tokens || 0} />
              <Metric label="Cache read/saved" value={selected.detail?.cache_read_tokens || 0} />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Response generated</p>
              <pre className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">{selected.detail?.response_text || ''}</pre>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">SQL generated</p>
              <pre className="bg-gray-900 text-green-300 rounded p-2 text-xs whitespace-pre-wrap">{selected.generated_sql || ''}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* --------------------------- Cache/Metrics ---------------------- */
function CacheTab() {
  const [metrics, setMetrics] = useState(null)
  const [recent, setRecent] = useState([])
  const [restarting, setRestarting] = useState(false)
  const load = async () => {
    const [m, r] = await Promise.all([api.get('/api/cache/metrics'), api.get('/api/cache/recent?limit=30')])
    setMetrics(m.data.metrics); setRecent(r.data.items || [])
  }
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t) }, [])

  const handleRestartServer = async () => {
    const result = await Swal.fire({
      title: 'Restart Server?',
      text: 'The server will restart and temporarily disconnect. This should take 2-3 seconds.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Restart',
      cancelButtonText: 'Cancel',
      confirmButtonColor: '#f59e0b',
    })

    if (!result.isConfirmed) return

    setRestarting(true)
    try {
      const response = await api.post('/api/system/restart', {})
      const { port, restart_in_seconds } = response.data

      await Swal.fire({
        title: 'Restarting...',
        text: `Server is restarting. Will reconnect in ~${restart_in_seconds} seconds...`,
        icon: 'info',
        didOpen: async () => {
          // Wait for server to restart and reconnect
          let connected = false
          let attempts = 0
          const maxAttempts = 10

          while (!connected && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000))
            try {
              await api.get('/api/health')
              connected = true
            } catch (e) {
              attempts++
            }
          }

          if (connected) {
            await Swal.fire({
              title: 'Reconnected!',
              text: 'Server has restarted successfully.',
              icon: 'success',
              timer: 2000,
            })
            load() // Refresh metrics
          } else {
            await Swal.fire({
              title: 'Connection Timeout',
              text: 'Could not reconnect to server. Please refresh the page.',
              icon: 'error',
            })
          }
        },
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
      })
    } catch (error) {
      await Swal.fire({
        title: 'Error',
        text: `Failed to restart server: ${error.message}`,
        icon: 'error',
      })
    } finally {
      setRestarting(false)
    }
  }

  if (!metrics) return <Loader className="animate-spin text-gray-400" />
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Queries (24h)" value={metrics.total_queries} />
        <Metric label="Success rate" value={`${metrics.success_rate}%`} />
        <Metric label="Avg latency" value={`${metrics.avg_duration_ms} ms`} />
        <Metric label="Active LLM" value={metrics.active_llm} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Metric label="Input tokens" value={metrics.tokens?.input || 0} />
        <Metric label="Output tokens" value={metrics.tokens?.output || 0} />
        <Metric label="Cache create" value={metrics.tokens?.cache_creation || 0} />
        <Metric label="Cache read" value={metrics.tokens?.cache_read || 0} />
        <Metric label="Tokens saved" value={metrics.tokens?.saved_by_cache || 0} />
      </div>
      <div className="card">
        <h3 className="font-medium text-sm mb-2">Recent queries + token usage</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr><th className="px-3 py-2">Time</th><th className="px-3 py-2">Prompt</th><th className="px-3 py-2">Rewritten</th><th className="px-3 py-2">Rows</th><th className="px-3 py-2">Input</th><th className="px-3 py-2">Output</th><th className="px-3 py-2">Cache read</th><th className="px-3 py-2">OK</th></tr>
            </thead>
            <tbody>
              {recent.map((r) => (
                <tr key={r.id} className="border-t border-gray-100">
                  <td className="px-3 py-1.5 text-gray-400 whitespace-nowrap">{r.created_at?.slice(11, 19)}</td>
                  <td className="px-3 py-1.5 max-w-[200px] truncate">{r.user_query}</td>
                  <td className="px-3 py-1.5 max-w-[200px] truncate text-brand-600">{r.rewritten_query}</td>
                  <td className="px-3 py-1.5">{r.row_count}</td>
                  <td className="px-3 py-1.5">{r.token_input || 0}</td>
                  <td className="px-3 py-1.5">{r.token_output || 0}</td>
                  <td className="px-3 py-1.5">{r.cache_read_tokens || 0}</td>
                  <td className="px-3 py-1.5">{r.success ? '✅' : '❌'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Restart Server Section */}
      <div className="card border-l-4 border-l-amber-400 bg-amber-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-sm text-amber-900">Server Management</h3>
            <p className="text-xs text-amber-700 mt-1">Restart the Flask backend server. It will reconnect within 2-3 seconds.</p>
          </div>
          <button 
            onClick={handleRestartServer}
            disabled={restarting}
            className="btn-primary flex items-center gap-2 whitespace-nowrap bg-amber-600 hover:bg-amber-700 disabled:opacity-50"
          >
            {restarting ? (
              <>
                <Loader size={16} className="animate-spin" /> Restarting...
              </>
            ) : (
              <>
                <RefreshCw size={16} /> Restart Server
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ======================== TOKEN TESTER TAB ========================
function TokenTesterTab() {
  const [token, setToken] = useState('')
  const [rawClaims, setRawClaims] = useState(null)
  const [mappedClaims, setMappedClaims] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [displayTab, setDisplayTab] = useState('raw')  // raw or mapped
  const [showExpiryModifier, setShowExpiryModifier] = useState(false)
  const [expiryAdjustment, setExpiryAdjustment] = useState(24)
  const [modifyingToken, setModifyingToken] = useState(false)
  const [newTokenFromModify, setNewTokenFromModify] = useState(null)

  const decodeToken = async () => {
    if (!token.trim()) {
      setError('Please paste a JWT token')
      return
    }

    setLoading(true)
    setError('')
    setRawClaims(null)
    setMappedClaims(null)
    setNewTokenFromModify(null)

    try {
      const response = await api.post('/api/settings/microservice/decode-token', {
        token: token.trim()
      })

      if (response.data.success) {
        setRawClaims(response.data.decoded_claims)
        setDisplayTab('raw')
      } else {
        setError(response.data.error || 'Failed to decode token')
      }
    } catch (e) {
      setError(handleApiError(e))
    } finally {
      setLoading(false)
    }
  }

  const verifyToken = async () => {
    if (!token.trim()) {
      setError('Please paste a JWT token')
      return
    }

    setLoading(true)
    setError('')
    setRawClaims(null)
    setMappedClaims(null)
    setNewTokenFromModify(null)

    try {
      const response = await api.post('/api/settings/microservice/verify-token', {
        token: token.trim()
      })

      if (response.data.success) {
        // Store raw token claims and mapped user context separately
        setRawClaims(response.data.raw_claims || {})
        setMappedClaims(response.data.user_context || {})
        setDisplayTab('raw')
      } else {
        setError(response.data.error || 'Token verification failed')
      }
    } catch (e) {
      setError(handleApiError(e))
    } finally {
      setLoading(false)
    }
  }

  const modifyTokenExpiry = async () => {
    if (!token.trim()) {
      setError('Please paste a JWT token')
      return
    }

    if (expiryAdjustment === 0) {
      setError('Adjustment must be non-zero')
      return
    }

    setModifyingToken(true)
    setError('')

    try {
      const response = await api.post('/api/settings/microservice/modify-token-expiry', {
        token: token.trim(),
        hours_adjustment: expiryAdjustment
      })

      if (response.data.success) {
        setNewTokenFromModify(response.data.new_token)
        setToken(response.data.new_token)
        setRawClaims(null)
        setMappedClaims(null)
        Swal.fire('Success!', response.data.message, 'success')
        // Auto-decode the new token to show updated expiry
        setTimeout(() => verifyToken(), 500)
      } else {
        setError(response.data.error || 'Failed to modify token')
      }
    } catch (e) {
      // Handle 501 Not Implemented (RS256 algorithm not supported for modification)
      if (e.response?.status === 501) {
        const errorData = e.response?.data
        const message = errorData?.error || 'This operation is not supported for your authentication algorithm'
        const hint = errorData?.hint || 'Token expiry modification requires symmetric algorithms like HS256'
        setError(`${message}. ${hint}`)
      } else {
        setError(handleApiError(e))
      }
    } finally {
      setModifyingToken(false)
      setShowExpiryModifier(false)
    }
  }

  const copyToClipboard = (data) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    Swal.fire('Copied!', 'Claims copied to clipboard', 'success')
  }

  const copyToken = (tokenToCopy) => {
    navigator.clipboard.writeText(tokenToCopy)
    Swal.fire('Copied!', 'Token copied to clipboard', 'success')
  }

  // Helper to format ISO datetime string
  const formatDateTime = (isoString) => {
    try {
      const date = new Date(isoString)
      return date.toLocaleString()
    } catch {
      return isoString
    }
  }

  // Helper to get expiry info from raw claims
  const getExpiryInfo = () => {
    if (!rawClaims?.exp) return null
    const expDate = new Date(rawClaims.exp * 1000)
    const now = new Date()
    const diffMs = expDate - now
    const diffHours = Math.round(diffMs / (1000 * 60 * 60))
    const isExpired = diffMs < 0
    
    return {
      expDate: expDate.toISOString(),
      formatted: expDate.toLocaleString(),
      isExpired,
      diffHours,
      message: isExpired 
        ? `Expired ${Math.abs(diffHours)} hours ago`
        : `Expires in ${diffHours} hours`
    }
  }

  const expiryInfo = getExpiryInfo()

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <Shield size={16} /> Auth Token Inspector
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Paste your JWT token below to inspect its claims. Choose "Decode" to see raw claims or "Verify" to validate the signature.
        </p>

        <div className="space-y-3">
          <textarea
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste your JWT token here (e.g., eyJhbGciOiJSUzI1NiJ9...)"
            className="w-full h-24 p-3 border border-gray-200 rounded-lg font-mono text-xs resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
          />

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={decodeToken}
              disabled={loading || !token.trim()}
              className="btn btn-secondary flex items-center gap-2"
            >
              {loading ? <Loader size={14} className="animate-spin" /> : <Eye size={14} />}
              Decode (No Verify)
            </button>
            <button
              onClick={verifyToken}
              disabled={loading || !token.trim()}
              className="btn btn-primary flex items-center gap-2"
            >
              {loading ? <Loader size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              Verify Signature
            </button>
            {rawClaims && (
              <button
                onClick={() => setShowExpiryModifier(!showExpiryModifier)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Pencil size={14} />
                Modify Expiry
              </button>
            )}
            <button
              onClick={() => {
                setToken('')
                setRawClaims(null)
                setMappedClaims(null)
                setNewTokenFromModify(null)
                setError('')
              }}
              className="btn btn-secondary"
            >
              Clear
            </button>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
              {error}
            </div>
          )}

          {/* Expiry Modification Panel */}
          {showExpiryModifier && rawClaims && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
              <h4 className="font-medium text-sm text-blue-900 flex items-center gap-2">
                <Pencil size={14} /> Modify Token Expiry
              </h4>
              
              {expiryInfo && (
                <div className="p-2 bg-white rounded border border-blue-100 text-xs">
                  <div className="text-gray-600">
                    <span className={`font-semibold ${expiryInfo.isExpired ? 'text-red-600' : 'text-green-600'}`}>
                      {expiryInfo.message}
                    </span>
                  </div>
                  <div className="text-gray-500 mt-1">
                    {expiryInfo.formatted}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className="block text-xs font-medium text-gray-700">
                  Adjust expiry by (hours):
                </label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={expiryAdjustment}
                    onChange={(e) => setExpiryAdjustment(parseFloat(e.target.value) || 0)}
                    className="input w-24 text-sm"
                    placeholder="Hours"
                  />
                  <span className="text-xs text-gray-500">
                    {expiryAdjustment > 0 ? '+' : ''}{expiryAdjustment} hours
                  </span>
                </div>
                <p className="text-xs text-gray-500">
                  Positive values extend the expiry, negative values shorten it
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={modifyTokenExpiry}
                  disabled={modifyingToken || expiryAdjustment === 0}
                  className="btn btn-primary text-sm flex items-center justify-center gap-1"
                >
                  {modifyingToken ? <Loader size={14} className="animate-spin" /> : <Pencil size={14} />}
                  {modifyingToken ? 'Modifying...' : 'Modify & Re-sign'}
                </button>
                <button
                  onClick={() => setShowExpiryModifier(false)}
                  className="btn btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>

              {newTokenFromModify && (
                <div className="p-2 bg-green-50 border border-green-200 rounded text-xs space-y-2">
                  <div className="text-green-700 font-medium">✅ New token created with modified expiry</div>
                  <div className="bg-white p-2 rounded border border-green-100 font-mono text-xs overflow-x-auto max-h-16">
                    {newTokenFromModify.substring(0, 50)}...
                  </div>
                  <button
                    onClick={() => copyToken(newTokenFromModify)}
                    className="text-xs px-2 py-1 bg-green-100 hover:bg-green-200 rounded flex items-center gap-1"
                  >
                    <Copy size={12} /> Copy New Token
                  </button>
                </div>
              )}
            </div>
          )}

          {(rawClaims || mappedClaims) && (
            <div className="space-y-3">
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700 flex items-center gap-2">
                <CheckCircle2 size={14} />
                Token successfully decoded {mappedClaims ? '& verified' : ''}
              </div>

              {/* Tab selector for Raw vs Mapped Claims */}
              <div className="flex gap-2 border-b border-gray-200">
                {rawClaims && (
                  <button
                    onClick={() => setDisplayTab('raw')}
                    className={`px-3 py-2 text-xs font-medium border-b-2 ${
                      displayTab === 'raw'
                        ? 'border-brand-500 text-brand-700'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Raw Token Claims
                  </button>
                )}
                {mappedClaims && (
                  <button
                    onClick={() => setDisplayTab('mapped')}
                    className={`px-3 py-2 text-xs font-medium border-b-2 ${
                      displayTab === 'mapped'
                        ? 'border-brand-500 text-brand-700'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Mapped User Context & RBAC
                  </button>
                )}
              </div>

              {/* Raw Claims Display */}
              {displayTab === 'raw' && rawClaims && (
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="text-xs font-medium text-gray-700">
                      Raw Token Claims (scopes, userId, companyName, etc.)
                    </h4>
                    <button
                      onClick={() => copyToClipboard(rawClaims)}
                      className="text-xs px-2 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50 flex items-center gap-1"
                    >
                      <Copy size={12} /> Copy
                    </button>
                  </div>

                  <div className="bg-white rounded p-2 border border-gray-100 w-full overflow-x-auto max-w-full">
                    <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap break-all max-w-full min-w-0">
                      {JSON.stringify(rawClaims, null, 2)}
                    </pre>
                  </div>

                  {/* Display raw claim fields in friendly format */}
                  <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-2">
                    {rawClaims.userId && (
                      <div className="p-2 bg-blue-50 rounded border border-blue-100">
                        <div className="text-xs text-gray-500">User ID</div>
                        <div className="text-sm font-medium text-blue-700">{rawClaims.userId}</div>
                      </div>
                    )}
                    {rawClaims.scopes && (
                      <div className="p-2 bg-purple-50 rounded border border-purple-100">
                        <div className="text-xs text-gray-500">Scopes</div>
                        <div className="text-sm font-medium text-purple-700">
                          {Array.isArray(rawClaims.scopes) ? rawClaims.scopes.join(', ') : rawClaims.scopes}
                        </div>
                      </div>
                    )}
                    {rawClaims.companyName && (
                      <div className="p-2 bg-indigo-50 rounded border border-indigo-100">
                        <div className="text-xs text-gray-500">Company Name</div>
                        <div className="text-sm font-medium text-indigo-700 truncate">{rawClaims.companyName}</div>
                      </div>
                    )}
                    {rawClaims.parentCompanyCode && (
                      <div className="p-2 bg-cyan-50 rounded border border-cyan-100">
                        <div className="text-xs text-gray-500">Parent Company Code</div>
                        <div className="text-sm font-medium text-cyan-700">{rawClaims.parentCompanyCode}</div>
                      </div>
                    )}
                    {rawClaims.companyType && (
                      <div className="p-2 bg-orange-50 rounded border border-orange-100">
                        <div className="text-xs text-gray-500">Company Type</div>
                        <div className="text-sm font-medium text-orange-700">{rawClaims.companyType}</div>
                      </div>
                    )}
                    {rawClaims.parentCompanyName && (
                      <div className="p-2 bg-green-50 rounded border border-green-100">
                        <div className="text-xs text-gray-500">Parent Company</div>
                        <div className="text-sm font-medium text-green-700 truncate">{rawClaims.parentCompanyName}</div>
                      </div>
                    )}
                    {rawClaims.exp && (
                      <div className="p-2 bg-yellow-50 rounded border border-yellow-100">
                        <div className="text-xs text-gray-500">Expiry</div>
                        <div className="text-sm font-medium text-yellow-700">{formatDateTime(new Date(rawClaims.exp * 1000).toISOString())}</div>
                      </div>
                    )}
                    {rawClaims.iat && (
                      <div className="p-2 bg-red-50 rounded border border-red-100">
                        <div className="text-xs text-gray-500">Issued At</div>
                        <div className="text-sm font-medium text-red-700">{formatDateTime(new Date(rawClaims.iat * 1000).toISOString())}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Mapped Claims Display */}
              {displayTab === 'mapped' && mappedClaims && (
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="text-xs font-medium text-gray-700">
                      Mapped User Context & RBAC Info (internal app format)
                    </h4>
                    <button
                      onClick={() => copyToClipboard(mappedClaims)}
                      className="text-xs px-2 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50 flex items-center gap-1"
                    >
                      <Copy size={12} /> Copy
                    </button>
                  </div>

                  <div className="bg-white rounded p-2 border border-gray-100 w-full overflow-x-auto max-w-full">
                    <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap break-all max-w-full min-w-0">
                      {JSON.stringify(mappedClaims, null, 2)}
                    </pre>
                  </div>

                  {/* Display mapped claim fields in friendly format */}
                  <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-2">
                    {mappedClaims.email && (
                      <div className="p-2 bg-blue-50 rounded border border-blue-100">
                        <div className="text-xs text-gray-500">Email</div>
                        <div className="text-sm font-medium text-blue-700 truncate">{mappedClaims.email}</div>
                      </div>
                    )}
                    {mappedClaims.app_role && (
                      <div className="p-2 bg-purple-50 rounded border border-purple-100">
                        <div className="text-xs text-gray-500">App Role</div>
                        <div className="text-sm font-medium text-purple-700">{mappedClaims.app_role}</div>
                      </div>
                    )}
                    {mappedClaims.company_name && (
                      <div className="p-2 bg-indigo-50 rounded border border-indigo-100">
                        <div className="text-xs text-gray-500">Company Name</div>
                        <div className="text-sm font-medium text-indigo-700 truncate">{mappedClaims.company_name}</div>
                      </div>
                    )}
                    {mappedClaims.company_id && (
                      <div className="p-2 bg-cyan-50 rounded border border-cyan-100">
                        <div className="text-xs text-gray-500">Company ID (Resolved)</div>
                        <div className="text-sm font-medium text-cyan-700">{mappedClaims.company_id}</div>
                      </div>
                    )}
                    {mappedClaims.is_admin !== undefined && (
                      <div className="p-2 bg-yellow-50 rounded border border-yellow-100">
                        <div className="text-xs text-gray-500">Is Admin</div>
                        <div className="text-sm font-medium text-yellow-700">{mappedClaims.is_admin ? '✅ Yes' : '❌ No'}</div>
                      </div>
                    )}
                    {mappedClaims.is_company_admin !== undefined && (
                      <div className="p-2 bg-orange-50 rounded border border-orange-100">
                        <div className="text-xs text-gray-500">Is Company Admin</div>
                        <div className="text-sm font-medium text-orange-700">{mappedClaims.is_company_admin ? '✅ Yes' : '❌ No'}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card text-xs text-gray-600 space-y-2">
        <h4 className="font-medium">📝 How to use:</h4>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Decode:</strong> Shows token claims without verifying signature (for inspection)</li>
          <li><strong>Verify:</strong> Decodes AND validates signature using the public key in .env</li>
          <li><strong>Modify Expiry:</strong> Extend or shorten token expiry and get a new re-signed token</li>
          <li><strong>Raw Claims:</strong> Original token claims (userId, scopes, companyName, parentCompanyCode, exp, iat)</li>
          <li><strong>Mapped Context:</strong> How token is interpreted by this app (company_id resolved from DB, RBAC roles)</li>
          <li>App Role: CENTRAL_ADMIN role → Admin (full access), ADMIN + company → Company Admin (company-scoped), else → User</li>
        </ul>
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="card">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
    </div>
  )
}

/* ========================= SERVER LOGS TAB ========================= */
function ServerLogsTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [minutes, setMinutes] = useState(1)
  const [stats, setStats] = useState(null)
  const logsEndRef = useRef(null)

  const loadLogs = async (mins = minutes) => {
    setLoading(true)
    try {
      const { data } = await api.get(`/api/system/logs?minutes=${mins}`)
      setLogs(data.logs || [])
      setStats(data.stats)
    } catch (e) {
      console.error('Failed to load logs:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs(minutes)
  }, [minutes])

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  const downloadLogs = () => {
    const content = logs.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `server_logs_${new Date().toISOString().slice(0, 19)}.log`
    a.click()
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="card space-y-3">
        <h3 className="font-medium text-sm flex items-center gap-2">
          <Terminal size={16} /> Server Logs
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Show last (minutes)</label>
            <select 
              className="input text-sm" 
              value={minutes}
              onChange={(e) => setMinutes(parseInt(e.target.value))}
            >
              <option value={1}>Last 1 min</option>
              <option value={5}>Last 5 min</option>
              <option value={10}>Last 10 min</option>
              <option value={30}>Last 30 min</option>
              <option value={60}>Last 1 hour</option>
              <option value={120}>Last 2 hours</option>
            </select>
          </div>
          <button
            onClick={() => loadLogs(minutes)}
            disabled={loading}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            {loading ? <Loader size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
          <button
            onClick={downloadLogs}
            disabled={logs.length === 0}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            <Download size={14} /> Download
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-gray-200">
            <div className="text-center p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">Total Lines</div>
              <div className="font-semibold text-gray-700">{stats.total_lines.toLocaleString()}</div>
            </div>
            <div className="text-center p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">Recent Logs</div>
              <div className="font-semibold text-gray-700">{logs.length}</div>
            </div>
            <div className="text-center p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">File Size</div>
              <div className="font-semibold text-gray-700">{(stats.file_size / 1024).toFixed(1)} KB</div>
            </div>
            <div className="text-center p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">Last Modified</div>
              <div className="font-semibold text-gray-700 text-[11px]">
                {stats.last_modified ? new Date(stats.last_modified).toLocaleTimeString() : 'N/A'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Logs Display */}
      <div className="card">
        <h3 className="font-medium text-sm mb-2">Logs Output</h3>
        <div className="bg-gray-900 rounded-lg p-3 font-mono text-xs text-gray-100 overflow-auto max-h-96 border border-gray-700">
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-4">
              {loading ? 'Loading logs...' : 'No logs found for the selected time range'}
            </div>
          ) : (
            <>
              {logs.map((log, idx) => (
                <div key={idx} className="py-0.5 hover:bg-gray-800 px-2 rounded">
                  <span className="text-gray-400">{idx + 1}</span>
                  <span className="mx-2">│</span>
                  <span className="whitespace-pre-wrap break-words">{log}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-xs text-blue-900">
          <span className="font-semibold">💡 Tip:</span> Click the Refresh button to view the last {minutes} minutes of logs. Download logs to save them permanently.
        </p>
      </div>
    </div>
  )
}

