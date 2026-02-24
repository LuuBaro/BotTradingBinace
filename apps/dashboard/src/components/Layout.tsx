import React, { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LogOut, Menu, X, BarChart3, Zap } from 'lucide-react'
import { useAuthStore } from '../store'

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { logout, user } = useAuthStore()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = React.useState(true)

  const menuItems = [
    { path: '/', label: 'Overview', icon: '📊' },
    { path: '/positions', label: 'Positions', icon: '📍' },
    { path: '/orders', label: 'Orders', icon: '📋' },
    { path: '/trades', label: 'Trades', icon: '💹' },
    { path: '/risk-config', label: 'Risk Config', icon: '⚙️' },
    { path: '/system-health', label: 'System Health', icon: '🏥' },
    { path: '/events', label: 'Events & Audit', icon: '📅' },
    { path: '/learning', label: 'Learning', icon: '🧠' },
  ]

  return (
    <div className="flex h-screen bg-slate-900 text-white overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 transition-all duration-300 overflow-hidden flex flex-col shadow-xl`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-slate-700 flex items-center gap-3 flex-shrink-0 hover:bg-slate-700 transition-colors">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg">
            <BarChart3 size={24} className="text-white" />
          </div>
          {sidebarOpen && (
            <div className="flex flex-col">
              <span className="font-bold text-lg">Trading Bot</span>
              <span className="text-xs text-slate-400">AI Powered</span>
            </div>
          )}
        </div>

        {/* Menu */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group ${
                  isActive
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                <span className="text-xl flex-shrink-0">{item.icon}</span>
                {sidebarOpen && (
                  <span className="font-medium flex-1">{item.label}</span>
                )}
                {isActive && sidebarOpen && (
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        {sidebarOpen && (
          <div className="p-4 border-t border-slate-700 space-y-3">
            <div className="bg-slate-700 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2 text-slate-300">
                <Zap size={14} />
                <span className="text-xs">Status: Running</span>
              </div>
              <div className="text-xs text-slate-400">
                Mode: Demo
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-gradient-to-r from-slate-800 to-slate-900 border-b border-slate-700 px-6 py-4 flex items-center justify-between flex-shrink-0 shadow-lg">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-300 hover:text-white"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <div className="flex items-center gap-6">
            {/* Status Indicator */}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-slate-300">Connected</span>
            </div>

            {/* User Info */}
            <div className="hidden sm:block">
              <p className="text-sm font-medium">{user?.username || 'Guest'}</p>
              <p className="text-xs text-slate-400">{user?.role || 'User'}</p>
            </div>

            {/* Logout Button */}
            <button
              onClick={() => {
                logout()
                window.location.href = '/login'
              }}
              className="btn btn-danger btn-sm"
              title="Logout"
            >
              <LogOut size={18} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-900 space-y-6">
          <div className="animate-slideInUp">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
