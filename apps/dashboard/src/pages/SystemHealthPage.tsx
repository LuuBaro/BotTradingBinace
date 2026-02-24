import React, { useEffect, useState } from 'react'
import { useDashboardStore } from '../store'
import { createApiClient } from '../api/client'

export const SystemHealthPage: React.FC = () => {
  const { health, latency } = useDashboardStore()
  const [reconStatus, setReconStatus] = useState<any>(null)
  const api = createApiClient('http://localhost:8001/api', localStorage.getItem('token') || '')

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const h = await api.getHealthStatus()
        const r = await api.getReconSummary()
        // Update dashboard store
        setReconStatus(r)
      } catch (error) {
        console.error('Failed to fetch health:', error)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000)
    return () => clearInterval(interval)
  }, [api])

  const getStatusBadge = (status: boolean | string) => {
    const isHealthy = status === true || status === 'healthy'
    return (
      <span className={`badge ${
        isHealthy
          ? 'badge-success'
          : 'badge-danger'
      }`}>
        {isHealthy ? '✅ Healthy' : '❌ Unhealthy'}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">System Health</h1>

      {/* Health Components */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h3 className="text-lg font-semibold">WebSocket</h3>
            {getStatusBadge(health?.ws_connected)}
          </div>
          <div className="card-body space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Connected:</span>
              <span className="text-white">{health?.ws_connected ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Reconnects:</span>
              <span className="text-white">{health?.ws_reconnects || 0}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h3 className="text-lg font-semibold">REST API</h3>
            {getStatusBadge(health?.rest_healthy)}
          </div>
          <div className="card-body space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Last Request:</span>
              <span className="text-white">{health?.rest_last_request || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Errors:</span>
              <span className="text-white">{health?.rest_errors || 0}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h3 className="text-lg font-semibold">Database</h3>
            {getStatusBadge(health?.db_healthy)}
          </div>
          <div className="card-body space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Connected:</span>
              <span className="text-white">{health?.db_connected ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Pool:</span>
              <span className="text-white">{health?.db_pool_size || 0}/{health?.db_pool_max || 10}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h3 className="text-lg font-semibold">Circuit Breaker</h3>
            {getStatusBadge(health?.circuit_breaker_state === 'CLOSED')}
          </div>
          <div className="card-body space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">State:</span>
              <span className={`font-bold ${
                health?.circuit_breaker_state === 'CLOSED' ? 'text-green-400' :
                health?.circuit_breaker_state === 'OPEN' ? 'text-red-400' :
                'text-yellow-400'
              }`}>
                {health?.circuit_breaker_state}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Safe Mode:</span>
              <span className="text-white">{health?.is_safe_for_trading ? '✅ Yes' : '❌ No'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Latency */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-xl font-bold">Latency Metrics</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-slate-400 text-sm mb-2">WebSocket P95</div>
              <div className="text-3xl font-bold text-blue-400">{latency?.ws_p95 || 0}ms</div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-2">REST P95</div>
              <div className="text-3xl font-bold text-blue-400">{latency?.rest_p95 || 0}ms</div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-2">Clock Skew</div>
              <div className="text-3xl font-bold text-blue-400">{latency?.clock_skew || 0}ms</div>
            </div>
          </div>
        </div>
      </div>

      {/* Reconciliation Status */}
      {reconStatus && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl font-bold">Reconciliation Status</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div>
                <div className="text-slate-400 text-sm mb-2">Last Sync</div>
                <div className="text-white font-mono">{reconStatus.last_sync}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-2">Mismatches</div>
                <div className={`text-2xl font-bold ${reconStatus.total_mismatches === 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {reconStatus.total_mismatches}
                </div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-2">Position Mismatches</div>
                <div className="text-white">{reconStatus.position_mismatches || 0}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-2">Sync Status</div>
                <div className="text-white font-semibold">
                  {reconStatus.total_mismatches === 0 ? '✅ Synced' : '⚠️ Mismatched'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
