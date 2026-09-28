import React, { useState, useEffect } from 'react'
import { Save, Loader, CheckCircle2, XCircle, Palette, Type, Image } from 'lucide-react'
import api, { handleApiError } from '../api/client'
import Swal from 'sweetalert2'

export default function AppSettingsTab() {
  const [settings, setSettings] = useState({
    app_name: 'BrainR',
    // Primary Colors
    primary_color: '#3b82f6',
    secondary_color: '#1f2937',
    accent_color: '#f59e0b',
    background_color: '#ffffff',
    text_color: '#000000',
    // Tab Styling
    active_tab_text_color: '#ffffff',
    active_tab_background_color: '#3b82f6',
    inactive_tab_text_color: '#6b7280',
    inactive_tab_background_color: '#f3f4f6',
    // Button Styling
    button_text_color: '#ffffff',
    button_background_color: '#3b82f6',
    button_hover_background_color: '#1e40af',
    button_disabled_text_color: '#6b7280',
    button_disabled_background_color: '#d1d5db',
    // Links & Navigation
    link_text_color: '#3b82f6',
    link_hover_color: '#1e40af',
    link_visited_color: '#8b5cf6',
    nav_text_color: '#6b7280',
    nav_background_color: '#ffffff',
    nav_active_text_color: '#ffffff',
    nav_active_background_color: '#3b82f6',
    // Alert & Status Colors
    error_text_color: '#991b1b',
    error_background_color: '#fee2e2',
    warning_text_color: '#92400e',
    warning_background_color: '#fef3c7',
    success_text_color: '#166534',
    success_background_color: '#dcfce7',
    info_text_color: '#0c4a6e',
    info_background_color: '#dbeafe',
    // Font Settings
    font_family: 'Inter, sans-serif',
    font_size_base: 14,
    font_size_small: 12,
    font_size_large: 16,
    font_size_xl: 18,
    // Logo & Theme
    logo_url: '',
    favicon_url: '',
    enable_dark_mode: false,
    theme_mode: 'light',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [logoPreview, setLogoPreview] = useState(null)
  const [faviconPreview, setFaviconPreview] = useState(null)

  // Load settings
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const { data } = await api.get('/api/settings/app')
      if (data.success && data.config) {
        setSettings(data.config)
        if (data.config.logo_url) setLogoPreview(data.config.logo_url)
        if (data.config.favicon_url) setFaviconPreview(data.config.favicon_url)
      }
    } catch (error) {
      handleApiError(error, 'Failed to load app settings')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleColorChange = (colorField, color) => {
    setSettings(prev => ({ ...prev, [colorField]: color }))
  }

  const handleLogoUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        const dataUrl = event.target.result
        setLogoPreview(dataUrl)
        setSettings(prev => ({ ...prev, logo_url: dataUrl }))
      }
      reader.readAsDataURL(file)
    }
  }

  const handleFaviconUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        const dataUrl = event.target.result
        setFaviconPreview(dataUrl)
        setSettings(prev => ({ ...prev, favicon_url: dataUrl }))
      }
      reader.readAsDataURL(file)
    }
  }

  const saveSettings = async () => {
    try {
      setSaving(true)
      const { data } = await api.post('/api/settings/app', settings)
      if (data.success) {
        setMessage({ type: 'success', text: 'App settings saved successfully!' })
        // Apply theme changes to the app immediately
        applyTheme(settings)
        // Also call the global theme function if available
        if (window.applyAppTheme) {
          window.applyAppTheme(settings)
        }
        // Apply dynamic CSS overrides
        if (window.injectThemeOverrides) {
          window.injectThemeOverrides(settings)
        }
        setTimeout(() => setMessage(null), 3000)
      }
    } catch (error) {
      handleApiError(error, 'Failed to save settings')
      setMessage({ type: 'error', text: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  const applyTheme = (themeSettings) => {
    const root = document.documentElement
    root.style.setProperty('--color-primary', themeSettings.primary_color)
    root.style.setProperty('--color-secondary', themeSettings.secondary_color)
    root.style.setProperty('--color-accent', themeSettings.accent_color)
    root.style.setProperty('--color-background', themeSettings.background_color)
    root.style.setProperty('--color-text', themeSettings.text_color)
    root.style.setProperty('--font-family', themeSettings.font_family)
    root.style.setProperty('--font-size-base', `${themeSettings.font_size_base}px`)
    
    if (themeSettings.theme_mode === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  const resetToDefaults = async () => {
    const result = await Swal.fire({
      title: 'Reset to Defaults?',
      text: 'This will reset all app settings to their default values.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Reset',
      cancelButtonText: 'Cancel',
    })

    if (result.isConfirmed) {
      const defaults = {
        app_name: 'BrainR',
        // Primary Colors
        primary_color: '#3b82f6',
        secondary_color: '#1f2937',
        accent_color: '#f59e0b',
        background_color: '#ffffff',
        text_color: '#000000',
        // Tab Styling
        active_tab_text_color: '#ffffff',
        active_tab_background_color: '#3b82f6',
        inactive_tab_text_color: '#6b7280',
        inactive_tab_background_color: '#f3f4f6',
        // Button Styling
        button_text_color: '#ffffff',
        button_background_color: '#3b82f6',
        button_hover_background_color: '#1e40af',
        button_disabled_text_color: '#6b7280',
        button_disabled_background_color: '#d1d5db',
        // Links & Navigation
        link_text_color: '#3b82f6',
        link_hover_color: '#1e40af',
        link_visited_color: '#8b5cf6',
        nav_text_color: '#6b7280',
        nav_background_color: '#ffffff',
        nav_active_text_color: '#ffffff',
        nav_active_background_color: '#3b82f6',
        // Alert & Status Colors
        error_text_color: '#991b1b',
        error_background_color: '#fee2e2',
        warning_text_color: '#92400e',
        warning_background_color: '#fef3c7',
        success_text_color: '#166534',
        success_background_color: '#dcfce7',
        info_text_color: '#0c4a6e',
        info_background_color: '#dbeafe',
        // Font Settings
        font_family: 'Inter, sans-serif',
        font_size_base: 14,
        font_size_small: 12,
        font_size_large: 16,
        font_size_xl: 18,
        // Logo & Theme
        logo_url: '',
        favicon_url: '',
        enable_dark_mode: false,
        theme_mode: 'light',
      }
      setSettings(defaults)
      setLogoPreview(null)
      setFaviconPreview(null)
      setMessage({ type: 'info', text: 'Settings reset to defaults. Click Save to apply.' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader className="animate-spin" size={24} />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-4 bg-gray-50 rounded-lg">
      <div className="mb-4">
        <h2 className="text-lg font-semibold mb-2">Application Branding & Theme</h2>
        <p className="text-sm text-gray-600">Customize the look and feel of your application</p>
      </div>

      {message && (
        <div className={`flex items-center gap-2 p-3 rounded ${
          message.type === 'success' ? 'bg-green-100 text-green-700' :
          message.type === 'error' ? 'bg-red-100 text-red-700' :
          'bg-blue-100 text-blue-700'
        }`}>
          {message.type === 'success' && <CheckCircle2 size={20} />}
          {message.type === 'error' && <XCircle size={20} />}
          {message.text}
        </div>
      )}

      {/* App Identity Section */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <h3 className="text-md font-semibold mb-4 flex items-center gap-2">
          <Image size={18} /> App Identity
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">App Name</label>
            <input
              type="text"
              name="app_name"
              value={settings.app_name}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Logo</label>
            <div className="flex gap-2">
              <input
                type="file"
                accept="image/*"
                onChange={handleLogoUpload}
                className="flex-1"
              />
              {logoPreview && (
                <img src={logoPreview} alt="Logo" className="h-10 w-10 object-contain border rounded" />
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">Max 2MB, PNG/JPG recommended</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Favicon</label>
            <div className="flex gap-2">
              <input
                type="file"
                accept="image/*"
                onChange={handleFaviconUpload}
                className="flex-1"
              />
              {faviconPreview && (
                <img src={faviconPreview} alt="Favicon" className="h-10 w-10 object-contain border rounded" />
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">Favicon for browser tab</p>
          </div>
        </div>
      </div>

      {/* Color Scheme Section */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <h3 className="text-md font-semibold mb-4 flex items-center gap-2">
          <Palette size={18} /> Color Scheme & Typography
        </h3>

        {/* Primary Colors */}
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Primary Colors</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'primary_color', label: 'Primary' },
              { key: 'secondary_color', label: 'Secondary' },
              { key: 'accent_color', label: 'Accent' },
              { key: 'background_color', label: 'Background' },
              { key: 'text_color', label: 'Text' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-10 w-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tab Styling */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Tab Styling</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'active_tab_text_color', label: 'Active Tab Text' },
              { key: 'active_tab_background_color', label: 'Active Tab BG' },
              { key: 'inactive_tab_text_color', label: 'Inactive Tab Text' },
              { key: 'inactive_tab_background_color', label: 'Inactive Tab BG' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-10 w-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Button Styling */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Button Styling</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'button_text_color', label: 'Button Text' },
              { key: 'button_background_color', label: 'Button BG' },
              { key: 'button_hover_background_color', label: 'Button Hover' },
              { key: 'button_disabled_text_color', label: 'Disabled Text' },
              { key: 'button_disabled_background_color', label: 'Disabled BG' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-10 w-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Link & Navigation Styling */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Links & Navigation</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'link_text_color', label: 'Link Color' },
              { key: 'link_hover_color', label: 'Link Hover' },
              { key: 'link_visited_color', label: 'Link Visited' },
              { key: 'nav_text_color', label: 'Nav Text' },
              { key: 'nav_background_color', label: 'Nav BG' },
              { key: 'nav_active_text_color', label: 'Active Nav Text' },
              { key: 'nav_active_background_color', label: 'Active Nav BG' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-10 w-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Alert/Status Colors */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Alert & Status Colors</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'error_text_color', label: 'Error Text' },
              { key: 'error_background_color', label: 'Error BG' },
              { key: 'warning_text_color', label: 'Warning Text' },
              { key: 'warning_background_color', label: 'Warning BG' },
              { key: 'success_text_color', label: 'Success Text' },
              { key: 'success_background_color', label: 'Success BG' },
              { key: 'info_text_color', label: 'Info Text' },
              { key: 'info_background_color', label: 'Info BG' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="h-10 w-12 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings[key] || '#000000'}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Typography Section */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Font Sizes</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { key: 'font_size_base', label: 'Base (px)', type: 'number', min: 12, max: 20 },
              { key: 'font_size_small', label: 'Small (px)', type: 'number', min: 10, max: 16 },
              { key: 'font_size_large', label: 'Large (px)', type: 'number', min: 14, max: 24 },
              { key: 'font_size_xl', label: 'Extra Large (px)', type: 'number', min: 16, max: 28 },
            ].map(({ key, label, type, min, max }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-1">{label}</label>
                <input
                  type={type}
                  name={key}
                  value={settings[key] || 14}
                  onChange={handleInputChange}
                  min={min}
                  max={max}
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Theme Mode */}
        <div className="mt-4 p-3 bg-gray-50 rounded">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              name="enable_dark_mode"
              checked={settings.enable_dark_mode}
              onChange={handleInputChange}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium">Enable Dark Mode Support</span>
          </label>
        </div>

        <div className="mt-3">
          <label className="block text-sm font-medium mb-2">Theme Mode</label>
          <select
            name="theme_mode"
            value={settings.theme_mode}
            onChange={handleInputChange}
            className="w-full md:w-1/3 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="auto">Auto (System)</option>
          </select>
        </div>
      </div>

      {/* Typography Section */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <h3 className="text-md font-semibold mb-4 flex items-center gap-2">
          <Type size={18} /> Typography
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Font Family</label>
            <select
              name="font_family"
              value={settings.font_family}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="Inter, sans-serif">Inter</option>
              <option value="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif">Segoe UI</option>
              <option value="'Helvetica Neue', Arial, sans-serif">Helvetica</option>
              <option value="Georgia, serif">Georgia</option>
              <option value="'Courier New', monospace">Courier New</option>
              <option value="'JetBrains Mono', monospace">JetBrains Mono</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Base Font Size (px)</label>
            <input
              type="number"
              name="font_size_base"
              value={settings.font_size_base}
              onChange={handleInputChange}
              min="12"
              max="20"
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Font Preview */}
        <div className="mt-4 p-3 bg-gray-50 rounded" style={{ fontFamily: settings.font_family, fontSize: `${settings.font_size_base}px` }}>
          <p>Font Preview: The quick brown fox jumps over the lazy dog</p>
          <p style={{ fontSize: `${settings.font_size_base * 1.5}px`, fontWeight: 'bold' }}>Heading Preview</p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 justify-end">
        <button
          onClick={resetToDefaults}
          className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 transition"
        >
          Reset to Defaults
        </button>
        <button
          onClick={saveSettings}
          disabled={saving}
          className="btn-primary flex items-center gap-2 px-4 py-2"
        >
          {saving ? <Loader className="animate-spin" size={16} /> : <Save size={16} />}
          Save Settings
        </button>
      </div>
    </div>
  )
}
