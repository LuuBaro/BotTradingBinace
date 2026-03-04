import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { PositionsPage } from './pages/PositionsPage'
import { OrdersPage } from './pages/OrdersPage'
import { TradesPage } from './pages/TradesPage'
import { TradeHistoryPage } from './pages/TradeHistoryPage'
import { RiskConfigPage } from './pages/RiskConfigPage'
import { SystemHealthPage } from './pages/SystemHealthPage'
import { EventsPage } from './pages/EventsPage'
import { LearningPage } from './pages/LearningPage'
import { SettingsPage } from './pages/SettingsPage'
import { IntelPage } from './pages/IntelPage'

function App() {
  const { isAuthenticated, clearToken } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [tokenWarning, setTokenWarning] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    setLoading(false)
  }, [])

  useEffect(() => {
    const handleAuthExpired = () => {
      console.log('🔐 Token expired - auto logout triggered')
      clearToken()
      window.location.href = '/login'
    }

    window.addEventListener('auth:expired', handleAuthExpired)

    const tokenExpirationTimer = setTimeout(() => {
      setTokenWarning(true)
      console.log('⏰ Token expiring in 5 minutes')
    }, 86400000 - 300000)

    const autoLogoutTimer = setTimeout(() => {
      console.log('🔐 Token expired - auto logout triggered')
      clearToken()
      window.location.href = '/login'
    }, 86400000)

    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired)
      clearTimeout(tokenExpirationTimer)
      clearTimeout(autoLogoutTimer)
    }
  }, [clearToken])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return (
    <Router>
      {tokenWarning && (
        <div className="fixed top-0 left-0 right-0 bg-amber-500/20 border-b border-amber-500/50 text-amber-300 px-4 py-3 backdrop-blur text-center font-medium z-50">
          ⏰ Your session expires in 5 minutes. Please save your work.
        </div>
      )}
      <Layout>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/intel" element={<IntelPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/trade-history" element={<TradeHistoryPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/risk-config" element={<RiskConfigPage />} />
          <Route path="/system-health" element={<SystemHealthPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/learning" element={<LearningPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
