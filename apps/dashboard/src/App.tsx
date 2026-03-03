import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import { Layout } from './components/Layout'
import { ToastContainer } from './components/ToastContainer'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { PositionsPage } from './pages/PositionsPage'
import { OrdersPage } from './pages/OrdersPage'
import { TradesPage } from './pages/TradesPage'
import { TradeHistoryPage } from './pages/TradeHistoryPage'
import { RiskConfigPage } from './pages/RiskConfigPage'
import { SystemHealthPage } from './pages/SystemHealthPage'
import { EventsPage } from './pages/EventsPage'
import { NeuralConsolePage } from './pages/NeuralConsolePage'
import { NeuralPortalPage } from './pages/NeuralPortalPage'
import { LearningPage } from './pages/LearningPage'
import { SettingsPage } from './pages/SettingsPage'
import { IntelPage } from './pages/IntelPage'
import { AdminPanelPage } from './pages/AdminPanelPage'
import { useLocation } from 'react-router-dom'

const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuthStore()
  if (user?.role?.toLowerCase() !== 'admin') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function App() {
  const { isAuthenticated } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if token is still valid
    localStorage.getItem('token')
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
    <>
      <ToastContainer />
      <Router>
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
          <Route path="/terminal" element={<NeuralConsolePage />} />
          <Route path="/portal" element={<NeuralPortalPage />} />
          <Route path="/settings" element={<AdminRoute><SettingsPage /></AdminRoute>} />
          <Route path="/admin" element={<AdminRoute><AdminPanelPage /></AdminRoute>} />
          <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Layout>
      </Router>
    </>
  )
}

export default App
