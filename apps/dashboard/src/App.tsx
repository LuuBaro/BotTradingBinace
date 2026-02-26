import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { PositionsPage } from './pages/PositionsPage'
import { OrdersPage } from './pages/OrdersPage'
import { TradesPage } from './pages/TradesPage'
import { RiskConfigPage } from './pages/RiskConfigPage'
import { SystemHealthPage } from './pages/SystemHealthPage'
import { EventsPage } from './pages/EventsPage'
import { LearningPage } from './pages/LearningPage'
import { SettingsPage } from './pages/SettingsPage'
import { IntelPage } from './pages/IntelPage'

function App() {
  const { isAuthenticated } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if token is still valid
    const token = localStorage.getItem('token')
    setLoading(false)
  }, [])

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
      <Layout>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/intel" element={<IntelPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/orders" element={<OrdersPage />} />
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
