import React, { useEffect } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { MessageSquare, Settings as SettingsIcon, Database, LogOut, Loader, Menu, Minus, Users } from 'lucide-react'
import Chat from './pages/Chat.jsx'
import Settings from './pages/Settings.jsx'
import MultiPersonChat from './pages/MultiPersonChat.jsx'
import Login from './pages/Login.jsx'
import { useAuth } from './contexts/AuthContext'
import { SidebarProvider, useSidebar } from './contexts/SidebarContext'
import axios from 'axios'

// Utility: Convert hex color to RGB
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (result) {
    return `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
  }
  return '59, 130, 246' // Default blue fallback
}

// Utility: Darken color (for hover states)
function darkenColor(hex, percent = 15) {
  const num = parseInt(hex.replace("#", ""), 16)
  const amt = Math.round(2.55 * percent)
  const R = (num >> 16) - amt < 0 ? 0 : (num >> 16) - amt
  const G = (num >> 8 & 0x00FF) - amt < 0 ? 0 : (num >> 8 & 0x00FF) - amt
  const B = (num & 0x0000FF) - amt < 0 ? 0 : (num & 0x0000FF) - amt
  return "#" + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}

// Global theme application function
window.applyAppTheme = (themeSettings) => {
  const root = document.documentElement
  
  // Primary Colors
  if (themeSettings.primary_color) {
    root.style.setProperty('--color-primary', themeSettings.primary_color)
    root.style.setProperty('--color-primary-rgb', hexToRgb(themeSettings.primary_color))
    root.style.setProperty('--color-primary-dark', darkenColor(themeSettings.primary_color))
  }
  
  if (themeSettings.secondary_color) {
    root.style.setProperty('--color-secondary', themeSettings.secondary_color)
    root.style.setProperty('--color-secondary-rgb', hexToRgb(themeSettings.secondary_color))
    root.style.setProperty('--color-secondary-dark', darkenColor(themeSettings.secondary_color))
  }
  
  if (themeSettings.accent_color) {
    root.style.setProperty('--color-accent', themeSettings.accent_color)
    root.style.setProperty('--color-accent-rgb', hexToRgb(themeSettings.accent_color))
    root.style.setProperty('--color-accent-dark', darkenColor(themeSettings.accent_color))
  }
  
  if (themeSettings.background_color) {
    root.style.setProperty('--color-background', themeSettings.background_color)
  }
  
  if (themeSettings.text_color) {
    root.style.setProperty('--color-text', themeSettings.text_color)
  }
  
  // Tab Styling
  if (themeSettings.active_tab_text_color) {
    root.style.setProperty('--color-active-tab-text', themeSettings.active_tab_text_color)
  }
  if (themeSettings.active_tab_background_color) {
    root.style.setProperty('--color-active-tab-bg', themeSettings.active_tab_background_color)
  }
  if (themeSettings.inactive_tab_text_color) {
    root.style.setProperty('--color-inactive-tab-text', themeSettings.inactive_tab_text_color)
  }
  if (themeSettings.inactive_tab_background_color) {
    root.style.setProperty('--color-inactive-tab-bg', themeSettings.inactive_tab_background_color)
  }
  
  // Button Styling
  if (themeSettings.button_text_color) {
    root.style.setProperty('--color-button-text', themeSettings.button_text_color)
  }
  if (themeSettings.button_background_color) {
    root.style.setProperty('--color-button-bg', themeSettings.button_background_color)
  }
  if (themeSettings.button_hover_background_color) {
    root.style.setProperty('--color-button-hover-bg', themeSettings.button_hover_background_color)
  }
  if (themeSettings.button_disabled_text_color) {
    root.style.setProperty('--color-button-disabled-text', themeSettings.button_disabled_text_color)
  }
  if (themeSettings.button_disabled_background_color) {
    root.style.setProperty('--color-button-disabled-bg', themeSettings.button_disabled_background_color)
  }
  
  // Links & Navigation
  if (themeSettings.link_text_color) {
    root.style.setProperty('--color-link', themeSettings.link_text_color)
  }
  if (themeSettings.link_hover_color) {
    root.style.setProperty('--color-link-hover', themeSettings.link_hover_color)
  }
  if (themeSettings.link_visited_color) {
    root.style.setProperty('--color-link-visited', themeSettings.link_visited_color)
  }
  if (themeSettings.nav_text_color) {
    root.style.setProperty('--color-nav-text', themeSettings.nav_text_color)
  }
  if (themeSettings.nav_background_color) {
    root.style.setProperty('--color-nav-bg', themeSettings.nav_background_color)
  }
  if (themeSettings.nav_active_text_color) {
    root.style.setProperty('--color-nav-active-text', themeSettings.nav_active_text_color)
  }
  if (themeSettings.nav_active_background_color) {
    root.style.setProperty('--color-nav-active-bg', themeSettings.nav_active_background_color)
  }
  
  // Alert & Status Colors
  if (themeSettings.error_text_color) {
    root.style.setProperty('--color-error-text', themeSettings.error_text_color)
  }
  if (themeSettings.error_background_color) {
    root.style.setProperty('--color-error-bg', themeSettings.error_background_color)
  }
  if (themeSettings.warning_text_color) {
    root.style.setProperty('--color-warning-text', themeSettings.warning_text_color)
  }
  if (themeSettings.warning_background_color) {
    root.style.setProperty('--color-warning-bg', themeSettings.warning_background_color)
  }
  if (themeSettings.success_text_color) {
    root.style.setProperty('--color-success-text', themeSettings.success_text_color)
  }
  if (themeSettings.success_background_color) {
    root.style.setProperty('--color-success-bg', themeSettings.success_background_color)
  }
  if (themeSettings.info_text_color) {
    root.style.setProperty('--color-info-text', themeSettings.info_text_color)
  }
  if (themeSettings.info_background_color) {
    root.style.setProperty('--color-info-bg', themeSettings.info_background_color)
  }
  
  // Font Settings
  if (themeSettings.font_family) {
    root.style.setProperty('--font-family', themeSettings.font_family)
  }
  
  if (themeSettings.font_size_base) {
    root.style.setProperty('--font-size-base', `${themeSettings.font_size_base}px`)
  }
  if (themeSettings.font_size_small) {
    root.style.setProperty('--font-size-small', `${themeSettings.font_size_small}px`)
  }
  if (themeSettings.font_size_large) {
    root.style.setProperty('--font-size-large', `${themeSettings.font_size_large}px`)
  }
  if (themeSettings.font_size_xl) {
    root.style.setProperty('--font-size-xl', `${themeSettings.font_size_xl}px`)
  }
  
  // Apply dark mode if enabled
  if (themeSettings.theme_mode === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  
  // Update app name in header if it exists
  if (themeSettings.app_name) {
    const appNameElement = document.querySelector('[data-app-name]')
    if (appNameElement) {
      appNameElement.textContent = themeSettings.app_name
    }
  }
  
  // Update favicon if provided
  if (themeSettings.favicon_url) {
    let faviconLink = document.querySelector('link[rel="icon"]')
    if (!faviconLink) {
      faviconLink = document.createElement('link')
      faviconLink.rel = 'icon'
      document.head.appendChild(faviconLink)
    }
    faviconLink.href = themeSettings.favicon_url
  }
}

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
  const [appName, setAppName] = React.useState('AI Assistant')
  const [logoUrl, setLogoUrl] = React.useState(null)
  
  React.useEffect(() => {
    // Load app settings and apply theme
    const loadTheme = async () => {
      try {
        const { data } = await axios.get('/api/settings/app/theme')
        if (data.success && data.theme) {
          window.applyAppTheme(data.theme)
          setAppName(data.theme.app_name || 'AI Assistant')
          setLogoUrl(data.theme.logo_url || null)
          
          // Apply dynamic CSS overrides for theme-aware styling
          injectThemeOverrides(data.theme)
        }
      } catch (error) {
        console.debug('Theme load skipped (no saved settings)')
      }
    }
    loadTheme()
  }, [])
  
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 px-3 sm:px-4 py-2.5 flex items-center gap-2 md:gap-4" style={{
        borderBottomColor: 'var(--color-border, #e5e7eb)',
        backgroundColor: 'var(--color-background, #ffffff)'
      }}>
        <button
          onClick={() => setSidebarOpen((prev) => !prev)}
          className="p-2 hover:bg-gray-100 rounded transition md:hidden"
          title={sidebarOpen ? 'Hide history' : 'Show history'}
        >
          {sidebarOpen ? <Minus size={16} className="text-gray-600" /> : <Menu size={16} className="text-gray-600" />}
        </button>
        <div className="flex items-center gap-2 px-3 py-1 rounded font-semibold" style={{
          color: 'var(--color-primary, #3b82f6)'
        }}>
          {logoUrl ? (
            <img src={logoUrl} alt="App Logo" className="h-6 w-6 object-contain" />
          ) : (
            <Database size={20} />
          )}
          <span data-app-name className="hidden sm:inline text-sm">{appName}</span>
        </div>
        <nav className="flex items-center gap-1 md:ml-2 overflow-x-auto pb-0.5 md:pb-0">
          <NavLink to="/chat" className={({ isActive }) =>
            `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${isActive ? 'font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
            style={({ isActive }) => isActive ? {
              backgroundColor: 'rgba(var(--color-primary-rgb, 59 130 246), 0.1)',
              color: 'var(--color-primary, #3b82f6)'
            } : {}}
          >
            <MessageSquare size={16} /> Chat
          </NavLink>
          <NavLink to="/multiperson-chat" className={({ isActive }) =>
            `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${isActive ? 'font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
            style={({ isActive }) => isActive ? {
              backgroundColor: 'rgba(var(--color-primary-rgb, 59 130 246), 0.1)',
              color: 'var(--color-primary, #3b82f6)'
            } : {}}
          >
            <Users size={16} /> Multi-Chat
          </NavLink>
          {(isCentralAdmin || user?.is_admin) && (
            <NavLink to="/settings" className={({ isActive }) =>
              `flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${isActive ? 'font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
              style={({ isActive }) => isActive ? {
                backgroundColor: 'rgba(var(--color-primary-rgb, 59 130 246), 0.1)',
                color: 'var(--color-primary, #3b82f6)'
              } : {}}
            >
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
          <button 
            onClick={logout} 
            className="flex items-center gap-1 text-gray-500 hover:text-red-500 whitespace-nowrap transition"
            style={{ '--hover-color': 'var(--color-accent, #ef4444)' }}
          >
            <LogOut size={15} /> <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>
      <main className="flex-1" style={{ backgroundColor: '#f9fafb' }}>{children}</main>
    </div>
  )
}

// Helper function to inject theme-aware CSS overrides
function injectThemeOverrides(theme) {
  // Remove existing style if it exists
  let styleEl = document.getElementById('theme-overrides')
  if (styleEl) {
    styleEl.remove()
  }
  
  // Create new style element with theme-aware CSS
  styleEl = document.createElement('style')
  styleEl.id = 'theme-overrides'
  styleEl.textContent = `
    /* ========== LINKS ========== */
    a {
      color: var(--color-link, var(--color-primary, #3b82f6));
      transition: color 0.2s ease;
    }
    a:hover {
      color: var(--color-link-hover, var(--color-primary-dark, #1e40af));
      text-decoration: underline;
    }
    a:visited {
      color: var(--color-link-visited, #8b5cf6);
    }
    
    /* ========== BUTTONS - Only theme buttons with btn-* classes ========== */
    [class*="btn-"] {
      background-color: var(--color-button-bg, var(--color-primary, #3b82f6)) !important;
      color: var(--color-button-text, white) !important;
      transition: all 0.2s ease;
    }
    
    [class*="btn-"]:hover {
      background-color: var(--color-button-hover-bg, var(--color-primary-dark, #1e40af)) !important;
      color: var(--color-button-text, white) !important;
      opacity: 0.9;
    }
    
    [class*="btn-"]:disabled {
      background-color: var(--color-button-disabled-bg, #d1d5db) !important;
      color: var(--color-button-disabled-text, #6b7280) !important;
      cursor: not-allowed;
      opacity: 0.6;
    }
    
    /* ========== TABS ========== */
    [role="tab"], .nav-link, .tab-link {
      color: var(--color-inactive-tab-text, #6b7280);
      background-color: var(--color-inactive-tab-bg, #f3f4f6);
      border-color: var(--color-border, #e5e7eb);
      transition: all 0.2s ease;
    }
    
    [role="tab"][aria-selected="true"], 
    .nav-link.active, 
    .tab-link.active,
    [role="tab"].active {
      color: var(--color-active-tab-text, white);
      background-color: var(--color-active-tab-bg, var(--color-primary, #3b82f6));
      border-color: var(--color-active-tab-bg, var(--color-primary, #3b82f6));
      font-weight: 600;
    }
    
    /* ========== NAVIGATION ========== */
    nav, [role="navigation"] {
      background-color: var(--color-nav-bg, white);
      color: var(--color-nav-text, #6b7280);
    }
    
    nav a, [role="navigation"] a {
      color: var(--color-nav-text, #6b7280);
    }
    
    nav a:hover, [role="navigation"] a:hover {
      color: var(--color-nav-active-text, var(--color-primary, #3b82f6));
      background-color: var(--color-nav-active-bg, rgba(59, 130, 246, 0.1));
    }
    
    nav a.active, [role="navigation"] a.active {
      color: var(--color-nav-active-text, white);
      background-color: var(--color-nav-active-bg, var(--color-primary, #3b82f6));
      font-weight: 600;
    }
    
    /* ========== ALERTS & STATUS ========== */
    .alert-error, [class*="alert-error"], .error-alert {
      background-color: var(--color-error-bg, #fee2e2);
      color: var(--color-error-text, #991b1b);
      border-color: var(--color-error-text, #991b1b);
    }
    
    .alert-warning, [class*="alert-warning"], .warning-alert {
      background-color: var(--color-warning-bg, #fef3c7);
      color: var(--color-warning-text, #92400e);
      border-color: var(--color-warning-text, #92400e);
    }
    
    .alert-success, [class*="alert-success"], .success-alert {
      background-color: var(--color-success-bg, #dcfce7);
      color: var(--color-success-text, #166534);
      border-color: var(--color-success-text, #166534);
    }
    
    .alert-info, [class*="alert-info"], .info-alert {
      background-color: var(--color-info-bg, #dbeafe);
      color: var(--color-info-text, #0c4a6e);
      border-color: var(--color-info-text, #0c4a6e);
    }
    
    /* ========== FORM ELEMENTS ========== */
    input:focus, textarea:focus, select:focus {
      border-color: var(--color-primary, #3b82f6) !important;
      box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 59 130 246), 0.1) !important;
    }
    
    /* ========== PRIMARY BRANDING ========== */
    .bg-brand-600, .bg-brand-700 {
      background-color: var(--color-primary, #3b82f6) !important;
    }
    
    .hover\\:bg-brand-700:hover, .hover\\:bg-brand-600:hover {
      background-color: var(--color-primary-dark, #1e40af) !important;
    }
    
    .text-brand-600, .text-brand-700, [class*="text-brand"] {
      color: var(--color-primary, #3b82f6) !important;
    }
    
    .border-brand-600, .border-brand-700, [class*="border-brand"] {
      border-color: var(--color-primary, #3b82f6) !important;
    }
    
    /* ========== TEXT & BACKGROUND ========== */
    [class*="text-gray-900"] {
      color: var(--color-text, #000000) !important;
    }
    
    .bg-white, [class*="bg-white"] {
      background-color: var(--color-background, #ffffff) !important;
    }
    
    /* ========== CHAT MESSAGES ========== */
    .chat-message-user {
      background-color: rgba(var(--color-primary-rgb, 59 130 246), 0.1);
      border-color: var(--color-primary, #3b82f6);
      color: var(--color-text, #000000);
    }
    
    .chat-message-assistant {
      background-color: #f3f4f6;
      color: var(--color-text, #000000);
    }
    
    /* ========== TABLES ========== */
    table tbody tr {
      background-color: var(--color-background, #ffffff);
      border-color: #f0f0f0;
      color: var(--color-text, #000000);
    }
    
    table tbody tr:hover {
      background-color: #f9f9f9;
    }
    
    /* ========== BADGES & PILLS ========== */
    [class*="badge"], [class*="pill"] {
      background-color: rgba(var(--color-primary-rgb, 59 130 246), 0.1);
      color: var(--color-primary, #3b82f6);
      border-color: var(--color-primary, #3b82f6);
    }
    
    /* ========== CARDS ========== */
    .card, [class*="card"] {
      background-color: var(--color-background, #ffffff);
      color: var(--color-text, #000000);
      border-color: #e5e7eb;
    }
    
    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    
    ::-webkit-scrollbar-track {
      background: #f3f4f6;
    }
    
    ::-webkit-scrollbar-thumb {
      background: #d1d5db;
      border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
      background: var(--color-secondary, #1f2937);
    }
  `
  document.head.appendChild(styleEl)
}

// Make it globally available
window.injectThemeOverrides = injectThemeOverrides

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
