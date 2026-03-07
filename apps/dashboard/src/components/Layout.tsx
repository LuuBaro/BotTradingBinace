import React, { useState, useEffect, useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LogOut, Menu, X, Zap, Activity, Shield, Settings, Grid, History, HeartPulse, Terminal, BookOpen, User, MessagesSquare } from 'lucide-react'
import { useAuthStore } from '../store'
import { useWebSocket } from '../hooks/useWebSocket'
import { NotificationBell } from './NotificationBell'
import { WalletIndicator } from './WalletIndicator'
import { createApiClient, getApiBaseUrl } from '../api/client'

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { logout, user } = useAuthStore()
  const location = useLocation()
  const token = localStorage.getItem('token') || ''
  const api = useMemo(() => createApiClient(getApiBaseUrl(), token), [token])
  // Desktop: open by default, Mobile: closed by default
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isMobileView, setIsMobileView] = useState(window.innerWidth < 768)

  // Initialize WebSocket connection
  useWebSocket()

  // Close mobile menu when location changes (navigation)
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 768
      setIsMobileView(isMobile)
      if (!isMobile) {
        setMobileMenuOpen(false)
        setSidebarOpen(true)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (!token) return

    const sendTelemetry = async (eventType: 'session_start' | 'network_change') => {
      try {
        const nav = navigator as any
        const connection = nav.connection || nav.mozConnection || nav.webkitConnection
        await api.logAccessTelemetry({
          event_type: eventType,
          network_online: navigator.onLine,
          network_effective_type: connection?.effectiveType || null,
          network_downlink_mbps: typeof connection?.downlink === 'number' ? connection.downlink : null,
          network_rtt_ms: typeof connection?.rtt === 'number' ? connection.rtt : null,
          user_agent: navigator.userAgent,
          platform: navigator.platform,
          language: navigator.language,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          screen_width: window.screen?.width || null,
          screen_height: window.screen?.height || null,
          device_memory_gb: typeof nav.deviceMemory === 'number' ? nav.deviceMemory : null,
          hardware_concurrency: typeof navigator.hardwareConcurrency === 'number' ? navigator.hardwareConcurrency : null,
        })
      } catch {
        // No-op: telemetry must never break UI
      }
    }

    sendTelemetry('session_start')
    const handleNetworkChange = () => sendTelemetry('network_change')
    window.addEventListener('online', handleNetworkChange)
    window.addEventListener('offline', handleNetworkChange)

    return () => {
      window.removeEventListener('online', handleNetworkChange)
      window.removeEventListener('offline', handleNetworkChange)
    }
  }, [api, token])

  const menuItems = [
    { path: '/', label: 'Overview', icon: <Grid size={20} /> },
    { path: '/positions', label: 'Active Zones', icon: <Activity size={20} /> },
    { path: '/orders', label: 'Order Stack', icon: <Terminal size={20} /> },
    { path: '/trade-history', label: 'Trade History', icon: <History size={20} /> },
    { path: '/trades', label: 'Trace Logs', icon: <History size={20} /> },
    { path: '/risk-config', label: 'Risk Vault', icon: <Shield size={20} /> },
    { path: '/system-health', label: 'Health Nexus', icon: <HeartPulse size={20} /> },
    { path: '/events', label: 'Audit Trail', icon: <Terminal size={20} /> },
    { path: '/learning', label: 'Neural Opt', icon: <BookOpen size={20} /> },
    { path: '/message-center', label: 'Message Ops', icon: <MessagesSquare size={20} /> },
    { path: '/settings', label: 'System Prefs', icon: <Settings size={20} /> },
  ]

  return (
    <div className="flex h-screen bg-[#020617] text-slate-200 overflow-hidden font-sans selection:bg-blue-500/30">
      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden" 
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      
      {/* Premium Sidebar */}
      <aside
        className={`w-72 ${sidebarOpen ? 'md:w-72' : 'md:w-24'}
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} 
          md:translate-x-0 fixed md:relative h-full
          bg-[#020617] border-r border-white/5 transition-all duration-500 ease-in-out flex flex-col z-50`}
      >
        {/* Logo Section */}
        <div className="h-20 md:h-24 flex items-center px-6 border-b border-white/5 gap-4">
          <div className={`p-3 bg-gradient-to-br from-blue-600 to-blue-400 rounded-2xl shadow-lg shadow-blue-500/20 transform transition-transform duration-500 ${sidebarOpen ? 'rotate-0' : 'rotate-180'}`}>
            <Zap size={24} className="text-white fill-current" />
          </div>
          <div className={`flex-col animate-fadeIn flex ${sidebarOpen ? '' : 'md:hidden'}`}>
            <span className="font-black text-xl tracking-tighter text-white">TiznDBot</span>
            <span className="text-[9px] font-black text-blue-400 uppercase tracking-[0.3em]">Trading Intelligence</span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 px-4 py-8 space-y-2 overflow-y-auto custom-scrollbar">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-300 group relative ${isActive
                  ? 'bg-blue-600 text-white shadow-2xl shadow-blue-500/20'
                  : 'text-slate-500 hover:text-white hover:bg-white/5 '
                  }`}
              >
                <div className={`transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`}>
                  {item.icon}
                </div>
                <span className={`font-bold text-sm tracking-tight flex-1 animate-fadeIn ${sidebarOpen ? '' : 'md:hidden'}`}>{item.label}</span>
                {isActive && (
                  <div className="absolute left-0 w-1.5 h-6 bg-white rounded-r-full shadow-[4px_0_15px_rgba(255,255,255,0.5)]"></div>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Sidebar Footer - System Identity */}
        <div className="p-6 border-t border-white/5 bg-slate-950/30">
          {isMobileView || sidebarOpen ? (
            <div className="p-4 bg-white/5 rounded-2xl border border-white/5 space-y-4 animate-fadeIn">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-glow"></div>
                <span className="text-[10px] font-black uppercase text-emerald-400 tracking-widest">Global Mainnet</span>
              </div>
              <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
                <span>V.4.2.0-STABLE</span>
                <span>94.2 MS</span>
              </div>
            </div>
          ) : (
            <div className="hidden md:flex justify-center">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-glow"></div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Orchestrator */}
      <div className="flex-1 flex flex-col overflow-hidden bg-mesh relative">
        {/* Glow Effects */}
        <div className="absolute top-0 left-1/4 w-[50%] h-[30%] bg-blue-500/5 blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-0 right-1/4 w-[40%] h-[20%] bg-purple-500/5 blur-[100px] pointer-events-none"></div>

        {/* Context-Aware Header */}
        <header className="h-20 md:h-24 glass-dark border-b border-white/5 px-4 md:px-10 flex items-center justify-between flex-shrink-0 relative z-40">
          <div className="flex items-center gap-3 md:gap-8">
            <button
              onClick={() => {
                // Mobile: toggle menu overlay, Desktop: toggle sidebar width
                if (window.innerWidth < 768) {
                  setMobileMenuOpen(!mobileMenuOpen)
                } else {
                  setSidebarOpen(!sidebarOpen)
                }
              }}
              className="p-2 md:p-3 bg-white/5 hover:bg-white/10 rounded-xl md:rounded-2xl transition-all text-slate-400 hover:text-white active:scale-95 border border-white/5"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <div className="hidden lg:flex items-center gap-4 text-slate-500">
              <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-xl border border-white/5">
                <Activity size={12} />
                <span className="text-[10px] font-black uppercase tracking-widest">Live Execution Stack</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 md:gap-6">
            <WalletIndicator />
            <NotificationBell />

            {/* User Profile Hook */}
            <div className="flex items-center gap-2 md:gap-4 pl-4 md:pl-8 border-l border-white/10">
              <div className="text-right hidden lg:block">
                <p className="text-sm font-black text-white tracking-tight">{user?.username || 'ROOT_SUDO'}</p>
                <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest">{user?.role || 'SYSTEM_ADMIN'}</p>
              </div>
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl md:rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 border border-white/10 flex items-center justify-center shadow-xl group hover:border-blue-500/50 transition-all cursor-pointer">
                <User size={18} className="md:w-5 md:h-5 text-slate-400 group-hover:text-blue-400 transition-colors" />
              </div>
            </div>

            {/* Logout Sequence */}
            <button
              onClick={() => {
                logout()
                // After logout, just go to login page - don't reload app
                // This preserves setupComplete state and avoids Setup page on re-entry
                window.location.href = '/login'
              }}
              className="p-2 md:p-3 bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white rounded-xl md:rounded-2xl transition-all active:scale-95 border border-rose-500/20 hover:shadow-lg hover:shadow-rose-500/20"
              title="Terminate Session"
            >
              <LogOut size={18} className="md:w-5 md:h-5" />
            </button>
          </div>
        </header>

        {/* Content Viewport */}
        <main className="flex-1 overflow-auto custom-scrollbar relative z-10 px-4 py-4 md:px-10 md:py-8">
          <div className="animate-slideUp max-w-[1600px] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
