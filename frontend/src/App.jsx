import React from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { MessageSquare, Settings as SettingsIcon, Database, LogOut, Loader, Menu, Minus, Users } from 'lucide-react'
import Chat from './pages/Chat.jsx'
import Settings from './pages/Settings.jsx'
import MultiPersonChat from './pages/MultiPersonChat.jsx'
import Login from './pages/Login.jsx'
import { useAuth } from './contexts/AuthContext'
import { SidebarProvider, useSidebar } from './contexts/SidebarContext'

function Protected({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400"><Loader className="animate-spin" /></div>
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return children
}

function Shell({ children }) {
  const { user, logout, isCentralAdmin } = useAuth()
  const { sidebarOpen, setSidebarOpen } = useSidebar()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 px-3 sm:px-4 py-2.5 flex items-center gap-2 md:gap-4 flex-wrap">
        <button
          onClick={() => setSidebarOpen((prev) => !prev)}
          className="p-2 hover:bg-gray-100 rounded transition md:hidden"
          title={sidebarOpen ? 'Hide history' : 'Show history'}
        >
          {sidebarOpen ? <Minus size={16} className="text-gray-600" /> : <Menu size={16} className="text-gray-600" />}
        </button>
        <div className="flex items-center gap-2 font-semibold text-brand-700 min-w-0">
          <Database size={20} /> AI Assistant
          <span className="hidden sm:inline text-xs font-normal text-gray-400">AI Assistant</span>
        </div>
        <nav className="order-3 md:order-none w-full md:w-auto flex items-center gap-1 md:ml-4 overflow-x-auto pb-0.5 md:pb-0">
          <NavLink to="/chat" className={({ isActive }) =>
            `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${isActive ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
            <MessageSquare size={16} /> Chat
          </NavLink>
          <NavLink to="/multiperson-chat" className={({ isActive }) =>
            `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${isActive ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
            <Users size={16} /> Multi-Chat
          </NavLink>
          {(isCentralAdmin || user?.is_admin) && (
            <NavLink to="/settings" className={({ isActive }) =>
              `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${isActive ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
              <SettingsIcon size={16} /> Settings
            </NavLink>
          )}
        </nav>
        <div className="ml-auto flex items-center gap-2 sm:gap-3 text-sm text-gray-500 min-w-0">
          <span className="hidden sm:inline truncate max-w-[38vw]">
            {user?.username}
            {user?.company_name ? ` · ${user.company_name}` : ''}
            {user?.is_admin ? ' · admin' : ''}
          </span>
          <button onClick={logout} className="flex items-center gap-1 text-gray-500 hover:text-red-500 whitespace-nowrap">
            <LogOut size={15} /> <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <SidebarProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Protected><Shell><Chat /></Shell></Protected>} />
        <Route path="/multiperson-chat" element={<Protected><Shell><MultiPersonChat /></Shell></Protected>} />
        <Route path="/settings" element={<Protected><Shell><Settings /></Shell></Protected>} />
      </Routes>
    </SidebarProvider>
  )
}
